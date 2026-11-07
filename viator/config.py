"""Impostazioni dell'utente e percorsi dei dati."""

import os

from PySide6.QtCore import QSettings, QStandardPaths

SEARCH_ENGINES = {
    "DuckDuckGo": "https://duckduckgo.com/?q={}",
    "Startpage": "https://www.startpage.com/do/search?q={}",
    "Ecosia": "https://www.ecosia.org/search?q={}",
    "Qwant": "https://www.qwant.com/?q={}",
    "Google": "https://www.google.com/search?q={}",
    "Bing": "https://www.bing.com/search?q={}",
}


def _default_download_dir():
    path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
    return path or os.path.expanduser("~")


HOME_URL = "viator://home"  # pagina "nuova scheda" integrata

DEFAULTS = {
    "search_engine": "DuckDuckGo",
    "start_url": HOME_URL,
    "theme": "auto",  # auto | light | dark
    "restore_session": True,
    "adblock": True,
    "download_dir": None,  # calcolato all'avvio
}

THEMES = {"auto": "Come il sistema", "light": "Chiaro", "dark": "Scuro"}


def data_dir():
    """Cartella dove Viator salva database, profilo e liste di blocco."""
    path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    if not path:
        path = os.path.join(os.path.expanduser("~"), ".viator")
    os.makedirs(path, exist_ok=True)
    return path


class Settings:
    def __init__(self):
        self._s = QSettings("Viator", "Viator")

    def get(self, key):
        default = DEFAULTS[key]
        if key == "download_dir" and default is None:
            default = _default_download_dir()
        value = self._s.value(key, default)
        if isinstance(DEFAULTS[key], bool):
            return value in (True, "true", "True", "1", 1)
        return value

    def set(self, key, value):
        self._s.setValue(key, value)

    def search_template(self):
        return SEARCH_ENGINES.get(self.get("search_engine"), SEARCH_ENGINES["DuckDuckGo"])
