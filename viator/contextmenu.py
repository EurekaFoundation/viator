"""Menu del tasto destro sulle pagine, in italiano."""

from urllib.parse import quote_plus

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtWebEngineCore import QWebEngineContextMenuRequest, QWebEnginePage
from PySide6.QtWidgets import QMenu

WA = QWebEnginePage.WebAction
Media = QWebEngineContextMenuRequest.MediaType


def _copy(text):
    QGuiApplication.clipboard().setText(text)


def build_context_menu(window, view, req):
    ctx = window.ctx
    page = view.page()
    menu = QMenu(view)

    def add(text, slot, icon=None, enabled=True):
        act = menu.addAction(text)
        act.triggered.connect(slot)
        act.setEnabled(enabled)
        if icon:
            act.setIcon(ctx.theme.icon(icon, "muted"))
        return act

    def page_action(text, action, icon=None):
        return add(text, lambda: view.triggerPageAction(action), icon, page.action(action).isEnabled())

    link = req.linkUrl()
    has_link = link.isValid() and not link.isEmpty()
    media = req.mediaType()
    media_url = req.mediaUrl()
    selection = req.selectedText().strip()
    editable = req.isContentEditable()

    # --- correzione ortografica
    if editable and req.misspelledWord():
        suggestions = req.spellCheckerSuggestions()[:5]
        for word in suggestions:
            add(word, lambda checked=False, w=word: page.replaceMisspelledWord(w))
        if not suggestions:
            add("Nessun suggerimento", lambda: None, enabled=False)
        menu.addSeparator()

    # --- link
    if has_link:
        add("Apri il link in una nuova scheda",
            lambda: window.add_tab(link, background=True, related=True), "plus")
        add("Apri il link in una nuova finestra", lambda: ctx.new_window(url=link), "window")
        add("Apri il link in una finestra privata", lambda: ctx.new_window(private=True, url=link), "mask")
        menu.addSeparator()
        add("Copia l'indirizzo del link", lambda: _copy(link.toString()), "link")
        page_action("Salva il link con nome…", WA.DownloadLinkToDisk, "download")
        menu.addSeparator()

    # --- immagini, video, audio
    if media == Media.MediaTypeImage:
        add("Apri l'immagine in una nuova scheda",
            lambda: window.add_tab(media_url, background=True, related=True), "image")
        page_action("Salva l'immagine con nome…", WA.DownloadImageToDisk, "download")
        page_action("Copia l'immagine", WA.CopyImageToClipboard, "copy")
        add("Copia l'indirizzo dell'immagine", lambda: _copy(media_url.toString()), "link")
        menu.addSeparator()
    elif media in (Media.MediaTypeVideo, Media.MediaTypeAudio):
        page_action("Riproduci / pausa", WA.ToggleMediaPlayPause)
        page_action("Attiva / disattiva l'audio", WA.ToggleMediaMute)
        page_action("Ripeti in continuo", WA.ToggleMediaLoop)
        page_action("Mostra i controlli", WA.ToggleMediaControls)
        menu.addSeparator()
        page_action("Salva il file con nome…", WA.DownloadMediaToDisk, "download")
        add("Copia l'indirizzo del file", lambda: _copy(media_url.toString()), "link")
        menu.addSeparator()

    # --- campi di testo
    if editable:
        page_action("Annulla", WA.Undo)
        page_action("Ripeti", WA.Redo)
        menu.addSeparator()
        page_action("Taglia", WA.Cut)
        page_action("Copia", WA.Copy, "copy")
        page_action("Incolla", WA.Paste, "clipboard")
        page_action("Incolla come testo semplice", WA.PasteAndMatchStyle)
        menu.addSeparator()
        page_action("Seleziona tutto", WA.SelectAll)
    elif selection:
        page_action("Copia", WA.Copy, "copy")
        short = selection if len(selection) <= 26 else selection[:25] + "…"
        engine = ctx.settings.get("search_engine")
        search = QUrl(ctx.settings.search_template().format(quote_plus(selection)))
        add(f"Cerca «{short}» con {engine}",
            lambda: window.add_tab(search, related=True), "search")
        menu.addSeparator()

    # --- pagina
    if not (has_link or editable or selection or media != Media.MediaTypeNone):
        history = view.history()
        add("Indietro", view.back, "back", history.canGoBack())
        add("Avanti", view.forward, "forward", history.canGoForward())
        add("Ricarica", view.reload, "reload")
        menu.addSeparator()
        web_page = view.url().scheme() in ("http", "https", "file")
        add("Salva la pagina con nome…", lambda: view.triggerPageAction(WA.SavePage), "download", web_page)
        add("Salva come PDF…", window.save_as_pdf, "file", web_page)
        add("Stampa…", window.print_page, "print", web_page)
        menu.addSeparator()
        if view.url().scheme() in ("http", "https"):
            pinned = ctx.storage.is_pinned(view.url().toString())
            add("Togli dalla pagina iniziale" if pinned else "Fissa nella pagina iniziale",
                window.toggle_pin, "thumbtack")
        page_action("Seleziona tutto", WA.SelectAll)
        page_action("Visualizza il codice della pagina", WA.ViewSource, "code")

    menu.addSeparator()
    add("Ispeziona", lambda: window.inspect(view), "code")
    return menu
