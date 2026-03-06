from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QComboBox, QSpinBox, QCheckBox,
    QPushButton, QTextEdit, QFormLayout, QGroupBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from core.config_manager import config

STYLE = """
    QDialog { background: #2b2b2b; color: #eee; }
    QTabWidget::pane { border: 1px solid #555; background: #2b2b2b; }
    QTabBar::tab { background: #333; color: #aaa; padding: 8px 16px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
    QTabBar::tab:selected { background: #2b2b2b; color: #eee; }
    QLabel { color: #ddd; }
    QLineEdit, QComboBox, QSpinBox, QTextEdit {
        background: #3a3a3a; color: #eee; border: 1px solid #555;
        border-radius: 4px; padding: 4px;
    }
    QCheckBox { color: #ddd; }
    QCheckBox::indicator { width: 16px; height: 16px; }
    QPushButton {
        background: #4a90d9; color: white; border: none;
        border-radius: 6px; padding: 8px 20px; font-weight: bold;
    }
    QPushButton:hover { background: #5aa0e9; }
    QGroupBox { color: #bbb; border: 1px solid #444; border-radius: 6px; margin-top: 8px; padding-top: 16px; }
    QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
"""


class SettingsDialog(QDialog):
    def __init__(self, event_bus, parent=None):
        super().__init__(parent)
        self._event_bus = event_bus
        self.setWindowTitle("CLAW 设置")
        self.setFixedSize(480, 420)
        self.setStyleSheet(STYLE)
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_general_tab(), "通用")
        self._tabs.addTab(self._build_ai_tab(), "服务器")
        self._tabs.addTab(self._build_water_tab(), "喝水提醒")
        self._tabs.addTab(self._build_news_tab(), "新闻源")
        layout.addWidget(self._tabs)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("background: #555;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _build_general_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(12)

        self._lang_combo = QComboBox()
        self._lang_combo.addItems(["中文", "English"])
        form.addRow("语言:", self._lang_combo)

        self._start_minimized = QCheckBox("启动时最小化到托盘")
        form.addRow("", self._start_minimized)

        return w

    def _build_ai_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        # Server connection
        server_group = QGroupBox("OpenClaw 服务器")
        server_form = QFormLayout(server_group)
        self._server_url = QLineEdit()
        self._server_url.setPlaceholderText("http://localhost:8000")
        server_form.addRow("服务器地址:", self._server_url)
        self._server_token = QLineEdit()
        self._server_token.setEchoMode(QLineEdit.EchoMode.Password)
        self._server_token.setPlaceholderText("认证令牌")
        server_form.addRow("Token:", self._server_token)
        layout.addWidget(server_group)

        layout.addStretch()
        return w

    def _build_water_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(12)

        self._water_enabled = QCheckBox("启用喝水提醒")
        form.addRow("", self._water_enabled)

        self._water_interval = QSpinBox()
        self._water_interval.setRange(5, 240)
        self._water_interval.setSuffix(" 分钟")
        form.addRow("提醒间隔:", self._water_interval)

        return w

    def _build_news_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        self._news_enabled = QCheckBox("启用每日新闻")
        layout.addWidget(self._news_enabled)

        hour_layout = QHBoxLayout()
        hour_layout.addWidget(QLabel("每日获取时间:"))
        self._news_hour = QSpinBox()
        self._news_hour.setRange(0, 23)
        self._news_hour.setSuffix(" 点")
        hour_layout.addWidget(self._news_hour)
        hour_layout.addStretch()
        layout.addLayout(hour_layout)

        layout.addWidget(QLabel("RSS 源 (每行一个):"))
        self._rss_feeds = QTextEdit()
        self._rss_feeds.setMaximumHeight(100)
        layout.addWidget(self._rss_feeds)

        newsapi_layout = QFormLayout()
        self._newsapi_key = QLineEdit()
        self._newsapi_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._newsapi_key.setPlaceholderText("可选，留空则仅使用RSS")
        newsapi_layout.addRow("NewsAPI Key:", self._newsapi_key)
        layout.addLayout(newsapi_layout)

        layout.addWidget(QLabel("搜索关键词 (逗号分隔):"))
        self._keywords = QLineEdit()
        self._keywords.setPlaceholderText("AI, 人工智能, LLM, GPT")
        layout.addWidget(self._keywords)

        layout.addStretch()
        return w

    def _load_values(self):
        # General
        lang = config.get("general", "language")
        self._lang_combo.setCurrentIndex(0 if lang == "zh" else 1)
        self._start_minimized.setChecked(config.get("general", "start_minimized") or False)

        # Server
        self._server_url.setText(config.get("server", "url") or "")
        self._server_token.setText(config.get("server", "token") or "")

        # Water
        self._water_enabled.setChecked(config.get("water_reminder", "enabled") or False)
        self._water_interval.setValue(config.get("water_reminder", "interval_minutes") or 45)

        # News
        self._news_enabled.setChecked(config.get("news", "enabled") or False)
        self._news_hour.setValue(config.get("news", "schedule_hour") or 9)
        feeds = config.get("news", "rss_feeds") or []
        self._rss_feeds.setPlainText("\n".join(feeds))
        self._newsapi_key.setText(config.get("news", "newsapi_key") or "")
        keywords = config.get("news", "keywords") or []
        self._keywords.setText(", ".join(keywords))

    def _save(self):
        # General
        config.set("general", "language", "zh" if self._lang_combo.currentIndex() == 0 else "en")
        config.set("general", "start_minimized", self._start_minimized.isChecked())

        # Server
        config.set("server", "url", self._server_url.text().strip() or "http://localhost:8000")
        config.set("server", "token", self._server_token.text().strip())

        # Water
        config.set("water_reminder", "enabled", self._water_enabled.isChecked())
        config.set("water_reminder", "interval_minutes", self._water_interval.value())

        # News
        config.set("news", "enabled", self._news_enabled.isChecked())
        config.set("news", "schedule_hour", self._news_hour.value())
        feeds = [f.strip() for f in self._rss_feeds.toPlainText().split("\n") if f.strip()]
        config.set("news", "rss_feeds", feeds)
        config.set("news", "newsapi_key", self._newsapi_key.text().strip())
        keywords = [k.strip() for k in self._keywords.text().split(",") if k.strip()]
        config.set("news", "keywords", keywords)

        self._event_bus.settings_changed.emit()
        self.accept()
