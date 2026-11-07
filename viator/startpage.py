"""Pagina "nuova scheda" di Viator, servita dall'indirizzo interno viator://home."""

import html
import json
from urllib.parse import quote

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QUrl, QUrlQuery
from PySide6.QtWebEngineCore import QWebEngineUrlRequestJob, QWebEngineUrlScheme, QWebEngineUrlSchemeHandler

from .config import HOME_URL
from .storage import site_title
from .theme import logo_svg

MAX_TILES = 8

SCHEME = b"viator"
SCHEME_NAME = "viator"

DEFAULT_SITES = [
    {"title": "Wikipedia", "url": "https://it.wikipedia.org/", "host": "wikipedia.org"},
    {"title": "OpenStreetMap", "url": "https://www.openstreetmap.org/", "host": "openstreetmap.org"},
    {"title": "YouTube", "url": "https://www.youtube.com/", "host": "youtube.com"},
    {"title": "GitHub", "url": "https://github.com/", "host": "github.com"},
]


def register_scheme():
    """Va chiamata prima di creare la QApplication."""
    scheme = QWebEngineUrlScheme(SCHEME)
    scheme.setSyntax(QWebEngineUrlScheme.Syntax.Host)
    scheme.setFlags(QWebEngineUrlScheme.Flag.SecureScheme | QWebEngineUrlScheme.Flag.LocalScheme)
    QWebEngineUrlScheme.registerScheme(scheme)


TILE_COLORS = ["#0B7A75", "#2F6FDE", "#C2571A", "#7A4CC2", "#B8336A", "#3E8E41", "#B08A12", "#4A5A6A"]


def _tile_color(text):
    return TILE_COLORS[sum(ord(c) for c in text) % len(TILE_COLORS)]


def _action_url(action, url, title=""):
    return f"viator://action/{action}?url={quote(url, safe='')}&title={quote(title, safe='')}"


def _tile(site, pinned):
    e = lambda v: html.escape(v, quote=True)
    letter = html.escape((site["title"] or site["host"] or "?")[0].upper())
    if pinned:
        action = (f'<a class="act" href="{e(_action_url("unpin", site["url"]))}" '
                  f'title="Togli dalla pagina iniziale">&times;</a>')
    else:
        action = (f'<a class="act" href="{e(_action_url("pin", site["url"], site["title"]))}" '
                  f'title="Fissa nella pagina iniziale">{PIN_SVG}</a>')
    dot = '<span class="dot" title="Sito fissato"></span>' if pinned else ""
    return (
        f'<div class="tile{" pinned" if pinned else ""}">'
        f'<a class="link" href="{e(site["url"])}" title="{e(site["url"])}">'
        f'<span class="badge" style="background:{_tile_color(site["host"])}">{letter}{dot}</span>'
        f'<span class="name">{html.escape(site["title"])}</span></a>{action}</div>'
    )


PIN_SVG = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
           'stroke-linecap="round" stroke-linejoin="round"><path d="M9 3.5h6M10 3.5v6l-3 4h10l-3-4v-6M12 13.5v7"/></svg>')


def build_html(ctx):
    t = ctx.theme.t
    pinned = ctx.storage.pinned()
    pinned_urls = {p["url"] for p in pinned}
    pinned_hosts = {p["host"] for p in pinned}
    others = [s for s in (ctx.storage.top_sites(MAX_TILES * 2) or DEFAULT_SITES)
              if s["url"] not in pinned_urls and s["host"] not in pinned_hosts]
    tiles = [_tile(p, True) for p in pinned]
    tiles += [_tile(s, False) for s in others[: max(0, MAX_TILES - len(pinned))]]
    tiles.append(
        '<div class="tile add"><a class="link" href="#" id="add" title="Fissa un sito">'
        '<span class="badge plus">+</span><span class="name">Aggiungi</span></a></div>'
    )
    blocked = ctx.blocker.total_blocked
    footer = (
        f"Viator ha bloccato {blocked} tracker da quando l'hai aperto."
        if ctx.blocker.enabled and blocked
        else "Navighi con il blocco dei tracker attivo." if ctx.blocker.enabled
        else "Il blocco dei tracker è disattivato."
    )
    engine = html.escape(ctx.settings.get("search_engine"))
    return f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8"><title>Nuova scheda</title>
