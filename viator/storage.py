"""Segnalibri e cronologia, salvati in locale in un database SQLite."""

import sqlite3
import time
from urllib.parse import urlsplit


def site_title(host):
    """Nome breve di un sito: www.wikipedia.org -> Wikipedia."""
    host = (host or "").lower()
    if host.startswith("www."):
        host = host[4:]
    labels = host.split(".")
    name = labels[-2] if len(labels) >= 2 else labels[0]
    return name.capitalize() or host


class Storage:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                created REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                visited REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_history_visited ON history(visited);
            CREATE INDEX IF NOT EXISTS idx_history_url ON history(url);
            CREATE TABLE IF NOT EXISTS pinned (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                position REAL NOT NULL
            );
            """
        )
        self.db.commit()

    # ---------- Segnalibri ----------
    def add_bookmark(self, title, url):
        self.db.execute(
            "INSERT OR REPLACE INTO bookmarks(title, url, created) VALUES (?, ?, ?)",
            (title or url, url, time.time()),
        )
        self.db.commit()

    def remove_bookmark(self, url):
        self.db.execute("DELETE FROM bookmarks WHERE url = ?", (url,))
        self.db.commit()

    def is_bookmarked(self, url):
        return self.db.execute("SELECT 1 FROM bookmarks WHERE url = ?", (url,)).fetchone() is not None

    def bookmarks(self, query=""):
        like = f"%{query}%"
        rows = self.db.execute(
            "SELECT id, title, url, created FROM bookmarks "
            "WHERE title LIKE ? OR url LIKE ? ORDER BY created DESC",
            (like, like),
        )
        return [dict(r) for r in rows]

    # ---------- Siti fissati nella pagina "nuova scheda" ----------
    def pin(self, title, url):
        self.db.execute(
            "INSERT OR IGNORE INTO pinned(title, url, position) VALUES (?, ?, ?)", (title or url, url, time.time())
        )
        self.db.commit()

    def unpin(self, url):
        self.db.execute("DELETE FROM pinned WHERE url = ?", (url,))
        self.db.commit()

    def is_pinned(self, url):
        return self.db.execute("SELECT 1 FROM pinned WHERE url = ?", (url,)).fetchone() is not None

    def pinned(self):
        rows = self.db.execute("SELECT title, url FROM pinned ORDER BY position")
        result = []
        for r in rows:
            host = urlsplit(r["url"]).hostname or ""
            result.append({"title": r["title"], "url": r["url"], "host": host[4:] if host.startswith("www.") else host})
        return result

    # ---------- Cronologia ----------
    def add_history(self, title, url):
        last = self.db.execute("SELECT id, url FROM history ORDER BY id DESC LIMIT 1").fetchone()
        now = time.time()
        if last and last["url"] == url:
            self.db.execute(
                "UPDATE history SET title = ?, visited = ? WHERE id = ?", (title or url, now, last["id"])
            )
        else:
            self.db.execute(
                "INSERT INTO history(title, url, visited) VALUES (?, ?, ?)", (title or url, url, now)
            )
        self.db.commit()

    def update_history_title(self, url, title):
        self.db.execute(
            "UPDATE history SET title = ? WHERE id = (SELECT MAX(id) FROM history WHERE url = ?)",
            (title, url),
        )
        self.db.commit()

    def history(self, query="", limit=1000):
        like = f"%{query}%"
        rows = self.db.execute(
            "SELECT id, title, url, visited FROM history "
            "WHERE title LIKE ? OR url LIKE ? ORDER BY visited DESC LIMIT ?",
            (like, like, limit),
        )
        return [dict(r) for r in rows]

    def delete_history(self, ids):
        self.db.executemany("DELETE FROM history WHERE id = ?", [(i,) for i in ids])
        self.db.commit()

    def clear_history(self):
        self.db.execute("DELETE FROM history")
        self.db.commit()

    def top_sites(self, limit=8):
        """Siti più visitati, raggruppati per dominio."""
        rows = self.db.execute(
            "SELECT url, COUNT(*) AS n FROM history GROUP BY url ORDER BY n DESC LIMIT 300"
        )
        sites = {}
        for r in rows:
            parts = urlsplit(r["url"])
            if parts.scheme not in ("http", "https") or not parts.hostname:
                continue
            host = parts.hostname
            key = host[4:] if host.startswith("www.") else host
            if key in sites:
                sites[key]["n"] += r["n"]
                continue
            sites[key] = {
                "title": site_title(host),
                "url": f"{parts.scheme}://{host}/",
                "host": key,
                "n": r["n"],
            }
        return sorted(sites.values(), key=lambda s: s["n"], reverse=True)[:limit]

    # ---------- Suggerimenti per la barra degli indirizzi ----------
    def suggestions(self, text, limit=10):
        like = f"%{text}%"
        urls = []
        for r in self.db.execute(
            "SELECT url FROM bookmarks WHERE url LIKE ? OR title LIKE ? LIMIT ?", (like, like, limit)
        ):
            urls.append(r["url"])
        for r in self.db.execute(
            "SELECT url, COUNT(*) AS n FROM history WHERE url LIKE ? OR title LIKE ? "
            "GROUP BY url ORDER BY n DESC LIMIT ?",
            (like, like, limit),
        ):
            if r["url"] not in urls:
                urls.append(r["url"])
        return urls[:limit]
