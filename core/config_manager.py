import os
import yaml

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")

DEFAULT_CONFIG = {
    "server": {
        "url": "http://localhost:8000",
        "token": "claw-dev-token-2026",
    },
    "general": {
        "language": "zh",
        "start_minimized": False,
    },
    "ai": {
        "provider": "openai",  # "openai" or "claude"
        "openai_api_key": "",
        "openai_model": "gpt-4o-mini",
        "openai_base_url": "",
        "claude_api_key": "",
        "claude_model": "claude-sonnet-4-20250514",
    },
    "water_reminder": {
        "enabled": True,
        "interval_minutes": 45,
    },
    "news": {
        "enabled": True,
        "schedule_hour": 9,
        "rss_feeds": [
            "https://rsshub.app/telegram/channel/AINewsDaily",
            "https://feeds.feedburner.com/theaibeat",
        ],
        "newsapi_key": "",
        "keywords": ["AI", "人工智能", "LLM", "GPT"],
    },
}


class ConfigManager:
    def __init__(self):
        self._config = {}
        self.load()

    def load(self):
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
        self._config = self._merge_defaults(DEFAULT_CONFIG, self._config)

    def save(self):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(self._config, f, allow_unicode=True, default_flow_style=False)

    def _merge_defaults(self, defaults, current):
        result = {}
        for key, default_val in defaults.items():
            if key in current:
                if isinstance(default_val, dict) and isinstance(current[key], dict):
                    result[key] = self._merge_defaults(default_val, current[key])
                else:
                    result[key] = current[key]
            else:
                result[key] = default_val
        return result

    def get(self, *keys):
        val = self._config
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return None
        return val

    def set(self, *args):
        """set("ai", "provider", "claude") - last arg is value."""
        keys, value = args[:-1], args[-1]
        d = self._config
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value
        self.save()


config = ConfigManager()
