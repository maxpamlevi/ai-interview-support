# 🎙️ AI Interview Assistant

[Đọc bằng tiếng Việt](README.vi.md)

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Gemini](https://img.shields.io/badge/AI-Gemini_2.0-orange?style=for-the-badge&logo=google)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green?style=for-the-badge&logo=qt)

**Real-time AI Interview Support System**
*Question Detection - Smart Answer Suggestions - Low Latency Optimization*

</div>

---

## ✨ Features

- **Real-time Audio Capture**: Capture audio directly from the system (Zoom, Google Meet, Teams) or Microphone.
- **Smart VAD (Voice Activity Detection)**: Automatically removes silence, processing only actual speech.
- **Gemini 2.0 Integration**: Analyzes questions and provides professional answer suggestions instantly.
- **Floating Overlay UI**: Transparent interface, always on top, displaying suggestions without obscuring the interview screen.
- **Multi-language Support**: Excellent support for both English and Vietnamese.

## 🛠️ Prerequisites

Before installing, ensure you have:

1.  **Python 3.10+**: [Download here](https://www.python.org/downloads/)
2.  **BlackHole (Virtual Audio Driver)**: To capture system audio (Zoom/Meet) without using external speakers.
    -   Download and install **BlackHole 2ch**: [ExistentialAudio/BlackHole](https://github.com/ExistentialAudio/BlackHole)
    -   *Why needed?* Meeting apps often take exclusive control of the microphone; BlackHole helps "loopback" the interviewer's audio output so the AI can hear it.

## 🚀 Installation

### 1. Clone Project
```bash
git clone https://github.com/your-repo/interview-assistant.git
cd interview-assistant
```

### 2. Setup Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # MacOS/Linux
# venv\Scripts\activate   # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Create Configuration
Create a `.env` file in the root directory and add your Gemini API Key:
```ini
GEMINI_API_KEY=your_api_key_here
```
> 👉 Get API Key at: [Google AI Studio](https://aistudio.google.com/)

---

## 🎧 Setup Audio (Important)

For the AI to hear the interviewer (from Zoom/Meet), you need to configure a **Multi-Output Device** on MacOS:

1.  Open **Audio MIDI Setup** (Search in Spotlight).
2.  Click the `+` icon in the bottom left -> **Create Multi-Output Device**.
3.  Check the boxes for:
    -   ✅ **MacBook Speakers** (or your headphones) -> *So you can hear.*
    -   ✅ **BlackHole 2ch** -> *So the AI can hear.*
    -   (Select Master Device as Speakers/Headphones to control volume).
4.  In MacOS Sound settings (System Settings -> Sound):
    -   Output: Select the **Multi-Output Device** you just created.

---

## 🎮 Usage

1.  Run the application:
    ```bash
    python main.py
    ```
2.  On the Overlay interface:
    -   **Device**: Select **BlackHole 2ch** (to hear the interviewer) or Microphone (to test your voice).
    -   **Language**: Select Vietnamese or English.
3.  Click **Start Listening**.
4.  When the interviewer finishes speaking, the AI will automatically detect, process, and display suggestions on the screen.

---

## ❓ Troubleshooting

-   **No suggestions appearing?**
    -   Check if BlackHole volume in Audio MIDI Setup is Muted.
    -   Ensure you selected the correct Device (BlackHole) in the app.
    -   Check the log on the interface for status (Listening/Processing).

-   **OpenAI/Gemini API Error?**
    -   Check `.env` file and ensure your API Key has quota remaining.

---

<div align="center">
Made with ❤️ by Jason & Gemini
</div>
