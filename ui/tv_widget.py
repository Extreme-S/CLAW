import math
from PyQt6.QtWidgets import QWidget, QMenu
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, QPoint
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPainterPath, QAction,
    QLinearGradient, QPolygonF,
)

# ---------------------------------------------------------------------------
# 画布 & 坐标
# ---------------------------------------------------------------------------
# Web SVG viewBox = 0 0 220 220，桌面缩放到 120x120
TV_W, TV_H = 120, 120
S = TV_W / 220.0  # ≈0.545 缩放因子

# SVG 中心 110,110 → 桌面中心
CX = 110 * S  # 60
CY = 110 * S  # 60

# ---------------------------------------------------------------------------
# 颜色（与网页端 CSS 变量一致）
# ---------------------------------------------------------------------------
CYAN = QColor(0, 229, 255)          # #00e5ff
PURPLE = QColor(124, 77, 255)       # #7c4dff
DARK_BG = QColor(10, 22, 40)        # #0a1628
PINK = QColor(255, 64, 129)         # chat 模式
ORANGE = QColor(255, 171, 64)       # reminder 模式


def _sv(x, y=None):
    """将 SVG 坐标 (220 空间) 映射到桌面像素。"""
    if y is None:
        return x * S
    return QPointF(x * S, y * S)


