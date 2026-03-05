import math
import random
from PyQt6.QtWidgets import QWidget, QMenu
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, pyqtProperty
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPainterPath, QAction,
)

# Canvas size — 小巧版
TV_W, TV_H = 100, 120

# B站经典蓝
BILI = QColor(0, 161, 214)       # #00A1D6
BILI_DARK = QColor(0, 130, 180)
WHITE = QColor(255, 255, 255)

# 机身区域（粗圆角矩形）
BODY = QRectF(10, 30, 80, 62)
BODY_R = 12  # 圆角半径


class TVWidget(QWidget):
    """B站经典小电视桌面宠物。"""

    def __init__(self, event_bus, parent=None):
        super().__init__(parent)
        self._event_bus = event_bus
        self._mode = "idle"
        self._screen_text = ""
        self._antenna_angle = 0.0
        self._frame = 0
        self._face_state = "normal"  # normal/blink/surprise/love/smirk/dizzy/sleep
        self._drag_pos = None
        self._bounce_y = 0.0

        self._chat_panel = None
        self._news_panel = None
        self._bubble = None  # BubbleToast, set externally
        self._dragged = False  # 区分单击和拖拽
        self._chat_open = False

        self._setup_window()
        self._setup_timers()
        self._connect_events()

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
        self._antenna_angle = 0.0

        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._update_blink)
        self._blink_timer.start(10000)

        self._frame_timer = QTimer(self)
        self._frame_timer.timeout.connect(self._tick)
        self._frame_timer.start(40)

    def _connect_events(self):
        self._event_bus.mode_changed.connect(self.set_mode)
        self._event_bus.water_reminder_triggered.connect(self._on_water_reminder)

    def get_antenna_angle(self):
        return self._antenna_angle

    def set_antenna_angle(self, v):
        self._antenna_angle = v
        self.update()

    antenna_angle = pyqtProperty(float, get_antenna_angle, set_antenna_angle)

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

    def _update_antenna(self):
        self._antenna_angle = 5 * math.sin(self._frame * 0.12)
        self.update()

    def _update_blink(self):
        if self._chat_open:
            return
        self._face_state = random.choice([
            "normal", "normal", "normal", "normal",
            "blink", "surprise", "love", "smirk", "dizzy", "sleep",
        ])
        QTimer.singleShot(3000, self._reset_face)
        self.update()

    def _reset_face(self):
        self._face_state = "normal"
        self.update()

    def _tick(self):
        self._frame += 1
        self._bounce_y = 1.2 * math.sin(self._frame * 0.06)
        self.update()

    def _on_water_reminder(self):
        import random
        from features.water_reminder import WATER_MESSAGES
        msg = random.choice(WATER_MESSAGES)
        self.show_bubble(msg)

    def show_bubble(self, text, duration=5000):
        """在小电视头顶弹出气泡消息。"""
        if self._bubble:
            self._bubble.show_message(text, self, duration)

    # ==================== PAINTING ====================
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.translate(0, self._bounce_y)

        self._draw_body(p)
        self._draw_antennas(p)

        if self._mode == "idle":
            self._draw_face(p)
        else:
            self._draw_text_screen(p)

        self._draw_legs(p)
        p.end()

    # ---------- 天线 ----------
    def _draw_antennas(self, p: QPainter):
        cx = BODY.center().x()
        base_y = BODY.top() - 2  # 起点在机身边框上方，避免重叠阴影
        pen = QPen(BILI, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)

        p.save()
        p.translate(cx - 5, base_y)
        p.rotate(self._antenna_angle)
        p.drawLine(QPointF(0, 0), QPointF(-14, -24))
        p.restore()

        p.save()
        p.translate(cx + 5, base_y)
        p.rotate(-self._antenna_angle)
        p.drawLine(QPointF(0, 0), QPointF(14, -24))
        p.restore()

    # ---------- 机身 ----------
    def _draw_body(self, p: QPainter):
        """白色填充 + 蓝色粗圆角边框。"""
        p.setBrush(WHITE)
        p.setPen(QPen(BILI, 5))
        p.drawRoundedRect(BODY, BODY_R, BODY_R)

    # ---------- 表情（idle 状态） ----------
    def _draw_face(self, p: QPainter):
        cx = BODY.center().x()
        cy = BODY.center().y()
        eye_y = cy - 5
        eye_lx = cx - 14
        eye_rx = cx + 14
        mouth_y = cy + 9
        st = self._face_state
        pen2 = QPen(BILI, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)

        # ===== 眼睛 =====
        if st == "blink":
            # 眯眯眼 —— 两条弧线
            p.setPen(pen2); p.setBrush(Qt.BrushStyle.NoBrush)
            for ex in (eye_lx, eye_rx):
                path = QPainterPath()
                path.moveTo(ex - 5, eye_y - 1)
                path.quadTo(QPointF(ex, eye_y + 4), QPointF(ex + 5, eye_y - 1))
                p.drawPath(path)

        elif st == "surprise":
            # 惊讶 —— 大圆眼 + 高光
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(BILI)
            for ex in (eye_lx, eye_rx):
                p.drawEllipse(QPointF(ex, eye_y), 6, 6)
                p.setBrush(WHITE)
                p.drawEllipse(QPointF(ex + 2, eye_y - 2), 2, 2)
                p.setBrush(BILI)

        elif st == "love":
            # 爱心眼
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(BILI)
            for ex in (eye_lx, eye_rx):
                self._draw_heart(p, ex, eye_y, 11)

        elif st == "smirk":
            # 坏笑 —— 左眼正常，右眼眯起
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(BILI)
            # 左眼：正常横条
            p.save()
            p.translate(eye_lx, eye_y); p.rotate(-8)
            p.drawRoundedRect(QRectF(-6, -2.5, 12, 5), 1.5, 1.5)
            p.restore()
            # 右眼：向上弯的弧线（挑眉）
            p.setPen(pen2); p.setBrush(Qt.BrushStyle.NoBrush)
            path = QPainterPath()
            path.moveTo(eye_rx - 6, eye_y + 1)
            path.quadTo(QPointF(eye_rx, eye_y - 4), QPointF(eye_rx + 6, eye_y + 1))
            p.drawPath(path)

        elif st == "dizzy":
            # 晕 —— 两个螺旋圈
            p.setPen(QPen(BILI, 1.5)); p.setBrush(Qt.BrushStyle.NoBrush)
            for ex in (eye_lx, eye_rx):
                p.drawEllipse(QPointF(ex, eye_y), 5, 5)
                p.drawEllipse(QPointF(ex, eye_y), 2, 2)

        elif st == "sleep":
            # 睡觉 —— 两条平线 + Zzz
            p.setPen(pen2); p.setBrush(Qt.BrushStyle.NoBrush)
            for ex in (eye_lx, eye_rx):
                p.drawLine(QPointF(ex - 5, eye_y), QPointF(ex + 5, eye_y))
            # Zzz
            p.setFont(QFont("Arial", 7, QFont.Weight.Bold))
            p.setPen(BILI)
            zx = eye_rx + 10
            p.drawText(QPointF(zx, eye_y - 6), "z")
            p.drawText(QPointF(zx + 4, eye_y - 12), "Z")

        else:
            # 默认 normal —— 倾斜横条眼 + 瞳孔微移
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(BILI)
            dx = 1.5 * math.sin(self._frame * 0.04)
            p.save()
            p.translate(eye_lx + dx, eye_y); p.rotate(-8)
            p.drawRoundedRect(QRectF(-6, -2.5, 12, 5), 1.5, 1.5)
            p.restore()
            p.save()
            p.translate(eye_rx + dx, eye_y); p.rotate(8)
            p.drawRoundedRect(QRectF(-6, -2.5, 12, 5), 1.5, 1.5)
            p.restore()

        # ===== 嘴巴 =====
        p.setPen(pen2); p.setBrush(Qt.BrushStyle.NoBrush)

        if st == "surprise":
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(BILI)
            p.drawEllipse(QPointF(cx, mouth_y + 1), 3, 3)
        elif st == "love":
            # 开心大笑弧
            path = QPainterPath()
            path.moveTo(cx - 10, mouth_y - 1)
            path.quadTo(QPointF(cx, mouth_y + 8), QPointF(cx + 10, mouth_y - 1))
            p.drawPath(path)
        elif st == "smirk":
            # 歪嘴笑
            path = QPainterPath()
            path.moveTo(cx - 8, mouth_y)
            path.quadTo(QPointF(cx + 2, mouth_y + 6), QPointF(cx + 10, mouth_y - 2))
            p.drawPath(path)
        elif st == "dizzy":
            # 波浪嘴
            path = QPainterPath()
            path.moveTo(cx - 8, mouth_y)
            path.cubicTo(QPointF(cx - 4, mouth_y + 4), QPointF(cx + 4, mouth_y - 4), QPointF(cx + 8, mouth_y))
            p.drawPath(path)
        elif st == "sleep":
            # 微张小嘴
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(BILI)
            p.drawEllipse(QPointF(cx, mouth_y + 1), 3, 2)
        else:
            # 默认 ω 猫嘴
            path = QPainterPath()
            w = 6
            path.moveTo(cx - w * 2, mouth_y)
            path.quadTo(QPointF(cx - w, mouth_y + 6), QPointF(cx, mouth_y))
            path.quadTo(QPointF(cx + w, mouth_y + 6), QPointF(cx + w * 2, mouth_y))
            p.drawPath(path)

    def _draw_heart(self, p: QPainter, cx, cy, size):
        """画一个小爱心。"""
        s = size / 2
        path = QPainterPath()
        path.moveTo(cx, cy + s * 0.5)
        path.cubicTo(QPointF(cx - s, cy - s * 0.3), QPointF(cx - s * 0.5, cy - s), QPointF(cx, cy - s * 0.3))
        path.cubicTo(QPointF(cx + s * 0.5, cy - s), QPointF(cx + s, cy - s * 0.3), QPointF(cx, cy + s * 0.5))
        p.drawPath(path)

    # ---------- 文字屏幕（非 idle 状态） ----------
    def _draw_text_screen(self, p: QPainter):
        inner = BODY.adjusted(6, 6, -6, -6)

        if self._mode == "reminder":
            p.setFont(QFont("PingFang SC", 8, QFont.Weight.Bold))
            p.setPen(BILI)
            p.drawText(inner, Qt.AlignmentFlag.AlignCenter, self._screen_text)
        elif self._mode in ("chat", "news"):
            p.setFont(QFont("PingFang SC", 6))
            p.setPen(BILI_DARK)
            text = self._screen_text or ("聊天中..." if self._mode == "chat" else "新闻...")
            p.drawText(inner, Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, text[:30])

    # ---------- 两只小短腿 ----------
    def _draw_legs(self, p: QPainter):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(BILI)

        foot_w = 14
        foot_h = 8
        foot_r = 4
        bottom = BODY.bottom()

        t = self._frame * 0.1
        off_l = math.sin(t) * 1.2
        off_r = math.sin(t + math.pi) * 1.2

        lx = BODY.left() + 12
        rx = BODY.right() - 12 - foot_w
        p.drawRoundedRect(QRectF(lx, bottom - 1 + off_l, foot_w, foot_h), foot_r, foot_r)
        p.drawRoundedRect(QRectF(rx, bottom - 1 + off_r, foot_w, foot_h), foot_r, foot_r)

    # ==================== MOUSE EVENTS ====================
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
            # 面板和气泡跟随移动
            for panel in (self._chat_panel, self._news_panel, self._bubble):
                if panel and panel.isVisible():
                    panel.move(panel.pos() + delta)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self._dragged:
            self._on_click()
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        self._dragged = True  # 防止双击同时触发单击气泡
        self._toggle_chat()

    def _on_click(self):
        """单击 CLAW，弹出随机互动消息。"""
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
                background: #fff; color: #333; border: 1px solid #e0e0e0;
                border-radius: 8px; padding: 6px;
                font-family: "PingFang SC";
            }
            QMenu::item { padding: 6px 20px; border-radius: 4px; }
            QMenu::item:selected { background: #00A1D6; color: white; }
            QMenu::separator { height: 1px; background: #eee; margin: 4px 8px; }
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
                self._face_state = "normal"
                self.update()
            else:
                self._face_state = "surprise"
                self._chat_open = True
                self.update()
                QTimer.singleShot(800, self._enter_chat_face)
                self._chat_panel.show_near(self)

    def _enter_chat_face(self):
        if self._chat_open:
            self._face_state = "smirk"
            self.update()

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
