import webbrowser
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class NewsItem(QFrame):
    def __init__(self, article: dict, parent=None):
        super().__init__(parent)
        self._link = article.get("link", "")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            NewsItem {
                background: #333; border-radius: 8px; padding: 4px;
            }
            NewsItem:hover { background: #3d3d3d; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        title = QLabel(article.get("title", ""))
        title.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        title.setStyleSheet("color: #7ec8e3; border: none;")
        title.setWordWrap(True)
        layout.addWidget(title)

        summary = QLabel(article.get("summary", "")[:120])
        summary.setFont(QFont("Arial", 9))
        summary.setStyleSheet("color: #aaa; border: none;")
        summary.setWordWrap(True)
        layout.addWidget(summary)

        meta = QLabel(f"{article.get('source', '')} · {article.get('date', '')[:10]}")
        meta.setFont(QFont("Arial", 8))
        meta.setStyleSheet("color: #666; border: none;")
        layout.addWidget(meta)

    def mousePressEvent(self, event):
        if self._link:
            webbrowser.open(self._link)


class NewsPanel(QWidget):
    def __init__(self, event_bus, news_collector, parent=None):
        super().__init__(parent)
        self._event_bus = event_bus
        self._news_collector = news_collector
        self._setup_ui()
        self._connect_events()
        self.hide()

    def _setup_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(360, 480)

        container = QFrame(self)
        container.setGeometry(0, 0, 360, 480)
        container.setStyleSheet("""
            QFrame {
                background: #2b2b2b;
                border: 1px solid #555;
                border-radius: 12px;
            }
        """)

        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Header
        header = QHBoxLayout()
        title = QLabel("📰 AI 新闻")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: #eee; border: none; padding: 4px;")
        header.addWidget(title)
        header.addStretch()

        refresh_btn = QPushButton("刷新")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #4a90d9; color: white; border: none;
                border-radius: 6px; padding: 6px 12px; font-size: 11px;
            }
            QPushButton:hover { background: #5aa0e9; }
        """)
        refresh_btn.clicked.connect(self._refresh)
        header.addWidget(refresh_btn)
        main_layout.addLayout(header)

        # Summary area
        self._summary_label = QLabel("")
        self._summary_label.setFont(QFont("Arial", 10))
        self._summary_label.setStyleSheet("color: #bde0fe; border: none; padding: 6px;")
        self._summary_label.setWordWrap(True)
        self._summary_label.hide()
        main_layout.addWidget(self._summary_label)

        # News list
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { width: 6px; background: transparent; }
            QScrollBar::handle:vertical { background: #555; border-radius: 3px; }
        """)
        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._list_layout.setSpacing(6)
        self._scroll.setWidget(self._list_container)
        main_layout.addWidget(self._scroll, 1)

        # Status
        self._status = QLabel("点击刷新获取最新新闻")
        self._status.setStyleSheet("color: #777; border: none; font-size: 10px;")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self._status)

    def _connect_events(self):
        self._event_bus.news_updated.connect(self._on_news)
        self._event_bus.news_summary_ready.connect(self._on_summary)

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

    def _refresh(self):
        self._status.setText("正在获取新闻...")
        self._news_collector.fetch_now()

    def _on_news(self, articles):
        # Clear existing
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for article in articles:
            self._list_layout.addWidget(NewsItem(article))

        count = len(articles)
        self._status.setText(f"共 {count} 条新闻" if count else "暂无新闻")

    def _on_summary(self, summary):
        self._summary_label.setText(f"📋 AI 摘要：\n{summary}")
        self._summary_label.show()
