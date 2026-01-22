import sys
import threading
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import pyqtSignal, QObject, QThread
from overlay_ui import OverlayUI
from audio_recorder import AudioRecorder
from gemini_client import GeminiClient
import config

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
        suggestion = self.gemini_client.generate_suggestion(audio_data, language=language)
        self.update_suggestion_signal.emit(suggestion)
        self.update_status_signal.emit("Listening...", "#4CAF50") # Green
        self.finished_signal.emit()

def main():
    app = QApplication(sys.argv)
    
    # Initialize components
    ui = OverlayUI()
    gemini_client = GeminiClient(api_key=config.GEMINI_API_KEY)
    
    # Audio Recorder (Main Thread is owner, but runs its own internal thread for VAD)
    recorder = AudioRecorder()
    
    # Worker Thread Management
    # We create a new worker/thread for each request? 
    # OR we have a dedicated worker thread.
    
    worker_thread = QThread()
    worker = AssistantWorker(gemini_client)
    worker.moveToThread(worker_thread)
    worker_thread.start()
    
    # Signal Wrapper to bridge Recorder -> UI/Main -> Worker
    # Recorder emits audio. Main knows UI state. Main triggers Worker.
    


    def handle_audio_processed(audio_data):
        # This runs in Main Thread because recorder signal is connected here?
        # WAIT. recorder.audio_processed_signal.emit() is called from recorder's internal thread.
        # Connected to a slot in Main Thread (this function if defined in main scope implicitly?)
        # Actually, python signals are not auto-queued across threads unless using Qt slots mechanism properly.
        # But `recorder` is a QObject. `audio_processed_signal` is pyqtSignal.
        pass

    # Populate Device Combo
    input_devices = AudioRecorder.list_input_devices()
    for idx, name in input_devices:
        ui.device_combo.addItem(f"{name}", idx)
        # Select BlackHole if present by default
        if "BlackHole" in name:
            ui.device_combo.setCurrentIndex(ui.device_combo.count() - 1)


    ui.show()
    
    # Signal Wrapper to bridge Recorder -> UI/Main -> Worker
    # Recorder emits audio. Main knows UI state. Main triggers Worker.
    
    class Coordinator(QObject):
        request_process = pyqtSignal(object, str) # audio, language

        def handle_audio(self, audio_data):
            # This slot runs in the Main Thread because Coordinator is created in Main
            # and signal comes from another thread (QueuedConnection)
            try:
                language = ui.get_selected_language()
                print(f"Audio received in Main Thread. Language: {language}")
                self.request_process.emit(audio_data, language)
            except Exception as e:
                print(f"Error in handle_audio: {e}")

    coordinator = Coordinator()
    coordinator.request_process.connect(worker.process_audio)

    # Correct wiring:
    # Connect recorder signal to coordinator slot
    # This ensures the lambda/slot runs in Main Thread
    recorder.audio_processed_signal.connect(coordinator.handle_audio)

    # Connect Recorder Logs to UI
    recorder.log_signal.connect(ui.append_log)

    # Connect Worker Signals to UI
    worker.update_suggestion_signal.connect(ui.append_suggestion)
    worker.update_status_signal.connect(ui.update_status)
    # Log status changes
    worker.update_status_signal.connect(lambda msg, col: ui.append_log(f"Status: {msg}"))

    # Connect UI buttons to Recorder
    # Pass the selected device index when starting
    ui.start_recording_signal.connect(lambda: recorder.start_recording(ui.get_selected_device_index()))
    ui.stop_recording_signal.connect(recorder.stop_recording)
    
    # Clean exit
    try:
        sys.exit(app.exec())
    except SystemExit:
        recorder.stop_recording()
        worker_thread.quit()
        worker_thread.wait()

if __name__ == "__main__":
    main()