class TVWidget(QWidget):
    """赛博朋克 CLAW 桌面宠物 — 与网页端 Logo 完全一致。"""

    def __init__(self, event_bus, parent=None):
        super().__init__(parent)
        self._event_bus = event_bus
        self._mode = "idle"
        self._screen_text = ""
        self._frame = 0
        self._drag_pos = None
        self._bounce_y = 0.0

        # 动画
        self._ring_angle = 0.0
        self._eye_pulse = 0.0  # 0~1

        self._chat_panel = None
        self._news_panel = None
        self._bubble = None
        self._dragged = False
        self._chat_open = False

        self._setup_window()
        self._setup_timers()
        self._connect_events()

    # ------------------------------------------------------------------ setup
    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(TV_W, TV_H)
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.x() + screen.width() - TV_W - 60
        y = screen.y() + screen.height() - TV_H - 40
        self.move(x, y)

    def _setup_timers(self):
        self._frame_timer = QTimer(self)
        self._frame_timer.timeout.connect(self._tick)
        self._frame_timer.start(40)  # ~25 fps

    def _connect_events(self):
        self._event_bus.mode_changed.connect(self.set_mode)
        self._event_bus.water_reminder_triggered.connect(self._on_water_reminder)

    def showEvent(self, event):
        super().showEvent(event)
        from core.macos_topmost import elevate_window
        elevate_window(self)

    def set_mode(self, mode):
        self._mode = mode
        self._screen_text = ""
        self.update()

    def set_screen_text(self, text):
        self._screen_text = text
        self.update()

    def _tick(self):
        self._frame += 1
        self._bounce_y = 3.0 * math.sin(self._frame * 0.045)
        self._ring_angle = (self._frame * 1.5) % 360
        self._eye_pulse = 0.5 + 0.5 * math.sin(self._frame * 0.08)
        self.update()

    def _on_water_reminder(self):
        import random
        from features.water_reminder import WATER_MESSAGES
        msg = random.choice(WATER_MESSAGES)
        self.show_bubble(msg)

    def show_bubble(self, text, duration=5000):
        if self._bubble:
            self._bubble.show_message(text, self, duration)

    # ================================================================ 渐变工具
    def _claw_gradient(self, x1, y1, x2, y2):
        """复现 SVG linearGradient #clawGrad: cyan → purple 对角线。"""
        g = QLinearGradient(_sv(x1, y1), _sv(x2, y2))
        g.setColorAt(0.0, CYAN)
        g.setColorAt(1.0, PURPLE)
        return g

    def _ring_gradient(self, x1, y1, x2, y2):
        """复现 SVG linearGradient #ringGrad。"""
        g = QLinearGradient(_sv(x1, y1), _sv(x2, y2))
        c0 = QColor(CYAN); c0.setAlpha(204)   # 0.8
        c1 = QColor(PURPLE); c1.setAlpha(102)  # 0.4
        c2 = QColor(CYAN); c2.setAlpha(204)
        g.setColorAt(0.0, c0)
        g.setColorAt(0.5, c1)
        g.setColorAt(1.0, c2)
        return g

    # ================================================================ PAINTING
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.translate(0, self._bounce_y)

        self._draw_outer_dash_ring(p)   # 最外旋转虚线环
        self._draw_main_ring(p)         # 外圆主环
        self._draw_inner_dash_ring(p)   # 内圆虚线环（反向）
        # 六边形及内部整体放大 1.15x（以中心为原点）
        p.save()
        p.translate(CX, CY)
        p.scale(1.05, 1.05)
        p.translate(-CX, -CY)
        p.translate(0, _sv(10))         # 整体下移，仍保持中上方
        self._draw_hexagon(p)           # 六边形底座
        self._draw_circuit_lines(p)     # 电路装饰线
        self._draw_claws(p)             # 三指机械爪
        self._draw_joints(p)            # 关节点 + 连接线
        self._draw_eye(p)               # AI 之眼
        p.restore()
        self._draw_label(p)             # CLAW 文字
        self._draw_ticks(p)             # 刻度标记

        p.end()

    # ---- 最外旋转虚线环  SVG: r=106 dasharray="6 10" opacity=0.3 ----
    def _draw_outer_dash_ring(self, p: QPainter):
        r = _sv(106)
        p.save()
        p.translate(CX, CY)
        p.rotate(self._ring_angle)
        pen = QPen(QBrush(self._ring_gradient(0, 0, 220, 220)), _sv(1))
        pen.setDashPattern([6, 10])
        p.setPen(pen)
        p.setOpacity(0.3)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(0, 0), r, r)
        p.restore()

    # ---- 外圆主环  SVG: r=96 stroke=clawGrad width=2 ----
    def _draw_main_ring(self, p: QPainter):
        r = _sv(96)
        pen = QPen(QBrush(self._claw_gradient(0, 0, 220, 220)), _sv(2))
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(CX, CY), r, r)

    # ---- 内圆虚线环  SVG: r=89 dasharray="4 8" opacity=0.25 反向 ----
    def _draw_inner_dash_ring(self, p: QPainter):
        r = _sv(89)
        p.save()
        p.translate(CX, CY)
        p.rotate(-self._ring_angle * 0.72)  # 反向、稍慢 (25/18≈1.39, 1/1.39≈0.72)
        pen = QPen(QBrush(self._ring_gradient(0, 0, 220, 220)), _sv(0.8))
        pen.setDashPattern([4, 8])
        p.setPen(pen)
        p.setOpacity(0.25)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(0, 0), r, r)
        p.restore()

    # ---- 六边形底座  SVG: points="110,20 164,51 164,113 110,144 56,113 56,51" ----
    def _draw_hexagon(self, p: QPainter):
        pts = QPolygonF([
            _sv(110, 20), _sv(164, 51), _sv(164, 113),
            _sv(110, 144), _sv(56, 113), _sv(56, 51),
        ])
        p.setBrush(DARK_BG)
        p.setPen(QPen(QBrush(self._claw_gradient(0, 0, 220, 220)), _sv(1.5)))
        p.drawPolygon(pts)

    # ---- 电路装饰线  SVG 四条线 opacity=0.2 ----
    def _draw_circuit_lines(self, p: QPainter):
        pen = QPen(CYAN, _sv(0.7))
        p.setPen(pen)
        p.setOpacity(0.2)
        p.drawLine(_sv(76, 53), _sv(76, 82))
        p.drawLine(_sv(144, 53), _sv(144, 82))
        p.drawLine(_sv(76, 82), _sv(92, 82))
        p.drawLine(_sv(144, 82), _sv(128, 82))
        p.setOpacity(1.0)

    # ---- 三指机械爪  SVG: 三个 path 填充 clawGrad opacity=0.95 ----
    def _draw_claws(self, p: QPainter):
        grad = self._claw_gradient(0, 0, 220, 220)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.setOpacity(0.95)

        # 上爪  M110 30 L101 57 L110 50 L119 57 Z
        top = QPainterPath()
        top.moveTo(_sv(110, 30))
        top.lineTo(_sv(101, 57))
        top.lineTo(_sv(110, 50))
        top.lineTo(_sv(119, 57))
        top.closeSubpath()
        p.drawPath(top)

        # 左下爪  M56 120 L78 102 L74 94 L59 109 Z
        left = QPainterPath()
        left.moveTo(_sv(56, 120))
        left.lineTo(_sv(78, 102))
        left.lineTo(_sv(74, 94))
        left.lineTo(_sv(59, 109))
        left.closeSubpath()
        p.drawPath(left)

        # 右下爪  M164 120 L142 102 L146 94 L161 109 Z
        right = QPainterPath()
        right.moveTo(_sv(164, 120))
        right.lineTo(_sv(142, 102))
        right.lineTo(_sv(146, 94))
        right.lineTo(_sv(161, 109))
        right.closeSubpath()
        p.drawPath(right)

        p.setOpacity(1.0)

    # ---- 关节点 + 连接线 ----
    def _draw_joints(self, p: QPainter):
        joints = [(110, 57), (76, 99), (144, 99)]
        # 连接线到中心眼区域  opacity=0.4
        targets = [(110, 72), (91, 91), (129, 91)]
        line_pen = QPen(CYAN, _sv(1.2))
        p.setOpacity(0.4)
        p.setPen(line_pen)
        for (jx, jy), (tx, ty) in zip(joints, targets):
            p.drawLine(_sv(jx, jy), _sv(tx, ty))
        p.setOpacity(1.0)

        # 关节圆点  r=2.5 opacity=0.7
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(CYAN)
        p.setOpacity(0.7)
        for jx, jy in joints:
            p.drawEllipse(_sv(jx, jy), _sv(2.5), _sv(2.5))
        p.setOpacity(1.0)

    # ---- AI 之眼 ----
    def _draw_eye(self, p: QPainter):
        # SVG 眼中心 (110, 88)
        ex, ey = 110, 88

        # 模式颜色
        if self._mode == "chat":
            accent = PINK
        elif self._mode == "reminder":
            accent = ORANGE
        else:
            accent = CYAN

        pulse = self._eye_pulse  # 0~1

        # 外环  r=20 stroke=clawGrad width=1.8  fill=DARK
        p.setBrush(DARK_BG)
        p.setPen(QPen(QBrush(self._claw_gradient(0, 0, 220, 220)), _sv(1.8)))
        p.drawEllipse(_sv(ex, ey), _sv(20), _sv(20))

        # 脉冲环  r: 12→16  opacity: 0.4→0.1
        pulse_r = _sv(12 + 4 * pulse)
        pulse_opacity = 0.4 - 0.3 * pulse
        p.setPen(QPen(accent, _sv(0.8)))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setOpacity(max(pulse_opacity, 0.05))
        p.drawEllipse(_sv(ex, ey), pulse_r, pulse_r)
        p.setOpacity(1.0)

        # 核心亮球  r: 7→9  opacity: 1→0.5
        core_r = _sv(7 + 2 * pulse)
        core_opacity = 1.0 - 0.5 * pulse
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(accent)
        p.setOpacity(core_opacity)
        p.drawEllipse(_sv(ex, ey), core_r, core_r)
        p.setOpacity(1.0)

    # ---- CLAW 文字  SVG: x=110 y=172 font-size=13 letter-spacing=6 opacity=0.7 ----
    def _draw_label(self, p: QPainter):
        p.setOpacity(0.7)
        font = QFont("Menlo", max(int(13 * S), 6), QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 6 * S)
        p.setFont(font)
        p.setPen(CYAN)
        text_rect = QRectF(0, _sv(162), TV_W, _sv(20))
        p.drawText(text_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, "CLAW")
        p.setOpacity(1.0)

    # ---- 刻度标记  SVG: 4 条线 opacity=0.25 ----
    def _draw_ticks(self, p: QPainter):
        p.setOpacity(0.25)
        pen = QPen(CYAN, _sv(1))
        p.setPen(pen)
        # 上: (110,14)→(110,20)
        p.drawLine(_sv(110, 14), _sv(110, 20))
        # 下: (110,200)→(110,206)
        p.drawLine(_sv(110, 200), _sv(110, 206))
        # 左: (14,110)→(20,110)
        p.drawLine(_sv(14, 110), _sv(20, 110))
        # 右: (200,110)→(206,110)
        p.drawLine(_sv(200, 110), _sv(206, 110))
        p.setOpacity(1.0)

    # ================================================================ MOUSE
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._dragged = False
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            old_pos = self.pos()
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            delta = new_pos - old_pos
            if abs(delta.x()) > 2 or abs(delta.y()) > 2:
                self._dragged = True
            self.move(new_pos)
            for panel in (self._chat_panel, self._news_panel, self._bubble):
                if panel and panel.isVisible():
                    panel.move(panel.pos() + delta)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self._dragged:
            self._on_click()
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        self._dragged = True
        self._toggle_chat()

    def _on_click(self):
        import random
        msgs = [
            "系统就绪，等待指令。",
            "CLAW 在线，有何需要？",
            "别戳了，我的传感器很灵敏的 >_<",
            "所有系统正常运行中。",
            "嘿，记得喝水，这是命令。",
            "今天也要高效运转！",
            "CLAW 24h 待命，随时响应。",
            "检测到你的注意力，已记录。",
            "陪你写代码的第 N 天～",
            "建议休息一下，眼睛会累的。",
            "叮，一条来自 CLAW 的问候。",
            "你今天的状态不错，继续保持。",
            "双击我进入对话模式。",
            "数据分析中... 你超棒的。",
            "认知引擎已就绪，awaiting input.",
        ]
        self.show_bubble(random.choice(msgs), 4000)

    def _show_context_menu(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #0a1628; color: #00e5ff;
                border: 1px solid #00e5ff;
                border-radius: 8px; padding: 6px;
                font-family: "Menlo";
            }
            QMenu::item { padding: 6px 20px; border-radius: 4px; }
            QMenu::item:selected { background: #7c4dff; color: white; }
            QMenu::separator { height: 1px; background: #1a3050; margin: 4px 8px; }
        """)

        chat_action = QAction("聊天", self)
        chat_action.triggered.connect(self._toggle_chat)
        menu.addAction(chat_action)

        news_action = QAction("新闻", self)
        news_action.triggered.connect(self._toggle_news)
        menu.addAction(news_action)

        menu.addSeparator()

        water_action = QAction("我喝水了", self)
        water_action.triggered.connect(lambda: self._event_bus.water_drunk.emit(0))
        menu.addAction(water_action)

        menu.addSeparator()

        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        menu.exec(event.globalPosition().toPoint())

    def _toggle_chat(self):
        if self._chat_panel:
            if self._chat_panel.isVisible():
                self._chat_panel.hide()
                self._chat_open = False
                self.update()
            else:
                self._chat_open = True
                self.update()
                self._chat_panel.show_near(self)

    def _toggle_news(self):
        if self._news_panel:
            if self._news_panel.isVisible():
                self._news_panel.hide()
                self._event_bus.mode_changed.emit("idle")
            else:
                self._news_panel.show_near(self)
                self._event_bus.mode_changed.emit("news")

    def _quit(self):
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()
