import sounddevice as sd
import numpy as np
import torch
import config
import threading
import queue
from PyQt6.QtCore import QObject, pyqtSignal

class AudioRecorder(QObject):
    audio_processed_signal = pyqtSignal(object) # Carries numpy array
    log_signal = pyqtSignal(str) # Log message

    def __init__(self):
        super().__init__()
        self.sample_rate = config.SAMPLE_RATE
        self.block_size = config.BLOCK_SIZE
        self.vad_threshold = config.VAD_THRESHOLD
        
        self.vad_threshold = config.VAD_THRESHOLD
        
        # Load Silero VAD model (using pip package)
        print("Loading Silero VAD model from pip package...")
        try:
            from silero_vad import load_silero_vad, VADIterator
            self.model = load_silero_vad(onnx=True)
            self.VADIterator = VADIterator
        except ImportError:
            # Fallback (old behavior) if package missing, but user said it's installed
            print("Failed to import silero_vad. Falling back to torch.hub...")
            self.model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                            model='silero_vad',
                                            force_reload=False,
                                            onnx=False)
            self.VADIterator = utils[3]

        # VAD only supports 8k or 16k. We record at 48k and downsample for VAD.
        self.vad_sample_rate = 16000
        self.vad_iterator = self.VADIterator(self.model,
                                             threshold=self.vad_threshold,
                                             sampling_rate=self.vad_sample_rate,
                                             min_silence_duration_ms=config.SILENCE_DURATION_MS,
                                             speech_pad_ms=config.SPEECH_PAD_MS)
        print("Model loaded.")

        self.recording = False
        self.audio_queue = queue.Queue()
        self.current_buffer = []
        self.is_speaking = False
        self.speech_start_time = None

        
        # Thread for processing audio to avoid blocking the audio callback
        self.processing_thread = threading.Thread(target=self.process_audio_queue)
        self.processing_thread.daemon = True
        self.processing_thread.start()

    # ... (list and start/stop methods) ...

    def process_audio_queue(self):
        while True:
            indata = self.audio_queue.get()
            if indata is None:
                continue

            # Downsample for VAD (48000 -> 16000)
            # Simple decimation [::3] works if ratio is integer and signal is typically voice
            # For 48k to 16k, step is 3.
            if self.sample_rate == 48000:
                vad_data = indata[::3]
            elif self.sample_rate == 16000:
                vad_data = indata
            else:
                # Fallback, might fail VAD if not 8k/16k, but usually we stick to these
                vad_data = indata
            
            # Convert to tensor for VAD
            vad_tensor = torch.from_numpy(vad_data).squeeze()
            
            # Use VADIterator logic
            speech_dict = self.vad_iterator(vad_tensor, return_seconds=True)
            
            if speech_dict and 'start' in speech_dict:
                self.is_speaking = True
                self.log_signal.emit("Voice detected")
            
            if self.is_speaking:
                self.current_buffer.append(indata) # Buffer the ORIGINAL high-quality audio
            
            if speech_dict and 'end' in speech_dict:
                self.is_speaking = False
                self.log_signal.emit("Voice ended, processing...")
                if self.current_buffer:
                    full_audio = np.concatenate(self.current_buffer)
                    # Emit signal instead of direct callback
                    self.audio_processed_signal.emit(full_audio)
                    self.current_buffer = []
                    self.vad_iterator.reset_states()

    @staticmethod
    def list_input_devices():
        devices = sd.query_devices()
        input_devices = []
        for i, d in enumerate(devices):
            if d['max_input_channels'] > 0:
                input_devices.append((i, d['name']))
        return input_devices

    def start_recording(self, device_index=None):
        if self.recording:
            return
        self.recording = True
        try:
            self.stream = sd.InputStream(samplerate=self.sample_rate,
                                        blocksize=self.block_size,
                                        device=device_index,
                                        channels=1,
                                        dtype='float32',
                                        callback=self.audio_callback)
            self.stream.start()
            self.log_signal.emit(f"Recording started on device index {device_index}...")
        except Exception as e:
            self.log_signal.emit(f"Error starting stream: {e}")
            self.recording = False

    def stop_recording(self):
        if not self.recording:
            return
        self.recording = False
        self.stream.stop()
        self.stream.close()
    def stop_recording(self):
        if not self.recording:
            return
        self.recording = False
        self.stream.stop()
        self.stream.close()
        self.log_signal.emit("Recording stopped.")
        
        # Force process any remaining buffer
        if self.current_buffer:
             self.log_signal.emit("Processing buffered audio (Manual Stop)...")
             self.finalize_recording()
             self.is_speaking = False
             # self.vad_iterator.reset_states() # Done in finalize



    def audio_callback(self, indata, frames, time, status):
        if status:
            self.log_signal.emit(f"Status: {status}")
        # Add audio to queue for processing
        self.audio_queue.put(indata.copy())

    def process_audio_queue(self):
        import scipy.signal
        import time
        
        while True:

            indata = self.audio_queue.get()
            if indata is None:
                continue

            # Check for silence/zeros (Debug)
            vol = np.linalg.norm(indata) * 10
            # if vol < 1:
            #     # Very silent
            #     pass

            # Downsample for VAD (48000 -> 16000)
            if self.sample_rate == 48000:
                # Better resampling
                # 1536 -> 512
                # Note: resample returns same shape as input if axis not specified, but we change length.
                # indata is (1536, 1)
                new_len = int(len(indata) / 3)
                vad_data = scipy.signal.resample(indata, new_len)
            elif self.sample_rate == 16000:
                vad_data = indata
            else:
                vad_data = indata
            
            # Convert to tensor for VAD
            vad_tensor = torch.from_numpy(vad_data).squeeze()
            
            # Get probability (for debugging)
            speech_prob = self.model(vad_tensor, 16000).item()
            if speech_prob > 0.3:
                 # Only log if it's somewhat significant to avoid spam
                 # self.log_signal.emit(f"VAD Prob: {speech_prob:.2f}")
                 pass

            # Use VADIterator logic
            speech_dict = self.vad_iterator(vad_tensor, return_seconds=True)
            
            if speech_dict:
                print(f"VAD Event: {speech_dict}") # Console debug

            # Store chunk with probability for smart filtering
            chunk_data = (indata, speech_prob)
            
            if speech_dict and 'start' in speech_dict:
                self.is_speaking = True
                self.speech_start_time = time.time()
                self.log_signal.emit(f"Voice detected (Prob: {speech_prob:.2f})")


            
            if self.is_speaking:
                self.current_buffer.append(chunk_data) # Buffer (data, prob) tuple
                
                # Check for max duration
                if self.speech_start_time and (time.time() - self.speech_start_time > config.MAX_SPEECH_DURATION_S):
                    self.log_signal.emit(f"Max speech duration ({config.MAX_SPEECH_DURATION_S}s) reached. Forcing process.")
                    # Force end logic
                    self.is_speaking = False
                    self.finalize_recording()
                    self.speech_start_time = None

            
            if speech_dict and 'end' in speech_dict:
                self.is_speaking = False
                self.speech_start_time = None
                self.log_signal.emit("Voice ended, processing...")
                self.finalize_recording()
    
    def finalize_recording(self):
        if not self.current_buffer:
            self.vad_iterator.reset_states()
            return
            
        self.log_signal.emit(f"Raw buffer size: {len(self.current_buffer)} chunks")
        
        # Smart Filter: Keep chunks with high prob OR neighbors of high prob
        # Pad size in chunks = SPEECH_PAD_MS / (block_size/sample_rate converted to ms)
        # Block size 1536 @ 48000 = 32ms.
        # Pad 300ms ~= 10 chunks.
        
        # Calculate chunks needed for padding
        chunk_duration_ms = (self.block_size / self.sample_rate) * 1000
        pad_chunks = int(config.SPEECH_PAD_MS / chunk_duration_ms)
        
        filtered_audio = []
        original_count = len(self.current_buffer)
        
        # Mark chunks to keep
        keep_mask = [False] * original_count
        
        for i, (data, prob) in enumerate(self.current_buffer):
            if prob > config.MIN_SPEECH_PROB:
                # Mark this chunk and neighbors
                start_k = max(0, i - pad_chunks)
                end_k = min(original_count, i + pad_chunks + 1)
                for k in range(start_k, end_k):
                    keep_mask[k] = True
                    
        # Construct final audio
        for i, keep in enumerate(keep_mask):
            if keep:
                filtered_audio.append(self.current_buffer[i][0])
                
        if not filtered_audio:
            self.log_signal.emit("No valid speech found in buffer (filtered everything).")
            self.current_buffer = []
            self.vad_iterator.reset_states()
            return

        self.log_signal.emit(f"Optimization: Reduced {original_count} -> {len(filtered_audio)} chunks")

        full_audio = np.concatenate(filtered_audio)
        self.audio_processed_signal.emit(full_audio)
        self.current_buffer = []
        self.vad_iterator.reset_states()

