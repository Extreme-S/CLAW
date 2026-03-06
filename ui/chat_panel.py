from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QScrollArea, QFrame,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPainter, QPainterPath

from core.config_manager import config
from core.api_client import OpenClawClient

BUBBLE_MAX_WIDTH = 260
BUBBLE_PADDING = 24  # left 12 + right 12


class ChatBubble(QLabel):
    """纯 QLabel 实现的聊天气泡，自绘圆角背景，宽度自适应文字。"""

    def __init__(self, text: str, is_user: bool, parent=None):
        super().__init__(text, parent)
        self._is_user = is_user
        self.setWordWrap(True)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setFont(QFont("PingFang SC", 11))
        self.setContentsMargins(12, 8, 12, 8)

        fm = self.fontMetrics()
        text_width = fm.horizontalAdvance(text) + BUBBLE_PADDING
        self.setFixedWidth(min(text_width, BUBBLE_MAX_WIDTH))
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        if is_user:
            self.setStyleSheet("color: white; background: transparent;")
        else:
            self.setStyleSheet("color: #e0e0e0; background: transparent;")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)

        if self._is_user:
            p.setBrush(QColor("#FB7299"))
        else:
            p.setBrush(QColor("#3a3a3a"))

        path = QPainterPath()
        r = 12.0
        rect = self.rect().toRectF()
        path.addRoundedRect(rect, r, r)
        p.drawPath(path)
        p.end()

        super().paintEvent(event)


class ServerChatWorker(QThread):
    """Streams chat response from OpenClaw server in a background thread."""
    chunk_received = pyqtSignal(str)   # accumulated text so far
    finished = pyqtSignal(str)          # full reply
    error = pyqtSignal(str)

    def __init__(self, client: OpenClawClient, message: str, session_id: str | None):
        super().__init__()
        self._client = client
        self._message = message
        self._session_id = session_id
        self.result_session_id = session_id or ""

    def run(self):
        try:
            result, stream = self._client.chat_stream(
                self._message, self._session_id
            )
            full_text = ""
            for delta in stream:
                full_text += delta
                self.chunk_received.emit(full_text)
            self.result_session_id = result[0] or self.result_session_id
            self.finished.emit(full_text)
        except Exception as e:
            self.error.emit(str(e))


