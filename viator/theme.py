"""Tema grafico di Viator: colori chiaro/scuro, icone e foglio di stile."""

import os
from string import Template

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPalette

# ---------------------------------------------------------------- Colori
LIGHT = {
    "frame": "#E8EBEE",          # fascia delle schede
    "surface": "#FFFFFF",        # barra di navigazione, scheda attiva, finestre
    "field": "#EEF0F3",          # barra degli indirizzi e campi
    "field_hover": "#E3E6EA",
    "page": "#F6F7F9",           # sfondo pagina nuova scheda
    "text": "#1B1D20",
    "muted": "#5E6570",
    "border": "#D4D9DF",
    "hover": "rgba(0, 0, 0, 0.07)",
    "pressed": "rgba(0, 0, 0, 0.13)",
    "accent": "#0B7A75",
    "accent_text": "#FFFFFF",
    "accent_soft": "rgba(11, 122, 117, 0.14)",
    "private_frame": "#E6DDF4",
    "private_accent": "#6B3FB0",
    "scroll": "rgba(0, 0, 0, 0.22)",
}

DARK = {
    "frame": "#16181B",
    "surface": "#24272C",
    "field": "#16181B",
    "field_hover": "#1D2024",
    "page": "#1B1D21",
    "text": "#ECEEF1",
    "muted": "#A0A7B0",
    "border": "#363B42",
    "hover": "rgba(255, 255, 255, 0.08)",
    "pressed": "rgba(255, 255, 255, 0.15)",
    "accent": "#3CC6BE",
    "accent_text": "#062220",
    "accent_soft": "rgba(60, 198, 190, 0.18)",
    "private_frame": "#21172F",
    "private_accent": "#A57BEF",
    "scroll": "rgba(255, 255, 255, 0.22)",
}

# ---------------------------------------------------------------- Icone
# Icone a tratto in una griglia 24x24, disegnate per Viator.
ICONS = {
    "back": '<path d="M15 5l-7 7 7 7"/>',
    "forward": '<path d="M9 5l7 7-7 7"/>',
    "reload": '<path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3"/><path d="M19.5 4.5V9H15"/>',
    "stop": '<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>',
    "home": '<path d="M4 11.5l8-7 8 7"/><path d="M6.5 10v9.5h4v-5h3v5h4V10"/>',
    "star": '<path d="M12 3.8l2.5 5.2 5.7.8-4.1 4 1 5.7L12 16.8l-5.1 2.7 1-5.7-4.1-4 5.7-.8z"/>',
    "menu": '<path d="M4.5 7h15M4.5 12h15M4.5 17h15"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "close": '<path d="M7.5 7.5l9 9M16.5 7.5l-9 9"/>',
    "lock": '<rect x="5.5" y="10.5" width="13" height="9" rx="2"/><path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5"/>',
    "info": '<circle cx="12" cy="12" r="8"/><path d="M12 11v5"/><path d="M12 8h.01"/>',
    "search": '<circle cx="11" cy="11" r="6"/><path d="M20 20l-4.5-4.5"/>',
    "shield": '<path d="M12 3.5l7 2.8v5.4c0 4.3-2.9 7.3-7 8.8-4.1-1.5-7-4.5-7-8.8V6.3z"/>',
    "download": '<path d="M12 4.5v10M7.5 10.5l4.5 4.5 4.5-4.5M5 19.5h14"/>',
    "up": '<path d="M6 15l6-6 6 6"/>',
    "down": '<path d="M6 9l6 6 6-6"/>',
    "mask": '<circle cx="7.5" cy="14.5" r="3"/><circle cx="16.5" cy="14.5" r="3"/>'
            '<path d="M10.5 14.5h3M3 12l2.2-5.5h13.6L21 12"/>',
    "clock": '<circle cx="12" cy="12" r="8"/><path d="M12 7.5V12l3 2"/>',
    "sliders": '<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>',
    "window": '<rect x="4" y="5" width="16" height="14" rx="2"/><path d="M4 9h16"/>',
    "zoom": '<circle cx="11" cy="11" r="6"/><path d="M20 20l-4.5-4.5M8.5 11h5M11 8.5v5"/>',
    "expand": '<path d="M4.5 9V4.5H9M15 4.5h4.5V9M19.5 15v4.5H15M9 19.5H4.5V15"/>',
    "mic": '<rect x="9" y="3.5" width="6" height="11" rx="3"/><path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v2.5"/>',
    "camera": '<rect x="3.5" y="7" width="12" height="10" rx="2"/><path d="M15.5 10.5l5-3v9l-5-3"/>',
    "monitor": '<rect x="3.5" y="4.5" width="17" height="11.5" rx="2"/><path d="M9 20h6M12 16v4"/>',
    "bell": '<path d="M6 16.5V11a6 6 0 0 1 12 0v5.5l1.5 1.5h-15z"/><path d="M10 20.5a2 2 0 0 0 4 0"/>',
    "pin": '<path d="M12 21s-6.5-6-6.5-11a6.5 6.5 0 0 1 13 0c0 5-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.3"/>',
    "clipboard": '<rect x="5.5" y="5" width="13" height="15.5" rx="2"/><path d="M9 5V3.5h6V5"/>',
    "thumbtack": '<path d="M9 3.5h6M10 3.5v6l-3 4h10l-3-4v-6M12 13.5v7"/>',
    "print": '<path d="M7 9V3.5h10V9"/><rect x="3.5" y="9" width="17" height="8" rx="2"/><path d="M7 14.5h10v6H7z"/>',
    "code": '<path d="M8.5 7l-5 5 5 5M15.5 7l5 5-5 5"/>',
    "copy": '<rect x="8.5" y="8.5" width="11" height="11" rx="2"/>'
            '<path d="M15.5 8.5V6a1.5 1.5 0 0 0-1.5-1.5H6A1.5 1.5 0 0 0 4.5 6v8A1.5 1.5 0 0 0 6 15.5h2.5"/>',
    "link": '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/>'
            '<path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
    "image": '<rect x="4" y="5" width="16" height="14" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="M20 16l-5-5-8 8"/>',
    "file": '<path d="M13.5 3.5H7a1.5 1.5 0 0 0-1.5 1.5v14A1.5 1.5 0 0 0 7 20.5h10a1.5 1.5 0 0 0 1.5-1.5V8.5z"/><path d="M13.5 3.5v5h5"/>',
    "check": '<path d="M5.5 12.5l4 4 9-9"/>',
    "exit": '<path d="M14 4.5h4a1.5 1.5 0 0 1 1.5 1.5v12a1.5 1.5 0 0 1-1.5 1.5h-4"/><path d="M10 16l-4-4 4-4M6 12h9"/>',
}


