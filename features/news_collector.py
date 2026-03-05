import asyncio
import aiohttp
import feedparser
from datetime import datetime, time as dtime
from PyQt6.QtCore import QThread, QTimer, QTime, pyqtSignal, QObject

from features.ai_chat import create_provider


class NewsWorker(QThread):
    """Fetch news from RSS feeds and NewsAPI in background."""
    finished = pyqtSignal(list)
    summary_ready = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, config):
        super().__init__()
        self._config = config

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            articles = loop.run_until_complete(self._fetch_all())
            loop.close()
            self.finished.emit(articles)

            # Generate AI summary
            if articles:
                self._generate_summary(articles)
        except Exception as e:
            self.error.emit(str(e))

    async def _fetch_all(self):
        articles = []
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            # RSS feeds
            feeds = self._config.get("news", "rss_feeds") or []
            for url in feeds:
                try:
                    items = await self._fetch_rss(session, url)
                    articles.extend(items)
                except Exception:
                    pass

            # NewsAPI
            newsapi_key = self._config.get("news", "newsapi_key")
            if newsapi_key:
                try:
                    items = await self._fetch_newsapi(session, newsapi_key)
                    articles.extend(items)
                except Exception:
                    pass

        # Deduplicate by title and sort by date
        seen = set()
        unique = []
        for a in articles:
            if a["title"] not in seen:
                seen.add(a["title"])
                unique.append(a)
        unique.sort(key=lambda x: x.get("date", ""), reverse=True)
        return unique[:20]

    async def _fetch_rss(self, session, url):
        async with session.get(url) as resp:
            text = await resp.text()
        feed = feedparser.parse(text)
        articles = []
        for entry in feed.entries[:10]:
            articles.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "summary": entry.get("summary", "")[:200],
                "date": entry.get("published", ""),
                "source": "RSS",
            })
        return articles

    async def _fetch_newsapi(self, session, api_key):
        keywords = self._config.get("news", "keywords") or ["AI"]
        q = " OR ".join(keywords)
        url = f"https://newsapi.org/v2/everything?q={q}&sortBy=publishedAt&pageSize=10&apiKey={api_key}"
        async with session.get(url) as resp:
            data = await resp.json()
        articles = []
        for a in data.get("articles", []):
            articles.append({
                "title": a.get("title", ""),
                "link": a.get("url", ""),
                "summary": (a.get("description") or "")[:200],
                "date": a.get("publishedAt", ""),
                "source": "NewsAPI",
            })
        return articles

    def _generate_summary(self, articles):
        provider = create_provider(self._config)
        if not provider:
            return
        text = "\n".join(f"- {a['title']}: {a['summary']}" for a in articles[:10])
        prompt = f"请用中文简要总结以下AI相关新闻，提取最重要的3-5条，每条一句话：\n\n{text}"
        try:
            result = provider.chat([
                {"role": "system", "content": "你是一个AI新闻编辑，擅长用简洁的中文总结新闻。"},
                {"role": "user", "content": prompt},
            ])
            self.summary_ready.emit(result)
        except Exception:
            pass


class NewsCollector(QObject):
    def __init__(self, event_bus, config, parent=None):
        super().__init__(parent)
        self._event_bus = event_bus
        self._config = config
        self._articles = []
        self._worker = None

        # Check every 10 minutes if it's time to fetch
        self._schedule_timer = QTimer(self)
        self._schedule_timer.timeout.connect(self._check_schedule)
        self._schedule_timer.start(10 * 60 * 1000)

    def fetch_now(self):
        if self._worker and self._worker.isRunning():
            return
        self._worker = NewsWorker(self._config)
        self._worker.finished.connect(self._on_fetched)
        self._worker.summary_ready.connect(self._on_summary)
        self._worker.error.connect(lambda e: None)
        self._worker.start()

    def _check_schedule(self):
        if not self._config.get("news", "enabled"):
            return
        hour = self._config.get("news", "schedule_hour") or 9
        now = QTime.currentTime()
        if now.hour() == hour and now.minute() < 10:
            self.fetch_now()

    def _on_fetched(self, articles):
        self._articles = articles
        self._event_bus.news_updated.emit(articles)

    def _on_summary(self, summary):
        self._event_bus.news_summary_ready.emit(summary)
