"""Descarga noticias y menciones de ciberseguridad de varias fuentes gratuitas
(feeds RSS, Hacker News y Reddit) y filtra las de los últimos N días.

Ninguna fuente requiere clave de API ni login:
- RSS: feeds públicos de medios especializados.
- Hacker News: API pública de Algolia (hn.algolia.com).
- Reddit: endpoints JSON públicos de subreddits (sin autenticación).
"""
import re
from datetime import datetime, timedelta, timezone
from time import mktime

import feedparser
import requests


FEEDS = [
    {"name": "The Hacker News", "url": "https://feeds.feedburner.com/TheHackersNews"},
    {"name": "BleepingComputer", "url": "https://www.bleepingcomputer.com/feed/"},
    {"name": "Krebs on Security", "url": "https://krebsonsecurity.com/feed/"},
    {"name": "Dark Reading", "url": "https://www.darkreading.com/rss.xml"},
    {"name": "We Live Security (ESET)", "url": "https://www.welivesecurity.com/en/rss/feed/"},
    {
        "name": "INCIBE-CERT Avisos",
        "url": "https://www.incibe.es/index.php/incibe-cert/alerta-temprana/avisos/feed",
    },
]


HN_ALGOLIA_URL = "https://hn.algolia.com/api/v1/search_by_date"
HN_QUERIES = ["ransomware", "phishing", "data breach", "vulnerability", "malware", "ciberseguridad"]


REDDIT_SUBREDDITS = ["cybersecurity", "netsec", "InfoSecNews"]
REDDIT_HEADERS = {
    "User-Agent": "quantumsec-content-bot/1.0 (investigacion semanal de contenido)"
}


def fetch_recent_articles(
    days: int = 30,
    feeds=None,
    include_hn: bool = True,
    include_reddit: bool = True,
):
    """Devuelve una lista de artículos/publicaciones (dict) de los últimos
    `days` días, combinando RSS + Hacker News + Reddit, sin duplicados y
    ordenados del más reciente al más antiguo.
    """
    articles = list(fetch_rss_articles(days=days, feeds=feeds))

    if include_hn:
        articles.extend(fetch_hn_articles(days=days))

    if include_reddit:
        articles.extend(fetch_reddit_articles(days=days))

    seen_links = set()
    deduped = []
    for article in articles:
        link = article.get("link")
        if link and link in seen_links:
            continue
        if link:
            seen_links.add(link)
        deduped.append(article)

    deduped.sort(key=lambda a: a["published"] or "", reverse=True)
    return deduped


def fetch_rss_articles(days: int = 30, feeds=None):
    feeds = feeds or FEEDS
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    articles = []

    for feed in feeds:
        try:
            parsed = feedparser.parse(feed["url"])
        except Exception as exc:  
            print(f"[warn] no se pudo descargar el feed de {feed['name']}: {exc}")
            continue

        if not parsed.entries:
            print(f"[warn] el feed de {feed['name']} no devolvió artículos (¿URL caducada?)")
            continue

        for entry in parsed.entries:
            published = _entry_datetime(entry)
            
            if published and published < cutoff:
                continue
            articles.append(
                {
                    "source": feed["name"],
                    "title": entry.get("title", "").strip(),
                    "link": entry.get("link", ""),
                    "summary": _clean_summary(entry.get("summary", "")),
                    "published": published.isoformat() if published else None,
                }
            )

    return articles


def fetch_hn_articles(days: int = 30, queries=None):
    """Busca en Hacker News (vía la API pública de Algolia) historias sobre
    los términos de `queries`, publicadas en los últimos `days` días.
    """
    queries = queries or HN_QUERIES
    cutoff_ts = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
    seen_ids = set()
    articles = []

    for query in queries:
        try:
            resp = requests.get(
                HN_ALGOLIA_URL,
                params={
                    "query": query,
                    "tags": "story",
                    "numericFilters": f"created_at_i>{cutoff_ts}",
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            print(f"[warn] error al consultar Hacker News para '{query}': {exc}")
            continue

        for hit in data.get("hits", []):
            object_id = hit.get("objectID")
            if not object_id or object_id in seen_ids:
                continue
            seen_ids.add(object_id)

            url = hit.get("url") or f"https://news.ycombinator.com/item?id={object_id}"
            points = hit.get("points", 0) or 0
            comments = hit.get("num_comments", 0) or 0
            created_at_i = hit.get("created_at_i")

            articles.append(
                {
                    "source": f"Hacker News ({points} puntos, {comments} comentarios)",
                    "title": (hit.get("title") or "").strip(),
                    "link": url,
                    "summary": "",
                    "published": _timestamp_to_iso(created_at_i),
                }
            )

    return articles


def fetch_reddit_articles(days: int = 30, subreddits=None, limit: int = 25):
    """Lee las publicaciones más nuevas de varios subreddits de ciberseguridad
    vía el endpoint JSON público de Reddit (sin autenticación).
    """
    subreddits = subreddits or REDDIT_SUBREDDITS
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    articles = []

    for subreddit in subreddits:
        url = f"https://www.reddit.com/r/{subreddit}/new.json"
        try:
            resp = requests.get(url, headers=REDDIT_HEADERS, params={"limit": limit}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            print(f"[warn] error al consultar r/{subreddit} en Reddit: {exc}")
            continue

        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            created_utc = post.get("created_utc")
            published_dt = (
                datetime.fromtimestamp(created_utc, tz=timezone.utc) if created_utc else None
            )
            if published_dt and published_dt < cutoff:
                continue

            score = post.get("score", 0) or 0
            num_comments = post.get("num_comments", 0) or 0
            permalink = post.get("permalink", "")
            link = f"https://www.reddit.com{permalink}" if permalink else post.get("url", "")

            articles.append(
                {
                    "source": f"Reddit r/{subreddit} ({score} upvotes, {num_comments} comentarios)",
                    "title": (post.get("title") or "").strip(),
                    "link": link,
                    "summary": _clean_summary(post.get("selftext", "")),
                    "published": published_dt.isoformat() if published_dt else None,
                }
            )

    return articles


def _entry_datetime(entry):
    for field in ("published_parsed", "updated_parsed"):
        value = entry.get(field)
        if value:
            return datetime.fromtimestamp(mktime(value), tz=timezone.utc)
    return None


def _timestamp_to_iso(unix_ts):
    if not unix_ts:
        return None
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc).isoformat()


def _clean_summary(html_summary: str, max_len: int = 280) -> str:
    text = re.sub("<[^<]+?>", "", html_summary or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text[:max_len]


if __name__ == "__main__":
    found = fetch_recent_articles()
    print(f"{len(found)} resultados encontrados en los últimos 30 días:\n")
    for article in found:
        print(f"- [{article['source']}] {article['title']} ({article['link']})")
