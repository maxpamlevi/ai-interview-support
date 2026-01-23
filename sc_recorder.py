import time
import threading
import queue
import numpy as np
import torch
import scipy.signal
import objc
from PyQt6.QtCore import QObject, pyqtSignal
from Foundation import NSObject, NSLog, NSArray
from ScreenCaptureKit import (
    SCShareableContent,
    SCContentFilter,
    SCStream,
    SCStreamConfiguration,
    SCStreamOutputTypeAudio
)
import CoreMedia
import AVFoundation

import config
import scipy.io.wavfile

class SCRecorderDelegate(NSObject):
    def initWithParent_(self, parent):
        self = objc.super(SCRecorderDelegate, self).init()
        if self:
            self.parent = parent
        return self

    def stream_didOutputSampleBuffer_ofType_(self, stream, sampleBuffer, sampleType):
        if sampleType == SCStreamOutputTypeAudio:
            self.parent.handle_audio_sample(sampleBuffer)

class SCRecorder(QObject):
    audio_processed_signal = pyqtSignal(object) # Carries numpy array
    log_signal = pyqtSignal(str) # Log message

    def __init__(self):
        super().__init__()
        # VAD Setup
        self.vad_threshold = config.VAD_THRESHOLD
        self.sample_rate = 48000 
        
        print("Loading Silero VAD model (SCK)...")
        try:
            from silero_vad import load_silero_vad, VADIterator
            self.model = load_silero_vad(onnx=True)
            self.VADIterator = VADIterator
        except ImportError:
            self.model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                            model='silero_vad',
                                            force_reload=False,
                                            onnx=False)
            self.VADIterator = utils[3]

        self.vad_sample_rate = 16000
        self.vad_iterator = self.VADIterator(self.model,
                                             threshold=self.vad_threshold,
                                             sampling_rate=self.vad_sample_rate,
                                             min_silence_duration_ms=config.SILENCE_DURATION_MS,
                                             speech_pad_ms=config.SPEECH_PAD_MS)
        
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.current_buffer = []
        self.is_speaking = False
        self.speech_start_time = None
        
        self.stream = None
        self.delegate = None
        self.queue = None
        
        # --- DEBUG: RAW DUMP ---
        self.raw_dump_buffer = []
        self.raw_dump_max = 500 # Dump first 500 samples
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self.process_audio_queue)
        self.processing_thread.daemon = True
        self.processing_thread.start()

    @staticmethod
    def list_input_devices():
        return [(-999, "System Audio (ScreenCaptureKit)")]

    def start_recording(self, device_index=None):
        if self.is_recording:
            return

        self.log_signal.emit("Initializing ScreenCaptureKit...")
        self.raw_dump_buffer = [] # Reset dump
        
        def handle_content(content, error):
            if error:
                self.log_signal.emit(f"Error SCK content: {error}")
                return
            
            displays = content.displays()
            if not displays:
                self.log_signal.emit("No displays found!")
                return
            
            main_display = displays[0]
            
            filter_ = SCContentFilter.alloc().initWithDisplay_excludingApplications_exceptingWindows_(
                main_display, [], []
            )
            
            config_ = SCStreamConfiguration.alloc().init()
            config_.setCapturesAudio_(True)
            config_.setExcludesCurrentProcessAudio_(False) 
            
            self.delegate = SCRecorderDelegate.alloc().initWithParent_(self)
            self.stream = SCStream.alloc().initWithFilter_configuration_delegate_(
                filter_, config_, self.delegate
            )
            
            # --- CRITICAL FIX: Add Stream Output with Dispatch Queue ---
            import ctypes
            import ctypes.util
            lib = ctypes.cdll.LoadLibrary(ctypes.util.find_library("System"))
            lib.dispatch_queue_create.restype = ctypes.c_void_p
            lib.dispatch_queue_create.argtypes = [ctypes.c_char_p, ctypes.c_void_p]
            
            self.queue = lib.dispatch_queue_create(b"com.ai-interview.audio", None)
            
            try:
                queue_ptr = self.queue
                if hasattr(queue_ptr, 'value'):
                    queue_addr = queue_ptr.value
                else:
                    queue_addr = queue_ptr
                    
                queue_obj = objc.objc_object(c_void_p=queue_addr)
                
                res = self.stream.addStreamOutput_type_sampleHandlerQueue_error_(
                    self.delegate, 
                    SCStreamOutputTypeAudio, 
                    queue_obj,
                    None
                )
                
                if isinstance(res, tuple):
                    success, err = res
                    if not success:
                        self.log_signal.emit(f"Failed to add stream output: {err}")
                    else:
                        self.log_signal.emit("Added Stream Output (Success).")
                else:
                    self.log_signal.emit(f"Added Stream Output (Res: {res}).")

            except Exception as e:
                self.log_signal.emit(f"Failed to add stream output (Exception): {e}")

            def handle_start(error):
                if error:
                    self.log_signal.emit(f"Start failed: {error}")
                else:
                    self.log_signal.emit("SCK Stream Started.")
                    self.is_recording = True
                    
            self.stream.startCaptureWithCompletionHandler_(handle_start)

        SCShareableContent.getShareableContentWithCompletionHandler_(handle_content)

    def stop_recording(self):
        if self.stream:
            self.stream.stopCaptureWithCompletionHandler_(lambda e: None)
        self.is_recording = False
        self.log_signal.emit("SCK Stream Stopped.")
        
        if self.raw_dump_buffer:
             self.save_raw_dump()
             
        if self.current_buffer:
             self.finalize_recording()

    def save_raw_dump(self):
        try:
            full_raw = np.concatenate(self.raw_dump_buffer)
            filename = f"sc_raw_debug_{int(time.time())}.wav"
            # Assume 48000 for SCK
            scipy.io.wavfile.write(filename, 48000, full_raw)
            self.log_signal.emit(f"Saved RAW debug audio to {filename}")
        except Exception as e:
            self.log_signal.emit(f"Failed to save raw dump: {e}")

    def handle_audio_sample(self, sampleBuffer):
        try:
            block_buffer = CoreMedia.CMSampleBufferGetDataBuffer(sampleBuffer)
            if not block_buffer:
                return
                
            length = CoreMedia.CMBlockBufferGetDataLength(block_buffer)
            if length == 0:
                print("SCK: Zero length buffer")
                return

            data_bytes = bytearray(length)
            CoreMedia.CMBlockBufferCopyDataBytes(block_buffer, 0, length, data_bytes)
            
            # Assume Float32
            audio_array = np.frombuffer(data_bytes, dtype=np.float32)
            
            # SCK often returns Non-Interleaved (Planar) Stereo [LLL...RRR]
            # If we treat it as Interleaved [LRLR...] we get slow audio (mixing adjacent L samples).
            # Let's try Planar Mixdown.
            
            sample_count = len(audio_array)
            
            # Heuristic: SCK System Audio is usually 2 channels. 
            # If Planar: L is first half, R is second half.
            
            if sample_count % 2 == 0:
                 half = sample_count // 2
                 left = audio_array[:half]
                 right = audio_array[half:]
                 audio_mono = (left + right) / 2.0
            else:
                 # Should not happen for Planar Stereo usually
                 audio_mono = audio_array

            # RAW DUMP (Save the MONO version)
            if len(self.raw_dump_buffer) < self.raw_dump_max:
                self.raw_dump_buffer.append(audio_mono)
                if len(self.raw_dump_buffer) == self.raw_dump_max:
                    self.log_signal.emit("Raw dump buffer full. Saving...")
                    self.save_raw_dump()
                
            self.audio_queue.put(audio_mono)
            
        except Exception as e:
            print(f"SCK Parse Error: {e}")
            pass

    def process_audio_queue(self):
        while True:
            indata = self.audio_queue.get()
            if indata is None:
                continue

            # Resample for VAD
            vad_data = indata[::3] 
            
            vad_tensor = torch.from_numpy(vad_data).float().squeeze()
            if len(vad_tensor) < 10: 
                continue
            
            speech_dict = self.vad_iterator(vad_tensor, return_seconds=True)
            
            if speech_dict and 'start' in speech_dict:
                self.is_speaking = True
                self.speech_start_time = time.time()
                self.log_signal.emit("Voice detected (SCK)")
                
            if self.is_speaking:
                self.current_buffer.append((indata, 1.0)) 
                
                if self.speech_start_time and (time.time() - self.speech_start_time > config.MAX_SPEECH_DURATION_S):
                    self.log_signal.emit("Max duration reached.")
                    self.is_speaking = False
                    self.finalize_recording()
                    self.speech_start_time = None
            
            if speech_dict and 'end' in speech_dict:
                self.is_speaking = False
                self.speech_start_time = None
                self.log_signal.emit("Voice ended (SCK), processing...")
                self.finalize_recording()

    def finalize_recording(self):
        if not self.current_buffer:
            self.vad_iterator.reset_states()
            return

        full_audio = np.concatenate([c[0] for c in self.current_buffer])
        self.audio_processed_signal.emit(full_audio)
        self.current_buffer = []
        self.vad_iterator.reset_states()