def _svg(body, stroke, fill="none", fill_opacity="1"):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
        f'fill="{fill}" fill-opacity="{fill_opacity}" stroke="{stroke}" stroke-width="1.8" '
        f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )


def logo_svg(accent="#0B7A75", needle="#FFFFFF"):
    """Logo di Viator: una bussola."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">'
        f'<circle cx="32" cy="32" r="30" fill="{accent}"/>'
        f'<circle cx="32" cy="32" r="22.5" fill="none" stroke="{needle}" stroke-opacity=".35" stroke-width="2"/>'
        '<g transform="rotate(35 32 32)">'
        f'<path d="M32 11 L39 32 H25 Z" fill="{needle}"/>'
        f'<path d="M32 53 L39 32 H25 Z" fill="{needle}" fill-opacity=".5"/>'
        "</g>"
        f'<circle cx="32" cy="32" r="3" fill="{accent}"/>'
        "</svg>"
    )


def system_is_dark():
    try:
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except AttributeError:  # Qt più vecchie di 6.5
        return QGuiApplication.palette().color(QPalette.ColorRole.Window).lightness() < 128


# ---------------------------------------------------------------- Stile
QSS = Template(r"""
QWidget { color: $text; }
QMainWindow, QDialog { background: $surface; }

/* ----- fascia delle schede ----- */
#TabStrip { background: $frame; }
#TabStrip[private="true"] { background: $private_frame; }
QTabBar { background: transparent; qproperty-drawBase: 0; }
QTabBar::tab {
    background: transparent; color: $muted;
    padding: 7px 8px 7px 10px; margin: 5px 2px 5px 0px;
    border: 1px solid transparent; border-radius: 9px;
}
QTabBar::tab:hover { background: $hover; color: $text; }
QTabBar::tab:selected { background: $surface; color: $text; border: 1px solid $border; }
QTabBar::close-button {
    image: url("$i_close_muted"); subcontrol-position: right;
    border-radius: 5px; padding: 1px; margin-left: 4px;
}
QTabBar::close-button:hover { image: url("$i_close_text"); background: $hover; }
QTabBar QToolButton { background: $frame; border: none; border-radius: 6px; }
QTabBar::tear { width: 0px; border: none; }

