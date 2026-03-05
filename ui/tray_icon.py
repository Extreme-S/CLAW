from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QAction, QPolygonF
from PyQt6.QtCore import Qt, QRectF, QPointF


def _generate_claw_icon(size=64):
    """Generate a cyberpunk CLAW icon using QPainter."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    s = size
    CYAN = QColor(0, 229, 255)
    DARK = QColor(10, 22, 40)

    # Outer ring
    p.setPen(QPen(CYAN, 1.5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QPointF(s * 0.5, s * 0.5), s * 0.42, s * 0.42)

    # Inner circle (dark)
    p.setPen(QPen(CYAN, 1.2))
    p.setBrush(DARK)
    p.drawEllipse(QPointF(s * 0.5, s * 0.5), s * 0.35, s * 0.35)

    # Three claw fingers
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(CYAN)

    # Top claw
    top_claw = QPolygonF([
        QPointF(s * 0.5, s * 0.15),
        QPointF(s * 0.44, s * 0.35),
        QPointF(s * 0.5, s * 0.31),
        QPointF(s * 0.56, s * 0.35),
    ])
    p.drawPolygon(top_claw)

    # Bottom-left claw
    bl_claw = QPolygonF([
        QPointF(s * 0.2, s * 0.72),
        QPointF(s * 0.36, s * 0.6),
        QPointF(s * 0.34, s * 0.54),
        QPointF(s * 0.24, s * 0.64),
    ])
    p.drawPolygon(bl_claw)

    # Bottom-right claw
    br_claw = QPolygonF([
        QPointF(s * 0.8, s * 0.72),
        QPointF(s * 0.64, s * 0.6),
        QPointF(s * 0.66, s * 0.54),
        QPointF(s * 0.76, s * 0.64),
    ])
    p.drawPolygon(br_claw)

    # Center eye
    p.setPen(QPen(CYAN, 1.5))
    p.setBrush(DARK)
    p.drawEllipse(QPointF(s * 0.5, s * 0.5), s * 0.11, s * 0.11)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(CYAN)
    p.drawEllipse(QPointF(s * 0.5, s * 0.5), s * 0.05, s * 0.05)

    p.end()
    return QIcon(pixmap)


class TrayIcon(QSystemTrayIcon):
    def __init__(self, tv_widget, event_bus, parent=None):
        super().__init__(parent)
        self._tv = tv_widget
        self._event_bus = event_bus

        self.setIcon(_generate_claw_icon())
        self.setToolTip("CLAW — AI 私人助手")
        self._build_menu()
        self.activated.connect(self._on_activated)

    def _build_menu(self):
        menu = QMenu()

        show_action = QAction("显示 CLAW", menu)
        show_action.triggered.connect(self._tv.show)
        menu.addAction(show_action)

        menu.addSeparator()

        chat_action = QAction("💬 聊天", menu)
        chat_action.triggered.connect(self._tv._toggle_chat)
        menu.addAction(chat_action)

        news_action = QAction("📰 新闻", menu)
        news_action.triggered.connect(self._tv._toggle_news)
        menu.addAction(news_action)

        menu.addSeparator()

        settings_action = QAction("⚙ 设置", menu)
        settings_action.triggered.connect(self._open_settings)
        menu.addAction(settings_action)

        menu.addSeparator()

        quit_action = QAction("退出", menu)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self._tv.isVisible():
                self._tv.hide()
            else:
                self._tv.show()
                self._tv.raise_()

    def _open_settings(self):
        from ui.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self._event_bus)
        dlg.exec()

    def _quit(self):
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()
