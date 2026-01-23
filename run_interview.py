import subprocess
import sys
import numpy as np
import threading
import queue
import time
import wave
import struct

# Configuration
SWIFT_TOOL_PATH = "./AudioCapture/.build/release/AudioCapture"
SAMPLE_RATE = 48000
CHANNELS = 1
# ScreenCaptureKit might send Float32 or Int16. We need to check.
DTYPE = np.float32
# Based on AudioRecorder.swift, we requested SampleRate 48000.
# Providing raw bytes from CMSampleBuffer. SCStream usually outputs Float32 planar or interleaved.
# Let's assume Float32 for now, if it sounds like static noise, we switch to Int16.

# For Whisper
try:
    from faster_whisper import WhisperModel
except ImportError:
    print("faster_whisper not found. Please pip install faster_whisper")
    sys.exit(1)

model_size = "large-v3"  # or medium.en
print(f"Loading Whisper model {model_size}...")
# Use CPU/int8 as per trans.py
# model = WhisperModel(model_size, device="cpu", compute_type="int8")
print("Model loaded.")


def audio_reader(process, audio_queue):
    """Reads raw audio from subprocess stdout and puts it into a queue."""
    chunk_size = 4096  # bytes
    while True:
        data = process.stdout.read(chunk_size)
        if not data:
            break
        # Assuming float32 (4 bytes per sample)
        # We need to buffer this properly or just dump to queue
        audio_queue.put(data)


def main():
    # Start the Swift process
    print(f"Starting Swift audio capture tool: {SWIFT_TOOL_PATH}")
    try:
        process = subprocess.Popen(
            [SWIFT_TOOL_PATH],
            stdout=subprocess.PIPE,
            stderr=sys.stderr,  # Pass stderr through to see errors/logs
            bufsize=0  # Unbuffered
        )
    except FileNotFoundError:
        print(f"Error: Could not find executable at {SWIFT_TOOL_PATH}")
        print("Did you run 'swift build -c release' in AudioCapture directory?")
        return

    audio_queue = queue.Queue()
    reader_thread = threading.Thread(
        target=audio_reader, args=(process, audio_queue), daemon=True)
    reader_thread.start()

    print("Listening for audio from Chrome... (Press Ctrl+C to stop)")

    # Debug WAV file
    wav_file = wave.open("debug_output.wav", "wb")
    wav_file.setnchannels(CHANNELS)
    wav_file.setsampwidth(2)  # 16-bit
    wav_file.setframerate(SAMPLE_RATE)

    # Accumulate audio for transcription
    audio_buffer = bytearray()

    # 2 seconds chunk for transcription
    # 48000 samples/sec * 4 bytes/sample * 2 sec = 384000 bytes
    bytes_per_second = SAMPLE_RATE * 4
    chunk_bytes_threshold = bytes_per_second * 2

    try:
        while True:
            try:
                data = audio_queue.get(timeout=0.1)

                # Write to WAV file (convert float32 to int16)
                # Data is raw float32 bytes.
                audio_np = np.frombuffer(data, dtype=np.float32)
                # Clip and convert to int16
                audio_int16 = (audio_np * 32767).clip(-32768,
                                                      32767).astype(np.int16)
                wav_file.writeframes(audio_int16.tobytes())

                audio_buffer.extend(data)

                if len(audio_buffer) >= chunk_bytes_threshold:
                    # Process this chunk
                    # Convert to numpy array
                    # We take the first chunk_bytes_threshold bytes
                    process_data = audio_buffer[:chunk_bytes_threshold]
                    # Keep the rest? Or overlap? For simple streaming, let's just clear or slide
                    # Sliding window is better but simpler logic first:
                    audio_buffer = audio_buffer[chunk_bytes_threshold:]

                    # Convert bytes to float32 array
                    audio_np = np.frombuffer(
                        process_data, dtype=np.float32).copy()

                    # Whisper expects 16k sample rate usually, check doc.
                    # faster-whisper handles resampling? No, we usually need to resample.
                    # But let's try passing it directly or resample manually?
                    # faster_whisper transcribes based on 16k input.

                    # Simple resampling (decimation) if high quality isn't needed or use scipy/librosa
                    # 48k -> 16k is factor of 3.
                    audio_np_16k = audio_np[::3]

                    segments, info = model.transcribe(
                        audio_np_16k, beam_size=5, language="en")

                    print("\n--- Transcription ---")
                    for segment in segments:
                        print(
                            f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
                    print("---------------------")

            except queue.Empty:
                continue

    except KeyboardInterrupt:
        print("\nStopping...")
        process.terminate()
        process.wait()
        wav_file.close()
        print("Debug audio saved to 'debug_output.wav'")


if __name__ == "__main__":
    main()
