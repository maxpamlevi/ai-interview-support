import sounddevice as sd
import soundfile as sf
import numpy as np
import sys

OUTPUT_FILE = "system_audio.wav"
SAMPLE_RATE = 44100
CHANNELS = 2
DURATION = 10  # seconds
DEVICE_KEYWORD = "BlackHole"

def find_blackhole_input():
    devices = sd.query_devices()
    for idx, d in enumerate(devices):
        if DEVICE_KEYWORD in d["name"] and d["max_input_channels"] > 0:
            return idx, d
    return None, None

def main():
    device_id, device = find_blackhole_input()

    if device_id is None:
        print("❌ Không tìm thấy BlackHole input device")
        sys.exit(1)

    print("✅ Using device:")
    print(f"   ID: {device_id}")
    print(f"   Name: {device['name']}")
    print(f"   Channels: {device['max_input_channels']}")

    print(f"\n🎙 Recording system audio for {DURATION} seconds...")
    print("▶️ Hãy bật YouTube / system sound NGAY BÂY GIỜ")

    audio = sd.rec(
        frames=int(DURATION * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        device=device_id
    )

    sd.wait()

    # Nếu toàn số 0 → routing sai
    if np.max(np.abs(audio)) < 1e-6:
        print("❌ File ghi ra toàn silence")
        print("👉 Kiểm tra lại:")
        print("   - System Output có phải Multi-Output Device không")
        print("   - BlackHole có input level nhảy không")
        sys.exit(1)

    sf.write(OUTPUT_FILE, audio, SAMPLE_RATE)
    print(f"✅ Saved: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
