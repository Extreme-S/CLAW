from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath, QFont


class BubbleToast(QWidget):
    """小电视头顶弹出的气泡消息，带三角尖角指向小电视。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(180, 80)

        self._text = ""
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(1.0)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._fade_out)

    def show_message(self, text, tv_widget, duration=5000):
        """在 tv_widget 上方弹出气泡。"""
        self._text = text

        # 定位：小电视正上方居中
        tv_pos = tv_widget.pos()
        tv_w = tv_widget.width()
        x = tv_pos.x() + tv_w // 2 - self.width() // 2
        y = tv_pos.y() - self.height() + 6
        self.move(x, y)

        self._opacity_effect.setOpacity(1.0)
        self.show()
        from core.macos_topmost import elevate_window
        elevate_window(self)
        self.update()

        # 弹入动画：从下方滑入
        self._anim = QPropertyAnimation(self, b"pos")
        self._anim.setDuration(300)
        self._anim.setStartValue(QPoint(x, y + 20))
        self._anim.setEndValue(QPoint(x, y))
        self._anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self._anim.start()

        self._hide_timer.start(duration)

    def _fade_out(self):
        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(500)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InQuad)
        self._fade_anim.finished.connect(self.hide)
        self._fade_anim.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        arrow_h = 10
        bubble_rect = 0, 0, w, h - arrow_h

        # 气泡路径（圆角矩形 + 底部三角箭头）
        path = QPainterPath()
        r = 14
        bx, by, bw, bh = bubble_rect
        path.addRoundedRect(float(bx), float(by), float(bw), float(bh), r, r)

        # 底部小三角
        arrow_cx = w / 2
        arrow = QPainterPath()
        arrow.moveTo(arrow_cx - 8, bh)
        arrow.lineTo(arrow_cx, bh + arrow_h)
        arrow.lineTo(arrow_cx + 8, bh)
        arrow.closeSubpath()
        path = path.united(arrow)

        # 阴影
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 20))
        p.translate(1, 2)
        p.drawPath(path)
        p.translate(-1, -2)

        # 白色气泡 + 蓝色边框
        p.setBrush(QColor(255, 255, 255))
        p.setPen(QPen(QColor(0, 161, 214), 2))
        p.drawPath(path)

        # 文字
        p.setPen(QColor(51, 51, 51))
        p.setFont(QFont("PingFang SC", 12))
        text_rect = path.boundingRect().adjusted(12, 6, -12, -arrow_h - 4)
        p.drawText(text_rect.toRect(),
                   Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                   self._text)

        p.end()