#PrivateBadge {
    background: $private_accent; color: #FFFFFF; font-weight: 600;
    border-radius: 10px; padding: 3px 10px; margin: 4px 0px;
}

/* ----- barra di navigazione ----- */
#NavBar { background: $surface; border-bottom: 1px solid $border; }
QToolButton {
    background: transparent; border: none; border-radius: 7px;
    padding: 6px; color: $text;
}
QToolButton:hover { background: $hover; }
QToolButton:pressed, QToolButton:checked { background: $pressed; }
QToolButton:disabled { background: transparent; }
QToolButton::menu-indicator { image: none; width: 0px; }
#ShieldButton { color: $accent; font-weight: 600; padding: 6px 8px; }

#UrlBar {
    background: $field; border: 1px solid transparent; border-radius: 11px;
    padding: 7px 6px; font-size: 14px;
    selection-background-color: $accent; selection-color: $accent_text;
}
#UrlBar:hover { background: $field_hover; }
#UrlBar:focus { background: $surface; border: 2px solid $accent; padding: 6px 5px; }

#PageProgress { background: transparent; border: none; }
#PageProgress::chunk { background: $accent; }

/* ----- barra dei permessi ----- */
#PermissionBar { background: $accent_soft; border-bottom: 1px solid $border; }
QPushButton#Primary { background: $accent; color: $accent_text; border: 1px solid $accent; font-weight: 600; }
QListWidget::item { padding: 8px 6px; border-radius: 6px; }
QListWidget::item:selected { background: $accent_soft; color: $text; }

/* ----- barra "trova nella pagina" e suggerimento link ----- */
#FindBar { background: $surface; border-top: 1px solid $border; }
#FindStatus { color: $muted; padding-left: 6px; }
#LinkHint {
    background: $surface; color: $muted; border: 1px solid $border;
    border-radius: 7px; padding: 4px 9px;
}

/* ----- menu, suggerimenti e tooltip ----- */
QMenu {
    background: $surface; border: 1px solid $border; border-radius: 12px; padding: 6px;
}
QMenu::item { padding: 8px 34px 8px 10px; border-radius: 7px; }
QMenu::item:selected { background: $hover; }
QMenu::icon { padding-left: 8px; }
QMenu::separator { height: 1px; background: $border; margin: 5px 8px; }
QToolTip {
    background: $surface; color: $text; border: 1px solid $border;
    border-radius: 7px; padding: 5px 8px;
}
QAbstractItemView#Completer, QListView {
    background: $surface; border: 1px solid $border; border-radius: 10px; padding: 4px;
    selection-background-color: $accent_soft; selection-color: $text; outline: 0;
}

/* ----- campi e pulsanti delle finestre di dialogo ----- */
QLineEdit {
    background: $field; border: 1px solid $border; border-radius: 8px; padding: 6px 8px;
    selection-background-color: $accent; selection-color: $accent_text;
}
QLineEdit:focus { border: 1px solid $accent; }
QPushButton {
    background: $field; border: 1px solid $border; border-radius: 8px; padding: 7px 16px;
}
QPushButton:hover { background: $field_hover; }
QPushButton:pressed { background: $pressed; }
QPushButton:default { background: $accent; color: $accent_text; border: 1px solid $accent; font-weight: 600; }
QComboBox {
    background: $field; border: 1px solid $border; border-radius: 8px; padding: 6px 10px;
}
QComboBox:hover { background: $field_hover; }
QComboBox::drop-down { border: none; width: 26px; }
QComboBox::down-arrow { image: url("$i_down_muted"); width: 14px; height: 14px; }
QComboBox QAbstractItemView {
    background: $surface; border: 1px solid $border; padding: 4px;
    selection-background-color: $accent_soft; selection-color: $text; outline: 0;
}
QCheckBox { spacing: 9px; }
QCheckBox::indicator {
    width: 16px; height: 16px; border: 1px solid $border; border-radius: 5px; background: $field;
}
QCheckBox::indicator:hover { border: 1px solid $accent; }
QCheckBox::indicator:checked { background: $accent; border: 1px solid $accent; image: url("$i_check"); }
#SectionTitle { font-weight: 600; padding-top: 14px; padding-bottom: 2px; }
#Muted { color: $muted; }
#DialogTitle { font-size: 18px; font-weight: 600; }

