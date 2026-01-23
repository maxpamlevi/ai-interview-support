import sys
import threading
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import pyqtSignal, QObject, QThread
from overlay_ui import OverlayUI
from audio_recorder import AudioRecorder
from gemini_client import GeminiClient
import config
from sc_recorder import SCRecorder

# Worker to handle API calls ensuring UI doesn't freeze
class AssistantWorker(QObject):
    update_suggestion_signal = pyqtSignal(str)
    update_status_signal = pyqtSignal(str, str) # text, color
    finished_signal = pyqtSignal()

    def __init__(self, gemini_client):
        super().__init__()
        self.gemini_client = gemini_client

    def process_audio(self, audio_data, language):
        # This function will run in a separate QThread
        self.update_status_signal.emit(f"Processing ({language})...", "#FFC107") # Amber
        
        # --- TEST MODE: SAVE AUDIO & SKIP API ---
        import scipy.io.wavfile
        import numpy as np
        import time
        import os
        
        timestamp = int(time.time())
        filename = f"debug_audio_{timestamp}.wav"
        
        # AudioRecorder uses config.SAMPLE_RATE.
        # We assume 16000 or 48000 depending on source, but config.SAMPLE_RATE is safer
        rate = config.SAMPLE_RATE
        # If SCK provides 48k, saving as 16k might be wrong pitch if we didn't resample.
        # But both recorders currently try to emit processed/resampled audio?
        # NO. AudioRecorder emits result of VAD buffer which is high quality buffer?
        # AudioRecorder: `self.current_buffer.append(indata)` -> indata is raw 48k/16k.
        
        scipy.io.wavfile.write(filename, rate, audio_data)
        print(f"Saved debug audio to {os.path.abspath(filename)}")
        
        self.update_suggestion_signal.emit(f"Audio saved to {filename}. API call skipped.")
        
        # suggestion = self.gemini_client.generate_suggestion(audio_data, language=language)
        # self.update_suggestion_signal.emit(suggestion)
        # ----------------------------------------
        
        self.update_status_signal.emit("Listening...", "#4CAF50") # Green
        self.finished_signal.emit()

def main():
    app = QApplication(sys.argv)
    
    # Initialize components
    ui = OverlayUI()
    gemini_client = GeminiClient(api_key=config.GEMINI_API_KEY)
    
    # Audio Recorder (Microphones)
    recorder = AudioRecorder()
    
    # SC Recorder (System Audio)
    sc_recorder = SCRecorder()
    
    # Worker Thread Management
    worker_thread = QThread()
    worker = AssistantWorker(gemini_client)
    worker.moveToThread(worker_thread)
    worker_thread.start()
    
    class Coordinator(QObject):
        request_process = pyqtSignal(object, str) # audio, language

        def handle_audio(self, audio_data):
            try:
                language = ui.get_selected_language()
                print(f"Audio received in Main Thread. Language: {language}")
                self.request_process.emit(audio_data, language)
            except Exception as e:
                print(f"Error in handle_audio: {e}")

    coordinator = Coordinator()
    coordinator.request_process.connect(worker.process_audio)

    # Wiring Recorders to Coordinator & UI
    recorder.audio_processed_signal.connect(coordinator.handle_audio)
    sc_recorder.audio_processed_signal.connect(coordinator.handle_audio)
    
    recorder.log_signal.connect(ui.append_log)
    sc_recorder.log_signal.connect(ui.append_log)

    # Connect Worker Signals to UI
    worker.update_suggestion_signal.connect(ui.append_suggestion)
    worker.update_status_signal.connect(ui.update_status)
    worker.update_status_signal.connect(lambda msg, col: ui.append_log(f"Status: {msg}"))

    # Populate Device Combo
    input_devices = AudioRecorder.list_input_devices()
    # Append SCK device
    input_devices.extend(SCRecorder.list_input_devices())
    
    for idx, name in input_devices:
        ui.device_combo.addItem(f"{name}", idx)
        # Select System Audio by default
        if "System Audio" in name:
            ui.device_combo.setCurrentIndex(ui.device_combo.count() - 1)

    # Ensure System Audio is selected if available (last item usually)
    if "System Audio" in ui.device_combo.itemText(ui.device_combo.count() - 1):
        ui.device_combo.setCurrentIndex(ui.device_combo.count() - 1)

    ui.show()

    # Handle Processing Logic
    def start_recording_wrapper():
        idx = ui.get_selected_device_index()
        # idx might be -999 for SCK
        if idx == -999: # SCK
            recorder.stop_recording()
            sc_recorder.start_recording(idx)
        else:
            sc_recorder.stop_recording()
            recorder.start_recording(idx)
            
    def stop_recording_wrapper():
        recorder.stop_recording()
        sc_recorder.stop_recording()

    # Connect UI buttons
    ui.start_recording_signal.connect(start_recording_wrapper)
    ui.stop_recording_signal.connect(stop_recording_wrapper)
    
    # Clean exit
    try:
        sys.exit(app.exec())
    except SystemExit:
        recorder.stop_recording()
        sc_recorder.stop_recording()
        worker_thread.quit()
        worker_thread.wait()

if __name__ == "__main__":
    main()
