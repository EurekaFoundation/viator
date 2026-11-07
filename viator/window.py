"""Finestra principale del browser: schede in alto, barra di navigazione, pagine."""

import os
import re
from functools import partial
from urllib.parse import quote_plus

from PySide6.QtCore import QEvent, QSize, QStringListModel, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QCursor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCompleter,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QProgressBar,
    QStackedWidget,
    QTabBar,
    QToolButton,
    QToolTip,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView

from . import APP_NAME
from .contextmenu import build_context_menu
from .dialogs import BookmarksDialog, HistoryDialog, SettingsDialog
from .permissions import PermissionBar, ScreenPicker, describe, site_name, state_label
from .startpage import SCHEME, SCHEME_NAME
from .storage import site_title

SAVABLE_SCHEMES = ("http", "https", "file")


def text_to_url(text, search_template):
    """Trasforma ciò che l'utente scrive in un indirizzo o in una ricerca."""
    text = text.strip()
    if not text:
        return None
    looks_like_address = " " not in text and (
        "." in text or ":" in text or text.lower().startswith("localhost")
    )
    if looks_like_address:
        has_scheme = "://" in text or text.lower().startswith(("about:", "data:", "file:"))
        is_local = text.lower().startswith(("localhost", "127.0.0.1"))
        if not has_scheme and not is_local:
            text = "https://" + text  # come Firefox: prima scelta https
        url = QUrl.fromUserInput(text)
        if url.isValid():
            return url
    return QUrl(search_template.format(quote_plus(text)))


class WebView(QWebEngineView):
    def __init__(self, browser_window, profile):
        super().__init__()
        self.browser_window = browser_window
        self.loading = False
        self.progress = 0
        self.pending_url = None   # scheda ripristinata, si carica quando la apri
        self.permissions = []     # richieste di permesso in attesa
        self.devtools = None
        self.setPage(QWebEnginePage(profile, self))

    def target_url(self):
        return self.pending_url if self.pending_url is not None else self.url()

    def contextMenuEvent(self, event):
        request = self.lastContextMenuRequest()
        if request is None:
            return super().contextMenuEvent(event)
        build_context_menu(self.browser_window, self, request).popup(event.globalPos())

    def createWindow(self, window_type):
        # link con target=_blank, popup, Ctrl+clic: si aprono in una nuova scheda
        background = window_type == QWebEnginePage.WebWindowType.WebBrowserBackgroundTab
        return self.browser_window.add_tab(background=background, related=True)


class TabBar(QTabBar):
    newTabRequested = Signal()

    def __init__(self):
        super().__init__()
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setExpanding(False)
        self.setDocumentMode(True)
        self.setDrawBase(False)
        self.setElideMode(Qt.TextElideMode.ElideRight)
        self.setUsesScrollButtons(True)
        self.setIconSize(QSize(16, 16))

    def tabSizeHint(self, index):
        size = super().tabSizeHint(index)
        size.setWidth(max(150, min(size.width(), 240)))
        return size

    def minimumTabSizeHint(self, index):
        size = super().minimumTabSizeHint(index)
        size.setWidth(min(size.width(), 96))
        return size

    def mouseReleaseEvent(self, event):
        # clic con la rotella: chiude la scheda
        if event.button() == Qt.MouseButton.MiddleButton:
            index = self.tabAt(event.position().toPoint())
            if index >= 0:
                self.tabCloseRequested.emit(index)
                return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        # doppio clic nello spazio vuoto: nuova scheda
        if self.tabAt(event.position().toPoint()) < 0:
            self.newTabRequested.emit()
            return
        super().mouseDoubleClickEvent(event)


