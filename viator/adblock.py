"""Blocco di tracker e pubblicità a livello di dominio.

Oltre alla piccola lista integrata, Viator legge un file opzionale
`blocklist.txt` nella cartella dei dati: può contenere un dominio per riga
oppure righe in formato hosts ("0.0.0.0 dominio.com"), quindi si possono
usare liste pubbliche già pronte.
"""

import os

from PySide6.QtWebEngineCore import QWebEngineUrlRequestInfo, QWebEngineUrlRequestInterceptor

BUILTIN_DOMAINS = {
    "doubleclick.net",
    "googlesyndication.com",
    "googleadservices.com",
    "google-analytics.com",
    "googletagmanager.com",
    "googletagservices.com",
    "adservice.google.com",
    "scorecardresearch.com",
    "quantserve.com",
    "adnxs.com",
    "criteo.com",
    "criteo.net",
    "taboola.com",
    "outbrain.com",
    "hotjar.com",
    "mixpanel.com",
    "amazon-adsystem.com",
    "pubmatic.com",
    "rubiconproject.com",
    "openx.net",
    "moatads.com",
    "adsrvr.org",
    "bat.bing.com",
    "ads.yahoo.com",
}


class Blocker(QWebEngineUrlRequestInterceptor):
    def __init__(self, enabled=True, blocklist_path=None, parent=None):
        super().__init__(parent)
        self.enabled = enabled
        self.blocklist_path = blocklist_path
        self.domains = set(BUILTIN_DOMAINS)
        self.total_blocked = 0
        self.page_counts = {}  # dominio della pagina -> tracker bloccati
        if blocklist_path and os.path.exists(blocklist_path):
            self.domains |= self._load_file(blocklist_path)

    @staticmethod
    def _load_file(path):
        domains = set()
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.split("#", 1)[0].strip()
                if not line:
                    continue
                parts = line.split()
                domain = parts[-1].lower()
                if domain not in ("localhost", "0.0.0.0", "127.0.0.1") and "." in domain:
                    domains.add(domain)
        return domains

    def is_blocked(self, host):
        parts = host.lower().split(".")
        # controlla il dominio e tutti i domini "genitori" (es. a.b.ads.com -> ads.com)
        for i in range(len(parts) - 1):
            if ".".join(parts[i:]) in self.domains:
                return True
        return False

    def blocked_for(self, page_host):
        return self.page_counts.get(page_host, 0)

    def interceptRequest(self, info):
        if not self.enabled:
            return
        # non blocchiamo mai la pagina principale aperta dall'utente
        if info.resourceType() == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeMainFrame:
            self.page_counts[info.requestUrl().host()] = 0
            return
        host = info.requestUrl().host()
        if host and self.is_blocked(host):
            info.block(True)
            self.total_blocked += 1
            page = info.firstPartyUrl().host()
            self.page_counts[page] = self.page_counts.get(page, 0) + 1
