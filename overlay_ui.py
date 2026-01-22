from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                             QLabel, QTextEdit, QPushButton, QHBoxLayout, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette, QFont

class OverlayUI(QMainWindow):
    start_recording_signal = pyqtSignal()
    stop_recording_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.old_pos = None

    def init_ui(self):
        self.setWindowTitle("Interview Assistant")
        self.setGeometry(100, 100, 400, 300)
        
        # Window flags for floating overlay
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Central widget customization
        self.central_widget = QWidget()
        self.central_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 30, 220);
                border-radius: 10px;
                color: white;
            }
            QPushButton {
                background-color: #4CAF50; 
                border: none;
                color: white;
                padding: 5px 10px;
                text-align: center;
                text-decoration: none;
                font-size: 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton#stopBtn {
                background-color: #f44336;
            }
            QPushButton#stopBtn:hover {
                background-color: #da190b;
            }
            QComboBox {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                font-size: 11px;
                padding: 2px;
            }
        """)
        self.setCentralWidget(self.central_widget)

        layout = QVBoxLayout()
        
        # Header (Drag handle + Title + Language)
        header_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-weight: bold; color: #aaa;")
        header_layout.addWidget(self.status_label)
        
        header_layout.addStretch()

        # Language Selector
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["English", "Vietnamese"])
        header_layout.addWidget(self.lang_combo)

        # Device Selector
        self.device_combo = QComboBox()
        self.device_combo.setToolTip("Select Input Device (e.g. BlackHole for System Audio)")
        # We will populate this from main.py or audio_recorder
        header_layout.addWidget(self.device_combo)
        
        # Close button
        self.close_btn = QPushButton("X")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setStyleSheet("background-color: transparent; color: #aaa; font-weight: bold;")
        self.close_btn.clicked.connect(self.close)
        header_layout.addWidget(self.close_btn)
        
        layout.addLayout(header_layout)

        # Suggestion Box
        self.suggestion_box = QTextEdit()
        self.suggestion_box.setReadOnly(True)
        self.suggestion_box.setPlaceholderText("Suggestions will appear here...")
        self.suggestion_box.setStyleSheet("background-color: rgba(0, 0, 0, 50); border: none; font-size: 14px;")
        layout.addWidget(self.suggestion_box)

        # Log Box (New)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText("System Logs...")
        self.log_box.setMaximumHeight(100) # Keep it small
        self.log_box.setStyleSheet("""
            background-color: rgba(0, 0, 0, 80); 
            border: 1px solid #444; 
            color: #ddd; 
            font-size: 10px; 
            font-family: monospace;
        """)
        layout.addWidget(self.log_box)

        # Controls
        controls_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start Listening")
        self.start_btn.clicked.connect(self.start_listening)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.clicked.connect(self.stop_listening)
        self.stop_btn.setEnabled(False)

        controls_layout.addWidget(self.start_btn)
        controls_layout.addWidget(self.stop_btn)
        layout.addLayout(controls_layout)

        self.central_widget.setLayout(layout)

    def get_selected_language(self):
        return self.lang_combo.currentText()

    def get_selected_device_index(self):
        # We store the device index as user data in the combo box item
        return self.device_combo.currentData()

    def append_log(self, text):
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"[{timestamp}] {text}")
        sb = self.log_box.verticalScrollBar()
        sb.setValue(sb.maximum())

    def start_listening(self):
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("Listening...")
        self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        self.append_log(f"Started listening. Target Language: {self.get_selected_language()}")
        self.start_recording_signal.emit()

    def stop_listening(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Stopped")
        self.status_label.setStyleSheet("font-weight: bold; color: #f44336;")
        self.stop_recording_signal.emit()

    def update_status(self, text, color="#aaa"):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"font-weight: bold; color: {color};")

    def append_suggestion(self, text):
        self.suggestion_box.append(f"\n> {text}")
        # Scroll to bottom
        sb = self.suggestion_box.verticalScrollBar()
        sb.setValue(sb.maximum())

    # Mouse events for dragging the window
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None