class ChatPanel(QWidget):
    def __init__(self, event_bus, parent=None):
        super().__init__(parent)
        self._event_bus = event_bus
        self._session_id: str | None = None
        self._worker = None

        self._setup_ui()
        self.hide()

    def _setup_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(320, 420)

        container = QWidget(self)
        container.setGeometry(0, 0, 320, 420)
        container.setObjectName("chatContainer")
        container.setStyleSheet("""
            #chatContainer {
                background: #2b2b2b;
                border: 1px solid #555;
                border-radius: 12px;
            }
        """)

        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel("CLAW")
        title.setFont(QFont("PingFang SC", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #eee; padding: 4px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QWidget { background: transparent; }
            QScrollBar:vertical { width: 6px; background: transparent; }
            QScrollBar::handle:vertical { background: #555; border-radius: 3px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)
        self._chat_container = QWidget()
        self._chat_layout = QVBoxLayout(self._chat_container)
        self._chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._chat_layout.setSpacing(8)
        self._chat_layout.setContentsMargins(4, 4, 4, 4)
        self._scroll.setWidget(self._chat_container)
        main_layout.addWidget(self._scroll, 1)

        input_layout = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("说点什么...")
        self._input.setStyleSheet("""
            QLineEdit {
                background: #3a3a3a; color: #eee; border: 1px solid #555;
                border-radius: 8px; padding: 8px; font-size: 12px;
            }
        """)
        self._input.returnPressed.connect(self._send)
        input_layout.addWidget(self._input)

        self._send_btn = QPushButton("发送")
        self._send_btn.setStyleSheet("""
            QPushButton {
                background: #00A1D6; color: white; border: none;
                border-radius: 8px; padding: 8px 14px; font-weight: bold;
            }
            QPushButton:hover { background: #00B8F0; }
        """)
        self._send_btn.clicked.connect(self._send)
        input_layout.addWidget(self._send_btn)
        main_layout.addLayout(input_layout)

    def show_near(self, tv_widget):
        tv_pos = tv_widget.pos()
        x = tv_pos.x() - self.width() - 10
        if x < 0:
            x = tv_pos.x() + tv_widget.width() + 10
        y = tv_pos.y()
        self.move(x, y)
        self.show()
        from core.macos_topmost import elevate_window
        elevate_window(self)
        self._input.setFocus()

    def _set_input_enabled(self, enabled):
        self._input.setEnabled(enabled)
        self._send_btn.setEnabled(enabled)
        self._input.setPlaceholderText("说点什么..." if enabled else "等待回复中...")

    def _create_client(self) -> OpenClawClient | None:
        url = config.get("server", "url")
        token = config.get("server", "token")
        if not url:
            return None
        return OpenClawClient(url, token or "")

    def _send(self):
        text = self._input.text().strip()
        if not text or self._worker is not None:
            return
        self._input.clear()

        self._add_bubble(text, is_user=True)

        # Water keyword shortcut
        water_keywords = ("喝水", "提醒喝水", "drink water", "补水")
        if any(kw in text.lower() for kw in water_keywords):
            self._event_bus.water_reminder_triggered.emit()
            self._add_bubble("好的！已经提醒你喝水啦～记得补充水分哦", is_user=False)
            return

        client = self._create_client()
        if not client:
            self._add_bubble("请先在设置中配置服务器地址。", is_user=False)
            return

        self._set_input_enabled(False)

        self._streaming_bubble = self._add_bubble("...", is_user=False)
        self._streaming_bubble.setFixedWidth(BUBBLE_MAX_WIDTH)

        self._worker = ServerChatWorker(client, text, self._session_id)
        self._worker.chunk_received.connect(self._on_chunk)
        self._worker.finished.connect(self._on_stream_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

        self._event_bus.chat_request_sent.emit(text)

    def _on_chunk(self, text_so_far):
        if self._streaming_bubble:
            self._streaming_bubble.setText(text_so_far)
            self._streaming_bubble.adjustSize()
            QTimer.singleShot(10, self._scroll_to_bottom)

    def _on_stream_done(self, full_text):
        # Update session_id from server response
        if self._worker:
            self._session_id = self._worker.result_session_id or self._session_id

        if self._streaming_bubble:
            fm = self._streaming_bubble.fontMetrics()
            text_width = fm.horizontalAdvance(full_text) + BUBBLE_PADDING
            self._streaming_bubble.setFixedWidth(min(text_width, BUBBLE_MAX_WIDTH))
            self._streaming_bubble.adjustSize()
        self._streaming_bubble = None
        self._worker = None
        self._set_input_enabled(True)
        self._input.setFocus()
        self._event_bus.chat_message_received.emit(full_text)

    def _on_error(self, err):
        if self._streaming_bubble:
            self._streaming_bubble.setText(f"出错了: {err}")
            self._streaming_bubble = None
        else:
            self._add_bubble(f"出错了: {err}", is_user=False)
        self._worker = None
        self._set_input_enabled(True)
        self._input.setFocus()

    def _add_bubble(self, text, is_user):
        bubble = ChatBubble(text, is_user)
        wrapper = QHBoxLayout()
        wrapper.setContentsMargins(0, 0, 0, 0)
        if is_user:
            wrapper.addStretch()
            wrapper.addWidget(bubble)
        else:
            wrapper.addWidget(bubble)
            wrapper.addStretch()
        self._chat_layout.addLayout(wrapper)
        QTimer.singleShot(50, self._scroll_to_bottom)
        return bubble

    def _scroll_to_bottom(self):
        sb = self._scroll.verticalScrollBar()
        sb.setValue(sb.maximum())