<style>
  :root {{ color-scheme: {"dark" if ctx.theme.dark else "light"}; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; min-height: 100vh; background: {t["page"]}; color: {t["text"]};
    font-family: system-ui, -apple-system, "Segoe UI", Ubuntu, Cantarell, sans-serif;
    display: flex; flex-direction: column; align-items: center;
  }}
  main {{ width: min(720px, 100% - 48px); margin-top: 15vh; display: flex; flex-direction: column; align-items: center; }}
  .brand {{ display: flex; align-items: center; gap: 14px; margin-bottom: 30px; }}
  .brand svg {{ width: 54px; height: 54px; }}
  .brand h1 {{ font-size: 38px; font-weight: 650; letter-spacing: -0.5px; margin: 0; }}
  form {{ width: 100%; position: relative; }}
  form svg {{ position: absolute; left: 18px; top: 50%; transform: translateY(-50%); width: 20px; height: 20px; }}
  input {{
    width: 100%; height: 54px; padding: 0 20px 0 50px; font-size: 16px;
    color: {t["text"]}; background: {t["surface"]}; border: 1px solid {t["border"]};
    border-radius: 16px; outline: none;
    box-shadow: 0 1px 2px rgba(0,0,0,.06), 0 6px 20px rgba(0,0,0,{".25" if ctx.theme.dark else ".06"});
  }}
  input:focus {{ border: 2px solid {t["accent"]}; padding-left: 49px; }}
  input::placeholder {{ color: {t["muted"]}; }}
  .tiles {{ width: 100%; margin-top: 44px; display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; }}
  .tile {{ position: relative; width: 120px; border-radius: 14px; transition: background .15s; }}
  .tile:hover {{ background: {t["hover"]}; }}
  .tile .link {{
    display: flex; flex-direction: column; align-items: center; gap: 10px;
    padding: 18px 8px 14px; text-decoration: none; color: {t["text"]};
  }}
  .badge {{
    position: relative; width: 52px; height: 52px; border-radius: 14px; display: grid; place-items: center;
    color: #fff; font-size: 22px; font-weight: 650;
  }}
  .badge.plus {{ background: transparent; border: 2px dashed {t["border"]}; color: {t["muted"]}; font-weight: 400; font-size: 26px; }}
  .dot {{
    position: absolute; right: -4px; top: -4px; width: 12px; height: 12px; border-radius: 50%;
    background: {t["accent"]}; border: 2px solid {t["page"]};
  }}
  .act {{
    position: absolute; top: 6px; right: 6px; width: 24px; height: 24px; border-radius: 7px;
    display: grid; place-items: center; text-decoration: none; font-size: 18px; line-height: 1;
    color: {t["muted"]}; background: {t["surface"]}; border: 1px solid {t["border"]};
    opacity: 0; transition: opacity .15s;
  }}
  .act svg {{ width: 14px; height: 14px; }}
  .tile:hover .act {{ opacity: 1; }}
  .act:hover {{ color: {t["accent"]}; border-color: {t["accent"]}; }}
  .name {{ font-size: 13px; color: {t["muted"]}; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  footer {{ margin: auto 0 26px; padding-top: 40px; font-size: 13px; color: {t["muted"]}; display: flex; align-items: center; gap: 8px; }}
  footer svg {{ width: 16px; height: 16px; }}
</style></head>
<body>
<main>
  <div class="brand">{logo_svg(t["accent"], t["surface"] if ctx.theme.dark else "#FFFFFF")}<h1>Viator</h1></div>
  <form id="f">
    <svg viewBox="0 0 24 24" fill="none" stroke="{t["muted"]}" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="6"/><path d="M20 20l-4.5-4.5"/></svg>
    <input id="q" type="search" autocomplete="off" placeholder="Cerca con {engine} o scrivi un indirizzo">
  </form>
  <nav class="tiles">{"".join(tiles)}</nav>
</main>
<footer>
  <svg viewBox="0 0 24 24" fill="none" stroke="{t["accent"]}" stroke-width="2" stroke-linejoin="round"><path d="M12 3.5l7 2.8v5.4c0 4.3-2.9 7.3-7 8.8-4.1-1.5-7-4.5-7-8.8V6.3z"/></svg>
  {html.escape(footer)}
</footer>
<script>
  const template = {json.dumps(ctx.settings.search_template())};
  document.getElementById("add").addEventListener("click", (e) => {{
    e.preventDefault();
    const site = (prompt("Indirizzo del sito da fissare (es. wikipedia.org):") || "").trim();
    if (!site) return;
    const url = /^[a-z]+:\\/\\//i.test(site) ? site : "https://" + site;
    location.href = "viator://action/pin?url=" + encodeURIComponent(url) + "&title=";
  }});
  document.getElementById("f").addEventListener("submit", (e) => {{
    e.preventDefault();
    const q = document.getElementById("q").value.trim();
    if (!q) return;
    const isAddress = !q.includes(" ") && (q.includes(".") || q.startsWith("localhost"));
    if (isAddress) location.href = /^[a-z]+:\\/\\//i.test(q) ? q : "https://" + q;
    else location.href = template.replace("{{}}", encodeURIComponent(q));
  }});
</script>
</body></html>"""


class StartPageHandler(QWebEngineUrlSchemeHandler):
    """Serve viator://home e gestisce le azioni della pagina (fissa / togli)."""

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx

    def requestStarted(self, job):
        url = job.requestUrl()
        if url.host() == "home":
            data = build_html(self.ctx).encode("utf-8")
            buffer = QBuffer(job)
            buffer.setData(QByteArray(data))
            buffer.open(QIODevice.OpenModeFlag.ReadOnly)
            job.reply(b"text/html", buffer)
        elif url.host() == "action" and job.initiator().scheme() == SCHEME_NAME:
            # solo la pagina "nuova scheda" stessa può chiedere queste azioni
            self._do_action(url)
            job.redirect(QUrl(HOME_URL))
        else:
            job.fail(QWebEngineUrlRequestJob.Error.UrlNotFound)

    def _do_action(self, url):
        query = QUrlQuery(url)
        target = QUrl(query.queryItemValue("url", QUrl.ComponentFormattingOption.FullyDecoded))
        if target.scheme() not in ("http", "https") or not target.host():
            return
        storage = self.ctx.storage
        if url.path() == "/pin":
            title = query.queryItemValue("title", QUrl.ComponentFormattingOption.FullyDecoded)
            storage.pin(title or site_title(target.host()), target.toString())
        elif url.path() == "/unpin":
            storage.unpin(target.toString())