QTreeWidget {
    background: $surface; alternate-background-color: $page;
    border: 1px solid $border; border-radius: 10px; outline: 0;
}
QTreeWidget::item { padding: 6px 4px; }
QTreeWidget::item:selected { background: $accent_soft; color: $text; }
QHeaderView::section {
    background: $page; color: $muted; border: none;
    border-bottom: 1px solid $border; padding: 7px 6px; font-weight: 600;
}

/* ----- download ----- */
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
#DownloadItem { background: $page; border: 1px solid $border; border-radius: 12px; }
QProgressBar { background: $field; border: none; border-radius: 3px; }
QProgressBar::chunk { background: $accent; border-radius: 3px; }

/* ----- barre di scorrimento ----- */
QScrollBar:vertical { background: transparent; width: 11px; margin: 2px; }
QScrollBar:horizontal { background: transparent; height: 11px; margin: 2px; }
QScrollBar::handle { background: $scroll; border-radius: 3px; }
QScrollBar::handle:vertical { min-height: 32px; }
QScrollBar::handle:horizontal { min-width: 32px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0px; height: 0px; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }
""")


class Theme:
    def __init__(self, dark, icon_root):
        self.dark = dark
        self.t = dict(DARK if dark else LIGHT)
        self.dir = os.path.join(icon_root, "dark" if dark else "light")
        os.makedirs(self.dir, exist_ok=True)
        self._write_icons()

    # ---------- icone
    def _write(self, name, svg):
        path = os.path.join(self.dir, name + ".svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)

    def _write_icons(self):
        t = self.t
        for name, body in ICONS.items():
            self._write(f"{name}-text", _svg(body, t["text"]))
            self._write(f"{name}-muted", _svg(body, t["muted"]))
            self._write(f"{name}-accent", _svg(body, t["accent"]))
        self._write("check-on", _svg(ICONS["check"], t["accent_text"]).replace('stroke-width="1.8"', 'stroke-width="3"'))
        self._write("star-filled", _svg(ICONS["star"], t["accent"], fill=t["accent"]))
        self._write("shield-filled", _svg(ICONS["shield"], t["accent"], fill=t["accent"], fill_opacity=".22"))
        self._write("private-mask", _svg(ICONS["mask"], t["private_accent"]))
        self._write("logo", logo_svg(LIGHT["accent"], "#FFFFFF"))

    def path(self, name, variant="text"):
        file = f"{name}-{variant}.svg" if variant else f"{name}.svg"
        return os.path.join(self.dir, file).replace("\\", "/")

    def icon(self, name, variant="text"):
        icon = QIcon(self.path(name, variant))
        if variant == "text":  # pulsanti disattivati: icona più chiara
            icon.addFile(self.path(name, "muted"), mode=QIcon.Mode.Disabled)
        return icon

    def logo(self):
        return QIcon(self.path("logo", None))

    # ---------- palette e foglio di stile
    def palette(self):
        t = self.t
        p = QPalette()
        R = QPalette.ColorRole
        for role, key in (
            (R.Window, "surface"), (R.WindowText, "text"), (R.Base, "surface"),
            (R.AlternateBase, "page"), (R.Text, "text"), (R.Button, "field"),
            (R.ButtonText, "text"), (R.Highlight, "accent"), (R.HighlightedText, "accent_text"),
            (R.ToolTipBase, "surface"), (R.ToolTipText, "text"), (R.PlaceholderText, "muted"),
            (R.Link, "accent"),
        ):
            p.setColor(role, QColor(t[key]))
        for role in (R.WindowText, R.Text, R.ButtonText):
            p.setColor(QPalette.ColorGroup.Disabled, role, QColor(t["muted"]))
        return p

    def stylesheet(self):
        values = dict(self.t)
        values["i_close_muted"] = self.path("close", "muted")
        values["i_close_text"] = self.path("close", "text")
        values["i_down_muted"] = self.path("down", "muted")
        values["i_check"] = self.path("check-on", None)
        return QSS.substitute(values)
