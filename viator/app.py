"""Avvio dell'applicazione e stato condiviso tra le finestre."""

import json
import os
import sys

from PySide6.QtCore import QByteArray, QCoreApplication, QTimer
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from . import APP_NAME, APP_VERSION
from .adblock import Blocker
from .config import HOME_URL, Settings, data_dir
from .downloads import DownloadManager
from .startpage import SCHEME, StartPageHandler, register_scheme
from .storage import Storage
from .theme import Theme, system_is_dark
from .window import BrowserWindow

Attr = QWebEngineSettings.WebAttribute


class AppContext:
    """Oggetti condivisi da tutte le finestre: profilo, dati, tema, download, sessione."""

    def __init__(self, qapp):
        self.qapp = qapp
        self.settings = Settings()
        self.folder = data_dir()
        self.windows = []
        self.theme = None
        self.downloads = None
        self.quitting = False
        self.session_path = os.path.join(self.folder, "session.json")

        self.storage = Storage(os.path.join(self.folder, "viator.db"))
        self.blocklist_path = os.path.join(self.folder, "blocklist.txt")
        self.blocker = Blocker(self.settings.get("adblock"), self.blocklist_path, qapp)

        qapp.setStyle("Fusion")  # stesso aspetto su Windows, macOS e Linux
        self.apply_theme()
        try:
            qapp.styleHints().colorSchemeChanged.connect(self._on_system_theme_changed)
        except AttributeError:  # Qt più vecchie di 6.5
            pass

        self.tray = None
        self._last_notification = None
        self.start_page_handler = StartPageHandler(self, qapp)
        # profilo persistente: cookie, cache, accessi e permessi restano salvati
        self.profile = QWebEngineProfile("viator", qapp)
        self.profile.setPersistentPermissionsPolicy(
            QWebEngineProfile.PersistentPermissionsPolicy.StoreOnDisk
        )
        self.configure_profile(self.profile)

        self.downloads = DownloadManager(self)

        # salvataggio periodico della sessione (utile se il computer si spegne di colpo)
        self._session_timer = QTimer(qapp)
        self._session_timer.timeout.connect(self.save_session)
        self._session_timer.start(20_000)
        qapp.aboutToQuit.connect(self._on_about_to_quit)

    def configure_profile(self, profile):
        """Impostazioni comuni al profilo normale e a quelli privati."""
        profile.setUrlRequestInterceptor(self.blocker)
        profile.downloadRequested.connect(self.handle_download)
        profile.installUrlSchemeHandler(SCHEME, self.start_page_handler)
        profile.setNotificationPresenter(self._show_notification)
        s = profile.settings()
        s.setAttribute(Attr.PluginsEnabled, True)            # serve al lettore PDF
        s.setAttribute(Attr.PdfViewerEnabled, True)          # i PDF si aprono in una scheda
        s.setAttribute(Attr.FullScreenSupportEnabled, True)  # video a schermo intero
        s.setAttribute(Attr.ScreenCaptureEnabled, True)      # condivisione schermo nelle videochiamate
        s.setAttribute(Attr.ScrollAnimatorEnabled, True)     # scorrimento morbido

    # ------------------------------------------------------------ tema
    def apply_theme(self):
        mode = self.settings.get("theme")
        dark = mode == "dark" or (mode == "auto" and system_is_dark())
        if self.theme is not None and self.theme.dark == dark:
            return
        self.theme = Theme(dark, os.path.join(self.folder, "icons"))
        self.qapp.setPalette(self.theme.palette())
        self.qapp.setStyleSheet(self.theme.stylesheet())
        self.qapp.setWindowIcon(self.theme.logo())
        for w in self.windows:
            w.apply_theme()
        if self.downloads:
            self.downloads.apply_theme()

    def _on_system_theme_changed(self, *args):
        if self.settings.get("theme") == "auto":
            self.apply_theme()

    # ------------------------------------------------------- notifiche
    def _show_notification(self, notification):
        """Le notifiche dei siti (a cui hai dato il permesso) arrivano dal sistema."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        if self.tray is None:
            self.tray = QSystemTrayIcon(self.theme.logo(), self.qapp)
            self.tray.setToolTip(APP_NAME)
            self.tray.messageClicked.connect(self._on_notification_clicked)
        self.tray.show()
        self._last_notification = notification
        title = notification.title() or notification.origin().host()
        self.tray.showMessage(title, notification.message(), self.theme.logo(), 8000)
        notification.show()

    def _on_notification_clicked(self):
        if self._last_notification is not None:
            self._last_notification.click()
        if self.windows:
            self.windows[-1].raise_()
            self.windows[-1].activateWindow()

    # ---------------------------------------------------------- finestre
    def homepage(self):
        return self.settings.get("start_url") or HOME_URL

    def new_window(self, private=False, url=None, empty=False):
        window = BrowserWindow(self, private=private)
        self.windows.append(window)
        if not empty:
            window.add_tab(url or self.homepage())
        window.show()
        return window

    def window_closed(self, window):
        if window in self.windows:
            self.windows.remove(window)
        if not self.windows:
            self.downloads.close()
            if self.tray:
                self.tray.hide()

    def refresh_bookmark_stars(self):
        for w in self.windows:
            w.update_star()

    def refresh_shields(self):
        for w in self.windows:
            w.update_shield()

    # ---------------------------------------------------------- sessione
    def save_session(self, windows=None):
        if windows is None:
            windows = [w for w in self.windows if not w.private]
        if not windows:
            return  # nessuna finestra normale aperta: lasciamo l'ultima sessione salvata
        data = {"version": 1, "windows": [w.session_state() for w in windows]}
        tmp = self.session_path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.session_path)
        except OSError:
            pass

    def restore_session(self):
        """Riapre le finestre e le schede dell'ultima volta. Restituisce True se ci è riuscito."""
        if not self.settings.get("restore_session"):
            return False
        try:
            with open(self.session_path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return False
        restored = False
        for state in data.get("windows", []):
            tabs = state.get("tabs") or []
            if not tabs:
                continue
            window = self.new_window(empty=True)
            geometry = state.get("geometry")
            if geometry:
                window.restoreGeometry(QByteArray.fromBase64(geometry.encode("ascii")))
            for tab in tabs:
                window.add_tab(tab.get("url"), background=True, lazy_title=tab.get("title", ""))
            current = min(max(0, state.get("current", 0)), window.tabbar.count() - 1)
            window.tabbar.setCurrentIndex(current)
            window._activate(current)
            restored = True
        return restored

    def _on_about_to_quit(self):
        self.quitting = True

    # ---------------------------------------------------------- download
    def handle_download(self, download):
        directory = self.settings.get("download_dir")
        os.makedirs(directory, exist_ok=True)
        download.setDownloadDirectory(directory)
        download.accept()
        self.downloads.add_download(download)
        self.show_downloads()

    def show_downloads(self):
        self.downloads.show()
        self.downloads.raise_()
        self.downloads.activateWindow()

    def quit(self):
        """Esci (Ctrl+Q): ricorda tutte le finestre aperte, poi chiudi."""
        self.save_session()
        self.quitting = True
        for w in list(self.windows):
            w.close()


def run():
    QCoreApplication.setOrganizationName(APP_NAME)
    QCoreApplication.setApplicationName(APP_NAME)
    QCoreApplication.setApplicationVersion(APP_VERSION)
    register_scheme()  # deve avvenire prima di creare l'applicazione
    if sys.platform == "win32":
        # icona e raggruppamento corretti nella barra delle applicazioni di Windows
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("EurekaFoundation.Viator")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setDesktopFileName("viator")
    ctx = AppContext(app)
    urls = [a for a in sys.argv[1:] if not a.startswith("-")]
    restored = ctx.restore_session()
    if urls and restored:
        ctx.windows[0].add_tab(urls[0])  # aperto da un link o da un file: nuova scheda
    elif not restored:
        ctx.new_window(url=urls[0] if urls else None)
    return app.exec()
