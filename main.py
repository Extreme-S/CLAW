import sys
from PyQt6.QtWidgets import QApplication

from core.config_manager import config
from core.event_bus import event_bus
from ui.tv_widget import TVWidget
from ui.tray_icon import TrayIcon
from ui.chat_panel import ChatPanel
from ui.news_panel import NewsPanel
from ui.bubble_toast import BubbleToast
from features.water_reminder import WaterReminder
from features.news_collector import NewsCollector


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("CLAW")

    tv = TVWidget(event_bus)

    # Bubble toast
    bubble = BubbleToast()
    tv._bubble = bubble

    # Chat panel
    chat_panel = ChatPanel(event_bus)
    tv._chat_panel = chat_panel

    # News
    news_collector = NewsCollector(event_bus, config)
    news_panel = NewsPanel(event_bus, news_collector)
    tv._news_panel = news_panel

    # System tray
    tray = TrayIcon(tv, event_bus)
    tray.show()

    # Water reminder
    water = WaterReminder(event_bus, config)

    # Update TV screen text on chat messages
    event_bus.chat_message_received.connect(lambda t: tv.set_screen_text(t[:60]))
    event_bus.news_summary_ready.connect(lambda t: tv.set_screen_text(t[:60]))

    tv.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