class BrowserWindow(QMainWindow):
    def __init__(self, ctx, private=False):
        super().__init__()
        self.ctx = ctx
        self.private = private
        self._closing = False
        self._page_fullscreen = False
        self._was_maximized = False
        self._menu_icons = []
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(1280, 820)

        if private:
            # profilo "off the record": nessun dato salvato su disco
            self.profile = QWebEngineProfile()
            ctx.configure_profile(self.profile)
        else:
            self.profile = ctx.profile

        self._build_ui()
        self._build_actions()
        self.apply_theme()
        self._update_title()

    # ================================================================= UI
    def _tool_button(self, tooltip, slot):
        b = QToolButton()
        b.setToolTip(tooltip)
        b.setAutoRaise(True)
        b.setIconSize(QSize(18, 18))
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.clicked.connect(slot)
        return b

    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- fascia delle schede
        self.tabstrip = QWidget()
        self.tabstrip.setObjectName("TabStrip")
        self.tabstrip.setProperty("private", self.private)
        strip = QHBoxLayout(self.tabstrip)
        strip.setContentsMargins(6, 0, 8, 0)
        strip.setSpacing(2)
        self.tabbar = TabBar()
        self.tabbar.tabCloseRequested.connect(self.close_tab)
        self.tabbar.currentChanged.connect(self._activate)
        self.tabbar.newTabRequested.connect(self.new_tab)
        self.btn_newtab = self._tool_button("Nuova scheda (Ctrl+T)", self.new_tab)
        strip.addWidget(self.tabbar)
        strip.addWidget(self.btn_newtab)
        strip.addStretch(1)
        if self.private:
            badge = QLabel("Navigazione privata")
            badge.setObjectName("PrivateBadge")
            strip.addWidget(badge)

        # ---- barra di navigazione
        self.navbar = QWidget()
        self.navbar.setObjectName("NavBar")
        nav = QHBoxLayout(self.navbar)
        nav.setContentsMargins(8, 6, 8, 6)
        nav.setSpacing(2)
        self.btn_back = self._tool_button("Indietro (Alt+←)", lambda: self._with_view(lambda v: v.back()))
        self.btn_forward = self._tool_button("Avanti (Alt+→)", lambda: self._with_view(lambda v: v.forward()))
        self.btn_reload = self._tool_button("Ricarica (F5)", self._reload_or_stop)
        self.btn_home = self._tool_button("Pagina iniziale (Alt+Home)", self.go_home)
        for b in (self.btn_back, self.btn_forward, self.btn_reload, self.btn_home):
            nav.addWidget(b)
        nav.addSpacing(6)

        self.urlbar = QLineEdit()
        self.urlbar.setObjectName("UrlBar")
        self.urlbar.setPlaceholderText("Cerca o inserisci un indirizzo")
        self.urlbar.returnPressed.connect(self.navigate_from_urlbar)
        self.site_action = self.urlbar.addAction(self.ctx.theme.icon("search", "muted"),
                                                 QLineEdit.ActionPosition.LeadingPosition)
        self.site_action.triggered.connect(self._show_site_info)
        self.star_action = self.urlbar.addAction(self.ctx.theme.icon("star", "muted"),
                                                 QLineEdit.ActionPosition.TrailingPosition)
        self.star_action.triggered.connect(self.toggle_bookmark)
        self.completer_model = QStringListModel(self)
        completer = QCompleter(self.completer_model, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.popup().setObjectName("Completer")
        completer.activated.connect(self._on_completer_activated)
        self.urlbar.setCompleter(completer)
        self.urlbar.textEdited.connect(self._update_suggestions)
        nav.addWidget(self.urlbar, 1)
        nav.addSpacing(6)

        self.btn_shield = QToolButton()
        self.btn_shield.setObjectName("ShieldButton")
        self.btn_shield.setIconSize(QSize(18, 18))
        self.btn_shield.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_shield.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_shield.clicked.connect(
            lambda: QToolTip.showText(QCursor.pos(), self.btn_shield.toolTip(), self.btn_shield)
        )
        self.btn_downloads = self._tool_button("Download (Ctrl+J)", self.ctx.show_downloads)
        self.btn_menu = QToolButton()
        self.btn_menu.setToolTip("Apri il menu")
        self.btn_menu.setIconSize(QSize(18, 18))
        self.btn_menu.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.btn_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu = QMenu(self)
        self.btn_menu.setMenu(self.menu)
        for b in (self.btn_shield, self.btn_downloads, self.btn_menu):
            nav.addWidget(b)

        # ---- sottile barra di caricamento
        self.progress = QProgressBar()
        self.progress.setObjectName("PageProgress")
        self.progress.setFixedHeight(2)
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        # ---- richieste di permesso (fotocamera, microfono, posizione…)
        self.permission_bar = PermissionBar(self)

        # ---- pagine
        self.stack = QStackedWidget()
        self.stack.installEventFilter(self)
        self.link_hint = QLabel(self.stack)
        self.link_hint.setObjectName("LinkHint")
        self.link_hint.hide()
        self._hint_timer = QTimer(self)
        self._hint_timer.setSingleShot(True)
        self._hint_timer.timeout.connect(self.link_hint.hide)

        # ---- barra "trova nella pagina"
        self.findbar = QWidget()
        self.findbar.setObjectName("FindBar")
        fb = QHBoxLayout(self.findbar)
        fb.setContentsMargins(10, 6, 10, 6)
        fb.setSpacing(4)
        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("Trova nella pagina")
        self.find_edit.setFixedWidth(300)
        self.find_edit.textChanged.connect(lambda: self.find_text())
        self.find_edit.returnPressed.connect(lambda: self.find_text())
        self.btn_find_prev = self._tool_button("Precedente", lambda: self.find_text(backward=True))
        self.btn_find_next = self._tool_button("Successivo (Invio)", lambda: self.find_text())
        self.find_status = QLabel()
        self.find_status.setObjectName("FindStatus")
        self.btn_find_close = self._tool_button("Chiudi (Esc)", self.close_find)
        for w in (self.find_edit, self.btn_find_prev, self.btn_find_next, self.find_status):
            fb.addWidget(w)
        fb.addStretch(1)
        fb.addWidget(self.btn_find_close)
        esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self.find_edit)
        esc.setContext(Qt.ShortcutContext.WidgetShortcut)
        esc.activated.connect(self.close_find)
        self.findbar.hide()

        root.addWidget(self.tabstrip)
        root.addWidget(self.navbar)
        root.addWidget(self.progress)
        root.addWidget(self.permission_bar)
        root.addWidget(self.stack, 1)
        root.addWidget(self.findbar)
        self.setCentralWidget(central)

    def _action(self, text, slot, shortcut=None, icon=None, menu=True):
        act = QAction(text, self)
        if shortcut:
            shortcuts = shortcut if isinstance(shortcut, (list, tuple)) else [shortcut]
            act.setShortcuts([QKeySequence(s) for s in shortcuts])
        act.triggered.connect(slot)
        self.addAction(act)  # così le scorciatoie funzionano anche fuori dal menu
        if icon:
            self._menu_icons.append((act, icon))
        if menu:
            self.menu.addAction(act)
        return act

    def _build_actions(self):
        ctx = self.ctx
        self._action("Nuova scheda", self.new_tab, "Ctrl+T", "plus")
        self._action("Nuova finestra", lambda: ctx.new_window(), "Ctrl+N", "window")
        self._action("Nuova finestra privata", lambda: ctx.new_window(private=True), "Ctrl+Shift+P", "mask")
        self.menu.addSeparator()
        self._action("Segnalibri", self.show_bookmarks, "Ctrl+Shift+O", "star")
        self._action("Cronologia", self.show_history, "Ctrl+H", "clock")
        self._action("Download", ctx.show_downloads, "Ctrl+J", "download")
        self.menu.addSeparator()
        self._action("Trova nella pagina…", self.open_find, "Ctrl+F", "search")
        self._action("Salva come PDF…", self.save_as_pdf, "Ctrl+Shift+S", "file")
        self._action("Stampa…", self.print_page, "Ctrl+P", "print")
        self._action("Fissa / togli dalla pagina iniziale", self.toggle_pin, None, "thumbtack")
        self._action("Zoom normale", lambda: self._zoom(None), "Ctrl+0", "zoom")
        self._action("Schermo intero", self.toggle_fullscreen, "F11", "expand")
        self.menu.addSeparator()
        self._action("Impostazioni", self.show_settings, "Ctrl+,", "sliders")
        self._action("Esci", ctx.quit, "Ctrl+Q", "exit")
        # scorciatoie senza voce di menu
        hidden = [
            ("Indietro", lambda: self._with_view(lambda v: v.back()), "Alt+Left"),
            ("Avanti", lambda: self._with_view(lambda v: v.forward()), "Alt+Right"),
            ("Ricarica", lambda: self._with_view(lambda v: v.reload()), ["F5", "Ctrl+R"]),
            ("Pagina iniziale", self.go_home, "Alt+Home"),
            ("Segnalibro", self.toggle_bookmark, "Ctrl+D"),
            ("Chiudi scheda", lambda: self.close_tab(self.tabbar.currentIndex()), "Ctrl+W"),
            ("Barra indirizzi", self.focus_urlbar, ["Ctrl+L", "F6", "Alt+D"]),
            ("Scheda successiva", lambda: self._cycle_tab(1), "Ctrl+Tab"),
            ("Scheda precedente", lambda: self._cycle_tab(-1), "Ctrl+Shift+Tab"),
            ("Aumenta zoom", lambda: self._zoom(0.1), ["Ctrl++", "Ctrl+="]),
            ("Riduci zoom", lambda: self._zoom(-0.1), "Ctrl+-"),
        ]
        for text, slot, keys in hidden:
            self._action(text, slot, keys, menu=False)

    def apply_theme(self):
        th = self.ctx.theme
        for button, name in (
            (self.btn_back, "back"), (self.btn_forward, "forward"), (self.btn_home, "home"),
            (self.btn_newtab, "plus"), (self.btn_downloads, "download"), (self.btn_menu, "menu"),
            (self.btn_find_prev, "up"), (self.btn_find_next, "down"), (self.btn_find_close, "close"),
        ):
            button.setIcon(th.icon(name))
        for act, name in self._menu_icons:
            act.setIcon(th.icon(name, "muted"))
        self.setWindowIcon(th.logo())
        self._update_reload_button()
        self._update_site_icon()
        self.update_star()
        self.update_shield()
        self.permission_bar.refresh()
        for i in range(self.tabbar.count()):
            view = self._view_at(i)
            if view and view.url().scheme() == SCHEME_NAME:
                self.tabbar.setTabIcon(i, th.logo())
                view.reload()  # la pagina "nuova scheda" prende i nuovi colori

    # ============================================================= Schede
    def _view_at(self, index):
        return self.tabbar.tabData(index) if 0 <= index < self.tabbar.count() else None

    def _index_of(self, view):
        for i in range(self.tabbar.count()):
            if self.tabbar.tabData(i) is view:
                return i
        return -1

    def current_view(self):
        return self._view_at(self.tabbar.currentIndex())

    def _with_view(self, fn):
        view = self.current_view()
        if view:
            fn(view)

    def add_tab(self, url=None, background=False, related=False, lazy_title=None):
        view = WebView(self, self.profile)
        self.stack.addWidget(view)
        current = self.tabbar.currentIndex()
        position = current + 1 if related and current >= 0 else self.tabbar.count()
        index = self.tabbar.insertTab(position, "Nuova scheda")
        self.tabbar.setTabData(index, view)

        view.titleChanged.connect(partial(self._on_title, view))
        view.iconChanged.connect(partial(self._on_icon, view))
        view.urlChanged.connect(partial(self._on_url, view))
        view.loadStarted.connect(partial(self._on_load_started, view))
        view.loadProgress.connect(partial(self._on_progress, view))
        view.loadFinished.connect(partial(self._on_load_finished, view))
        page = view.page()
        page.linkHovered.connect(self._on_link_hovered)
        page.fullScreenRequested.connect(self._on_fullscreen_request)
        page.findTextFinished.connect(partial(self._on_find_result, view))
        page.permissionRequested.connect(partial(self._on_permission_requested, view))
        page.desktopMediaRequested.connect(lambda request: ScreenPicker(request, self).run())
        page.pdfPrintingFinished.connect(self._on_pdf_saved)
        view.printFinished.connect(lambda ok: self._flash("Stampa inviata" if ok else "Stampa non riuscita"))

        if url is not None:
            url = url if isinstance(url, QUrl) else QUrl.fromUserInput(url)
            if lazy_title is not None:
                view.pending_url = url
                self.tabbar.setTabText(index, lazy_title or url.host() or "Nuova scheda")
                self.tabbar.setTabToolTip(index, lazy_title or url.toString())
            else:
                view.load(url)
        if not background:
            self.tabbar.setCurrentIndex(index)
            self._activate(index)
        return view

    def new_tab(self):
        self.add_tab(self.ctx.homepage())
        self.focus_urlbar()

    def close_tab(self, index):
        view = self._view_at(index)
        if view is None:
            return
        if self.tabbar.count() <= 1:
            self.close()
            return
        self.tabbar.removeTab(index)
        self.stack.removeWidget(view)
        view.deleteLater()

    def _cycle_tab(self, step):
        n = self.tabbar.count()
        if n:
            self.tabbar.setCurrentIndex((self.tabbar.currentIndex() + step) % n)

    def _activate(self, index):
        if self._closing:
            return
        view = self._view_at(index)
        if view is None:
            return
        self.stack.setCurrentWidget(view)
        if view.pending_url is not None:  # scheda ripristinata: caricala ora
            url, view.pending_url = view.pending_url, None
            view.load(url)
        self._show_url(view.target_url())
        self._update_title()
        self._update_nav()
        self._update_reload_button()
        self.progress.setValue(view.progress if view.loading else 0)
        self.update_shield()
        self.link_hint.hide()
        self.permission_bar.refresh()
        if self.findbar.isVisible():
            self.find_text()

    # ================================================== Eventi delle pagine
    def _on_title(self, view, title):
        i = self._index_of(view)
        if i < 0:
            return
        title = title or "Nuova scheda"
        if view.url().scheme() == SCHEME_NAME:
            title = "Nuova scheda"
        self.tabbar.setTabText(i, title)
        self.tabbar.setTabToolTip(i, title)
        if view is self.current_view():
            self._update_title()
        if not self.private and view.url().scheme() in ("http", "https"):
            self.ctx.storage.update_history_title(view.url().toString(), title)

    def _on_icon(self, view, icon):
        i = self._index_of(view)
        if i >= 0:
            if view.url().scheme() == SCHEME_NAME:
                icon = self.ctx.theme.logo()
            self.tabbar.setTabIcon(i, icon)

    def _on_url(self, view, url):
        if url.scheme() == SCHEME_NAME:
            self._on_icon(view, None)
        if view is self.current_view():
            self._show_url(url)
            self._update_nav()

    def _on_load_started(self, view):
        view.loading = True
        view.progress = 0
        if view is self.current_view():
            self._update_reload_button()
            self.progress.setValue(5)

    def _on_progress(self, view, value):
        view.progress = value
        if view is self.current_view():
            self.progress.setValue(max(value, 5))
            self.update_shield()

    def _on_load_finished(self, view, ok):
        view.loading = False
        if view is self.current_view():
            self._update_reload_button()
            self._update_nav()
            self.update_shield()
            QTimer.singleShot(250, lambda: self.progress.setValue(0))
        url = view.url()
        if ok and not self.private and url.scheme() in ("http", "https"):
            self.ctx.storage.add_history(view.title(), url.toString())

    def _on_link_hovered(self, url):
        if not url:
            self.link_hint.hide()
            return
        metrics = self.link_hint.fontMetrics()
        self._flash(metrics.elidedText(url, Qt.TextElideMode.ElideMiddle, 640), timeout=None)

    def _flash(self, text, timeout=1500):
        self.link_hint.setText(text)
        self.link_hint.adjustSize()
        self._place_hint()
        self.link_hint.show()
        self.link_hint.raise_()
        if timeout:
            self._hint_timer.start(timeout)
        else:
            self._hint_timer.stop()

    def _place_hint(self):
        hint = self.link_hint
        hint.move(10, self.stack.height() - hint.height() - 10)

    def eventFilter(self, obj, event):
        if obj is self.stack and event.type() == QEvent.Type.Resize:
            self._place_hint()
        return super().eventFilter(obj, event)

    # ===================================================== Aggiornamenti UI
    def _show_url(self, url):
        hidden = url.isEmpty() or url.scheme() == SCHEME_NAME or url.toString() == "about:blank"
        self.urlbar.setText("" if hidden else url.toDisplayString())
        self.urlbar.setCursorPosition(0)
        self._update_site_icon()
        self.update_star()

    def _update_site_icon(self):
        th = self.ctx.theme
        view = self.current_view()
        scheme = view.url().scheme() if view else ""
        if scheme == "https":
            self.site_action.setIcon(th.icon("lock", "muted"))
            self.site_action.setToolTip("Connessione sicura")
        elif scheme == "http":
            self.site_action.setIcon(th.icon("info", "muted"))
            self.site_action.setToolTip("Connessione non sicura: i dati non sono cifrati")
        else:
            self.site_action.setIcon(th.icon("search", "muted"))
            self.site_action.setToolTip("")

    def _show_site_info(self):
        """Clic sul lucchetto: sicurezza della connessione e permessi del sito."""
        view = self.current_view()
        if not view or view.url().scheme() not in ("http", "https"):
            return
        th = self.ctx.theme
        menu = QMenu(self)
        title = menu.addAction(site_name(view.url()))
        title.setEnabled(False)
        menu.addAction(th.icon(*(("lock", "accent") if view.url().scheme() == "https" else ("info", "muted"))),
                       self.site_action.toolTip()).setEnabled(False)
        origin = QUrl(f"{view.url().scheme()}://{view.url().authority()}")
        saved = [p for p in self.profile.listPermissionsForOrigin(origin) if state_label(p.state()) != "Chiedi"]
        menu.addSeparator()
        if saved:
            for p in saved:
                act = menu.addAction(th.icon(describe(p)[2], "muted"),
                                     f"{describe(p)[1]}: {state_label(p.state())} — clic per ripristinare")
                act.triggered.connect(lambda checked=False, perm=p: (perm.reset(), self._flash("Permesso ripristinato")))
        else:
            menu.addAction("Nessun permesso speciale per questo sito").setEnabled(False)
        menu.addSeparator()
        menu.addAction(th.icon("sliders", "muted"), "Tutti i permessi dei siti…", self.show_permissions)
        menu.popup(self.urlbar.mapToGlobal(self.urlbar.rect().bottomLeft()))

    def _update_title(self):
        view = self.current_view()
        title = "Nuova scheda"
        if view and view.url().scheme() != SCHEME_NAME and view.title():
            title = view.title()
        suffix = " — navigazione privata" if self.private else ""
        self.setWindowTitle(f"{title} — {APP_NAME}{suffix}")

    def _update_nav(self):
        view = self.current_view()
        history = view.history() if view else None
        self.btn_back.setEnabled(bool(history and history.canGoBack()))
        self.btn_forward.setEnabled(bool(history and history.canGoForward()))

    def _update_reload_button(self):
        view = self.current_view()
        loading = bool(view and view.loading)
        self.btn_reload.setIcon(self.ctx.theme.icon("stop" if loading else "reload"))
        self.btn_reload.setToolTip("Interrompi" if loading else "Ricarica (F5)")

    def update_star(self):
        view = self.current_view()
        url = view.url() if view else QUrl()
        savable = url.scheme() in SAVABLE_SCHEMES
        self.star_action.setVisible(savable)
        if not savable:
            return
        saved = self.ctx.storage.is_bookmarked(url.toString())
        self.star_action.setIcon(self.ctx.theme.icon("star-filled", None) if saved
                                 else self.ctx.theme.icon("star", "muted"))
        self.star_action.setToolTip("Rimuovi dai segnalibri (Ctrl+D)" if saved
                                    else "Aggiungi ai segnalibri (Ctrl+D)")

    def update_shield(self):
        th = self.ctx.theme
        blocker = self.ctx.blocker
        if not blocker.enabled:
            self.btn_shield.setIcon(th.icon("shield", "muted"))
            self.btn_shield.setText("")
            self.btn_shield.setToolTip("Blocco dei tracker disattivato (Impostazioni)")
            return
        view = self.current_view()
        count = blocker.blocked_for(view.url().host()) if view else 0
        self.btn_shield.setIcon(th.icon("shield-filled", None) if count else th.icon("shield", "accent"))
        self.btn_shield.setText(str(count) if count else "")
        self.btn_shield.setToolTip(
            f"{count} tracker bloccati in questa pagina" if count
            else "Protezione dai tracker attiva: nessun tracker in questa pagina"
        )

    def _update_suggestions(self, text):
        self.completer_model.setStringList(self.ctx.storage.suggestions(text) if len(text) >= 2 else [])

    # ============================================================= Comandi
    def navigate_from_urlbar(self):
        url = text_to_url(self.urlbar.text(), self.ctx.settings.search_template())
        if url is None:
            return
        view = self.current_view()
        if view:
            view.load(url)
            view.setFocus()
        else:
            self.add_tab(url)

    def _on_completer_activated(self, text):
        self.urlbar.setText(text)
        self.navigate_from_urlbar()

    def focus_urlbar(self):
        self.urlbar.setFocus()
        self.urlbar.selectAll()

    def go_home(self):
        self._with_view(lambda v: v.load(QUrl.fromUserInput(self.ctx.homepage())))

    def _reload_or_stop(self):
        view = self.current_view()
        if view:
            view.stop() if view.loading else view.reload()

    def toggle_bookmark(self):
        view = self.current_view()
        if not view or view.url().scheme() not in SAVABLE_SCHEMES:
            return
        url = view.url().toString()
        if self.ctx.storage.is_bookmarked(url):
            self.ctx.storage.remove_bookmark(url)
            self._flash("Rimosso dai segnalibri")
        else:
            self.ctx.storage.add_bookmark(view.title(), url)
            self._flash("Aggiunto ai segnalibri")
        self.ctx.refresh_bookmark_stars()

    def _zoom(self, delta):
        view = self.current_view()
        if not view:
            return
        if delta is None:
            view.setZoomFactor(1.0)
        else:
            view.setZoomFactor(max(0.25, min(5.0, view.zoomFactor() + delta)))
        self._flash(f"Zoom {round(view.zoomFactor() * 100)}%")

    # ======================================= Permessi, PDF, stampa, fissati
    def _on_permission_requested(self, view, permission):
        view.permissions.append(permission)
        if view is self.current_view():
            self.permission_bar.refresh()
        else:
            i = self._index_of(view)
            if i >= 0:
                self.tabbar.setTabToolTip(i, "Questa scheda chiede un permesso")

    def show_permissions(self):
        from .permissions import PermissionsDialog
        PermissionsDialog(self.profile, self).exec()

    def _suggested_name(self, view, extension):
        name = re.sub(r'[\\/:*?"<>|]+', " ", view.title() or "pagina").strip()[:80] or "pagina"
        return os.path.join(self.ctx.settings.get("download_dir"), f"{name}.{extension}")

    def save_as_pdf(self):
        view = self.current_view()
        if not view:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Salva come PDF", self._suggested_name(view, "pdf"), "PDF (*.pdf)")
        if path:
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            view.page().printToPdf(path)

    def _on_pdf_saved(self, path, ok):
        self._flash(f"PDF salvato: {os.path.basename(path)}" if ok else "Impossibile salvare il PDF")

    def print_page(self):
        view = self.current_view()
        if not view:
            return
        from PySide6.QtPrintSupport import QPrintDialog, QPrinter
        self._printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(self._printer, self)
        dialog.setWindowTitle("Stampa")
        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            view.print(self._printer)

    def toggle_pin(self):
        view = self.current_view()
        if not view or view.url().scheme() not in ("http", "https"):
            self._flash("Si possono fissare solo i siti web")
            return
        url = view.url().toString()
        if self.ctx.storage.is_pinned(url):
            self.ctx.storage.unpin(url)
            self._flash("Tolto dalla pagina iniziale")
        else:
            self.ctx.storage.pin(site_title(view.url().host()), url)
            self._flash("Fissato nella pagina iniziale")

    def inspect(self, view):
        """Strumenti per sviluppatori (utile anche a scuola)."""
        if view.devtools is None:
            dev = QWebEngineView()
            dev.setWindowTitle(f"Strumenti per sviluppatori — {APP_NAME}")
            dev.setWindowIcon(self.ctx.theme.logo())
            dev.resize(1000, 700)
            view.page().setDevToolsPage(dev.page())
            view.destroyed.connect(dev.close)
            view.devtools = dev
        view.triggerPageAction(QWebEnginePage.WebAction.InspectElement)
        view.devtools.show()
        view.devtools.raise_()

    # ============================================================ Sessione
    def session_state(self):
        tabs = []
        for i in range(self.tabbar.count()):
            view = self._view_at(i)
            if view is None:
                continue
            url = view.target_url()
            if url.isEmpty() or url.scheme() in ("data", "about"):
                continue
            if url.scheme() == SCHEME_NAME and url.host() != "home":
                continue
            tabs.append({"url": url.toString(), "title": self.tabbar.tabText(i)})
        return {
            "tabs": tabs,
            "current": max(0, self.tabbar.currentIndex()),
            "geometry": bytes(self.saveGeometry().toBase64()).decode("ascii"),
        }

    # ================================================ Trova nella pagina
    def open_find(self):
        self.findbar.show()
        self.find_edit.setFocus()
        self.find_edit.selectAll()

    def find_text(self, backward=False):
        view = self.current_view()
        if not view:
            return
        text = self.find_edit.text()
        if not text:
            self.find_status.setText("")
        if backward:
            view.findText(text, QWebEnginePage.FindFlag.FindBackward)
        else:
            view.findText(text)

    def _on_find_result(self, view, result):
        if view is not self.current_view() or not self.find_edit.text():
            return
        total = result.numberOfMatches()
        self.find_status.setText(f"{result.activeMatch()} di {total}" if total else "Nessun risultato")

    def close_find(self):
        self._with_view(lambda v: v.findText(""))
        self.find_status.setText("")
        self.findbar.hide()
        self._with_view(lambda v: v.setFocus())

    # =================================================== Schermo intero
    def toggle_fullscreen(self):
        if self._page_fullscreen:
            self._with_view(lambda v: v.triggerPageAction(QWebEnginePage.WebAction.ExitFullScreen))
        else:
            self._set_fullscreen(not self.isFullScreen())

    def _on_fullscreen_request(self, request):
        request.accept()
        self._page_fullscreen = request.toggleOn()
        self._set_fullscreen(request.toggleOn(), hide_chrome=True)

    def _set_fullscreen(self, on, hide_chrome=False):
        if on:
            self._was_maximized = self.isMaximized()
            if hide_chrome:  # video a schermo intero: nascondi tutta l'interfaccia
                for w in (self.tabstrip, self.navbar, self.progress):
                    w.hide()
            self.showFullScreen()
        else:
            for w in (self.tabstrip, self.navbar, self.progress):
                w.show()
            self.showMaximized() if self._was_maximized else self.showNormal()

    # ========================================================== Finestre
    def _open_in_new_tab(self, url):
        self.add_tab(url)
        self.raise_()

    def show_bookmarks(self):
        BookmarksDialog(self.ctx, self._open_in_new_tab, self).show()

    def show_history(self):
        HistoryDialog(self.ctx, self._open_in_new_tab, self).show()

    def show_settings(self):
        SettingsDialog(self.ctx, self).exec()

    def closeEvent(self, event):
        # se è l'ultima finestra normale, ricorda le sue schede per la prossima volta
        if not self.private and not self.ctx.quitting:
            others = [w for w in self.ctx.windows if w is not self and not w.private]
            if not others:
                self.ctx.save_session([self])
        # le pagine vanno eliminate prima del profilo che le usa
        self._closing = True
        views = [self._view_at(i) for i in range(self.tabbar.count())]
        while self.tabbar.count():
            self.tabbar.removeTab(0)
        for v in views:
            if v is not None:
                self.stack.removeWidget(v)
                v.deleteLater()
        if self.private:
            self.profile.deleteLater()
        self.ctx.window_closed(self)
        super().closeEvent(event)
