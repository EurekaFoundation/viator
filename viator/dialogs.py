"""Finestre per segnalibri, cronologia e impostazioni."""

import os
from datetime import datetime

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from .config import HOME_URL, SEARCH_ENGINES, THEMES

ROLE = Qt.ItemDataRole.UserRole


class _ListDialog(QDialog):
    title = ""
    columns = ("Titolo", "Indirizzo")

    def __init__(self, ctx, open_url, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.open_url = open_url
        self.setWindowTitle(self.title)
        self.resize(820, 520)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Cerca…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.reload)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(list(self.columns))
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.setColumnWidth(0, 320)
        self.tree.setColumnWidth(1, 320)
        self.tree.itemActivated.connect(lambda item, col: self.open_url(item.data(0, ROLE)["url"]))

        btn_open = QPushButton("Apri")
        btn_open.clicked.connect(self._open_selected)
        btn_open.setDefault(True)
        btn_delete = QPushButton("Elimina")
        btn_delete.setAutoDefault(False)
        btn_delete.clicked.connect(self._delete_selected)
        buttons = QHBoxLayout()
        self.add_extra_buttons(buttons)
        buttons.addStretch()
        buttons.addWidget(btn_delete)
        buttons.addWidget(btn_open)

        heading = QLabel(self.title)
        heading.setObjectName("DialogTitle")
        top = QHBoxLayout()
        top.addWidget(heading)
        top.addStretch(1)
        self.search.setFixedWidth(280)
        top.addWidget(self.search)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(12)
        layout.addLayout(top)
        layout.addWidget(self.tree)
        layout.addLayout(buttons)
        self.reload()

    # da ridefinire nelle sottoclassi
    def fetch(self, query):
        return []

    def values(self, row):
        return [row["title"], row["url"]]

    def delete_rows(self, rows):
        pass

    def add_extra_buttons(self, layout):
        pass

    def reload(self, *args):
        self.tree.clear()
        for row in self.fetch(self.search.text()):
            item = QTreeWidgetItem(self.values(row))
            item.setToolTip(1, row["url"])
            item.setData(0, ROLE, row)
            self.tree.addTopLevelItem(item)

    def _selected_rows(self):
        return [item.data(0, ROLE) for item in self.tree.selectedItems()]

    def _open_selected(self):
        for row in self._selected_rows():
            self.open_url(row["url"])

    def _delete_selected(self):
        rows = self._selected_rows()
        if rows:
            self.delete_rows(rows)
            self.reload()


class BookmarksDialog(_ListDialog):
    title = "Segnalibri"

    def fetch(self, query):
        return self.ctx.storage.bookmarks(query)

    def delete_rows(self, rows):
        for row in rows:
            self.ctx.storage.remove_bookmark(row["url"])
        self.ctx.refresh_bookmark_stars()


class HistoryDialog(_ListDialog):
    title = "Cronologia"
    columns = ("Titolo", "Indirizzo", "Visitato")

    def fetch(self, query):
        return self.ctx.storage.history(query)

    def values(self, row):
        when = datetime.fromtimestamp(row["visited"]).strftime("%d/%m/%Y %H:%M")
        return [row["title"], row["url"], when]

    def delete_rows(self, rows):
        self.ctx.storage.delete_history([r["id"] for r in rows])

    def add_extra_buttons(self, layout):
        btn = QPushButton("Cancella tutta la cronologia")
        btn.setAutoDefault(False)
        btn.clicked.connect(self._clear_all)
        layout.addWidget(btn)

    def _clear_all(self):
        answer = QMessageBox.question(self, "Cronologia", "Vuoi cancellare tutta la cronologia?")
        if answer == QMessageBox.StandardButton.Yes:
            self.ctx.storage.clear_history()
            self.reload()


class SettingsDialog(QDialog):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        s = ctx.settings
        self.setWindowTitle("Impostazioni")
        self.resize(660, 660)

        self.theme = QComboBox()
        for key, label in THEMES.items():
            self.theme.addItem(label, key)
        self.theme.setCurrentIndex(max(0, self.theme.findData(s.get("theme"))))

        self.engine = QComboBox()
        self.engine.addItems(list(SEARCH_ENGINES))
        self.engine.setCurrentText(s.get("search_engine"))

        start = s.get("start_url")
        self.homepage = QLineEdit("" if start == HOME_URL else start)
        self.homepage.setPlaceholderText("Pagina iniziale di Viator")
        self.restore = QCheckBox("All'avvio riapri le schede dell'ultima volta")
        self.restore.setChecked(s.get("restore_session"))

        self.download_dir = QLineEdit(s.get("download_dir"))
        browse = QPushButton("Sfoglia…")
        browse.clicked.connect(self._browse)
        dl_row = QHBoxLayout()
        dl_row.addWidget(self.download_dir, 1)
        dl_row.addWidget(browse)

        self.adblock = QCheckBox("Blocca tracker e pubblicità")
        self.adblock.setChecked(s.get("adblock"))
        blocklist_info = QLabel("Puoi bloccare altri domini scrivendoli nel file blocklist.txt\nnella cartella dei dati di Viator.")
        blocklist_info.setObjectName("Muted")
        open_folder = QPushButton("Apri cartella dei dati")
        open_folder.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(ctx.blocklist_path)))
        )
        clear_data = QPushButton("Elimina cookie e dati dei siti")
        clear_data.clicked.connect(self._clear_site_data)
        permissions = QPushButton("Permessi dei siti…")
        permissions.clicked.connect(self._show_permissions)
        for b in (browse, clear_data, open_folder, permissions):
            b.setAutoDefault(False)

        heading = QLabel("Impostazioni")
        heading.setObjectName("DialogTitle")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(6)
        layout.addWidget(heading)

        form = QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(form)

        def section(title, rows):
            label = QLabel(title)
            label.setObjectName("SectionTitle")
            form.addRow(label)
            for text, widget in rows:
                form.addRow(text, widget)

        section("Aspetto", [("Tema:", self.theme)])
        section("Ricerca e avvio", [("Motore di ricerca:", self.engine), ("Pagina iniziale:", self.homepage), ("", self.restore)])
        section("Privacy", [("", self.adblock), ("", blocklist_info), ("", open_folder), ("", permissions), ("", clear_data)])
        section("Download", [("Salva i file in:", dl_row)])
        layout.addStretch(1)

        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        box.button(QDialogButtonBox.StandardButton.Save).setText("Salva")
        box.button(QDialogButtonBox.StandardButton.Save).setDefault(True)
        box.button(QDialogButtonBox.StandardButton.Cancel).setText("Annulla")
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        layout.addWidget(box)

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "Cartella download", self.download_dir.text())
        if path:
            self.download_dir.setText(path)

    def _show_permissions(self):
        from .permissions import PermissionsDialog
        PermissionsDialog(self.ctx.profile, self).exec()

    def _clear_site_data(self):
        profile = self.ctx.profile
        profile.cookieStore().deleteAllCookies()
        profile.clearHttpCache()
        QMessageBox.information(self, "Privacy", "Cookie e cache eliminati.")

    def accept(self):
        s = self.ctx.settings
        s.set("theme", self.theme.currentData())
        s.set("search_engine", self.engine.currentText())
        s.set("start_url", self.homepage.text().strip() or HOME_URL)
        s.set("adblock", self.adblock.isChecked())
        s.set("restore_session", self.restore.isChecked())
        s.set("download_dir", self.download_dir.text().strip())
        self.ctx.blocker.enabled = self.adblock.isChecked()
        self.ctx.apply_theme()
        self.ctx.refresh_shields()
        super().accept()
