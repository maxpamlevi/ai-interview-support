# 🎙️ AI Interview Assistant

[Read in English](README.md)

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Gemini](https://img.shields.io/badge/AI-Gemini_2.0-orange?style=for-the-badge&logo=google)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green?style=for-the-badge&logo=qt)

**Hệ thống hỗ trợ phỏng vấn thời gian thực sử dụng AI**
*Nhận diện câu hỏi - Gợi ý câu trả lời thông minh - Tối ưu hóa độ trễ*

</div>

---

## ✨ Features

- **Real-time Audio Capture**: Thu âm trực tiếp từ hệ thống (Zoom, Google Meet, Teams) hoặc Microphone.
- **Smart VAD (Voice Activity Detection)**: Tự động loại bỏ khoảng lặng, chỉ xử lý giọng nói thực.
- **Gemini 2.0 Integration**: Phân tích câu hỏi và gợi ý câu trả lời chuyên nghiệp trong tích tắc.
- **Floating Overlay UI**: Giao diện trong suốt, luôn nổi trên cùng, hiển thị gợi ý mà không che khuất màn hình phỏng vấn.
- **Multi-language Support**: Hỗ trợ tốt cả Tiếng Anh và Tiếng Việt.

## 🛠️ Prerequisites

Trước khi cài đặt, hãy đảm bảo bạn đã có:

1.  **Python 3.10+**: [Download here](https://www.python.org/downloads/)

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
Tạo file `.env` tại thư mục gốc và thêm API Key Gemini của bạn:
```ini
GEMINI_API_KEY=your_api_key_here
```
> 👉 Lấy API Key tại: [Google AI Studio](https://aistudio.google.com/)

---



## 🎮 Usage

1.  Chạy ứng dụng:
    ```bash
    python main.py
    ```
2.  Trên giao diện Overlay:
    -   **Device**: Chọn **System Audio** (để nghe người phỏng vấn) hoặc Microphone (để test giọng bạn).
    -   **Language**: Chọn Tiếng Việt hoặc English.
3.  Nhấn **Start Listening**.
4.  Khi người phỏng vấn nói xong, AI sẽ tự động phát hiện, xử lý và hiện gợi ý lên màn hình.

---

## ❓ Troubleshooting

-   **Không thấy gợi ý hiện ra?**
    -   Đảm bảo bạn đã chọn đúng Device trong app.
    -   Xem log trên giao diện để biết trạng thái (Listening/Processing).

-   **Lỗi OpenAI/Gemini API?**
    -   Kiểm tra lại file `.env` và chắc chắn API Key còn hạn mức.

---

<div align="center">
Made with ❤️ by Jason & Gemini
</div>
