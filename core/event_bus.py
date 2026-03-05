from PyQt6.QtCore import QObject, pyqtSignal


class EventBus(QObject):
    """Simple event bus for inter-module communication."""

    # TV display mode changes
    mode_changed = pyqtSignal(str)  # "idle", "chat", "news", "reminder"

    # Water reminder events
    water_reminder_triggered = pyqtSignal()
    water_drunk = pyqtSignal(int)  # daily count

    # Chat events
    chat_message_received = pyqtSignal(str)  # AI response text
    chat_request_sent = pyqtSignal(str)  # user message

    # News events
    news_updated = pyqtSignal(list)  # list of news dicts
    news_summary_ready = pyqtSignal(str)

    # Settings changed
    settings_changed = pyqtSignal()


# Global singleton
event_bus = EventBus()
