import json
import os
from datetime import date, datetime

from PyQt6.QtCore import QTimer, QObject, QTime

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "water_log.json")

WATER_MESSAGES = [
    "该喝水啦～",
    "喝口水休息一下吧！",
    "补充水分时间到！",
    "来杯水吧～保持元气满满！",
    "叮～喝水提醒！",
]


class WaterReminder(QObject):
    def __init__(self, event_bus, config, parent=None):
        super().__init__(parent)
        self._event_bus = event_bus
        self._config = config
        self._today_count = 0
        self._last_triggered_hour = -1

        self._load_log()

        # 每 20 秒检查一次是否到整点
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check_hourly)
        self._timer.start(20 * 1000)

        self._event_bus.water_drunk.connect(self._on_drunk)

    def trigger_now(self):
        """手动触发喝水提醒（聊天消息调用）。"""
        self._event_bus.water_reminder_triggered.emit()

    def _check_hourly(self):
        if not self._config.get("water_reminder", "enabled"):
            return
        now = QTime.currentTime()
        hour = now.hour()
        # 整点前后 1 分钟内触发，且每小时只触发一次
        if now.minute() == 0 and hour != self._last_triggered_hour:
            self._last_triggered_hour = hour
            self._event_bus.water_reminder_triggered.emit()

    def _on_drunk(self, _=0):
        self._today_count += 1
        self._save_log()

    def _load_log(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
            self._today_count = data.get(str(date.today()), 0)
        else:
            self._today_count = 0

    def _save_log(self):
        data = {}
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
        data[str(date.today())] = self._today_count
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
