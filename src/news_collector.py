import urllib.request
import xml.etree.ElementTree as ET
import json
from dataclasses import dataclass, field


@dataclass
class NewsItem:
    title: str
    source: str
    sentiment: str = "不明"
    url: str = ""


_SENTIMENT_MAP = {
    "Bullish": "強気",
    "Bearish": "弱気",
    "Neutral": "中立",
    "Somewhat-Bullish": "やや強気",
    "Somewhat-Bearish": "やや弱気",
}

_RSS_FEEDS = [
    ("Reuters", "https://feeds.reuters.com/reuters/businessNews"),
    ("CNBC", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
    ("NHK経済", "https://www.nhk.or.jp/rss/news/cat5.xml"),
    ("Reddit/investing", "https://www.reddit.com/r/investing/.rss"),
    ("SeekingAlpha", "https://seekingalpha.com/market_currents.xml"),
]

_SOURCE_CATEGORIES = {
    "NHK経済": "日本",
    "Reuters": "国際",
    "CNBC": "アメリカ",
    "AlphaVantage": "アメリカ",
    "Reddit/investing": "SNS/分析",
    "SeekingAlpha": "SNS/分析",
}


def _fetch_alpha_vantage(api_key: str) -> list[NewsItem]:
    url = (
        f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT"
        f"&topics=economy_macro,financial_markets,earnings"
        f"&sort=LATEST&limit=10&apikey={api_key}"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        items = []
        for article in data.get("feed", []):
            sentiment = _SENTIMENT_MAP.get(article.get("overall_sentiment_label", ""), "不明")
            items.append(NewsItem(
                title=article.get("title", ""),
                source="AlphaVantage",
                sentiment=sentiment,
                url=article.get("url", ""),
            ))
        return items
    except Exception:
        return []


def _fetch_rss(source_name: str, feed_url: str) -> list[NewsItem]:
    try:
        req = urllib.request.Request(feed_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = resp.read()
        root = ET.fromstring(raw)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items = []
        for item in root.findall(".//item"):
            title_el = item.find("title")
            link_el = item.find("link")
            title = title_el.text.strip() if title_el is not None and title_el.text else ""
            url = link_el.text.strip() if link_el is not None and link_el.text else ""
            if title:
                items.append(NewsItem(title=title, source=source_name, url=url))
        if not items:
            for entry in root.findall(".//atom:entry", ns):
                title_el = entry.find("atom:title", ns)
                link_el = entry.find("atom:link", ns)
                title = title_el.text.strip() if title_el is not None and title_el.text else ""
                url = link_el.get("href", "") if link_el is not None else ""
                if title:
                    items.append(NewsItem(title=title, source=source_name, url=url))
        return items
    except Exception:
        return []


def _is_japanese(text: str) -> bool:
    japanese_chars = sum(1 for c in text if '　' <= c <= '鿿' or '＀' <= c <= '￯')
    return japanese_chars > len(text) * 0.1


def translate_titles(news_items: list[NewsItem]) -> list[NewsItem]:
    import config
    from openai import OpenAI

    targets = [i for i, item in enumerate(news_items) if not _is_japanese(item.title)]
    if not targets or not config.OPENAI_API_KEY:
        return news_items

    titles = "\n".join(f"{i+1}. {news_items[idx].title}" for i, idx in enumerate(targets))
    try:
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"以下のニュースタイトルを自然な日本語に翻訳・要約してください。番号付きで同じ順番で返してください。\n\n{titles}"
            }],
            temperature=0.1,
        )
        translated_lines = response.choices[0].message.content.strip().split("\n")
        translated_lines = [l.strip() for l in translated_lines if l.strip()]
        for i, idx in enumerate(targets):
            if i < len(translated_lines):
                line = translated_lines[i]
                if ". " in line:
                    line = line.split(". ", 1)[1]
                news_items[idx].title = line
    except Exception:
        pass
    return news_items


def fetch_news() -> list[NewsItem]:
    import config
    results: list[NewsItem] = []

    if config.ALPHA_VANTAGE_API_KEY:
        results.extend(_fetch_alpha_vantage(config.ALPHA_VANTAGE_API_KEY))

    for source_name, feed_url in _RSS_FEEDS:
        results.extend(_fetch_rss(source_name, feed_url))

    return results[:20]


def format_news_for_ai(news_items: list[NewsItem]) -> str:
    if not news_items:
        return "ニュースなし"

    categories = {"日本": [], "アメリカ": [], "国際": [], "SNS/分析": []}
    for item in news_items:
        cat = _SOURCE_CATEGORIES.get(item.source, "国際")
        categories[cat].append(item)

    lines = []
    counter = 1
    for cat_name, items in categories.items():
        if not items:
            continue
        lines.append(f"【{cat_name}】")
        for item in items:
            sentiment_tag = f"[{item.sentiment}] " if item.sentiment != "不明" else ""
            lines.append(f"{counter}. {sentiment_tag}{item.source}: {item.title}")
            counter += 1
    return "\n".join(lines)
