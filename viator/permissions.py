"""Permessi dei siti: fotocamera, microfono, posizione, notifiche, schermo…"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtWebEngineCore import QWebEnginePermission
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

Type = QWebEnginePermission.PermissionType
State = QWebEnginePermission.State

# (cosa chiede il sito, nome breve, icona)
INFO = {
    Type.MediaAudioCapture: ("usare il microfono", "Microfono", "mic"),
    Type.MediaVideoCapture: ("usare la fotocamera", "Fotocamera", "camera"),
    Type.MediaAudioVideoCapture: ("usare la fotocamera e il microfono", "Fotocamera e microfono", "camera"),
    Type.DesktopVideoCapture: ("condividere il tuo schermo", "Condivisione schermo", "monitor"),
    Type.DesktopAudioVideoCapture: ("condividere il tuo schermo e l'audio", "Condivisione schermo e audio", "monitor"),
    Type.Notifications: ("mostrarti delle notifiche", "Notifiche", "bell"),
    Type.Geolocation: ("conoscere la tua posizione", "Posizione", "pin"),
    Type.ClipboardReadWrite: ("leggere e scrivere negli appunti", "Appunti", "clipboard"),
    Type.LocalFontsAccess: ("vedere i caratteri installati sul computer", "Caratteri installati", "info"),
    Type.MouseLock: ("bloccare il puntatore del mouse", "Blocco del puntatore", "info"),
}


def describe(permission):
    return INFO.get(permission.permissionType(), ("usare una funzione del computer", "Altro", "info"))


def site_name(origin):
    if origin.scheme() == "file":
        return "Questa pagina locale"
    host = origin.host()
    return host[4:] if host.startswith("www.") else (host or origin.toString())


def state_label(state):
    return {State.Granted: "Consentito", State.Denied: "Bloccato"}.get(state, "Chiedi")


class PermissionBar(QWidget):
    """Barra "Consenti / Blocca" che compare sotto la barra degli indirizzi."""

    def __init__(self, window):
        super().__init__()
        self.window = window
        self.setObjectName("PermissionBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.icon = QLabel()
        self.icon.setFixedSize(QSize(22, 22))
        self.text = QLabel()
        self.text.setTextFormat(Qt.TextFormat.RichText)
        self.btn_deny = QPushButton("Blocca")
        self.btn_allow = QPushButton("Consenti")
        self.btn_allow.setObjectName("Primary")
        for b in (self.btn_deny, self.btn_allow):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setAutoDefault(False)
        self.btn_deny.clicked.connect(lambda: self._decide(False))
        self.btn_allow.clicked.connect(lambda: self._decide(True))
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 8, 14, 8)
        row.setSpacing(10)
        row.addWidget(self.icon)
        row.addWidget(self.text, 1)
        row.addWidget(self.btn_deny)
        row.addWidget(self.btn_allow)
        self.hide()

    def refresh(self):
        """Mostra la prima richiesta in attesa della scheda attiva."""
        view = self.window.current_view()
        pending = getattr(view, "permissions", []) if view else []
        while pending and (not pending[0].isValid() or pending[0].state() != State.Ask):
            pending.pop(0)
        if not pending:
            self.hide()
            return
        permission = pending[0]
        what, _, icon = describe(permission)
        self.icon.setPixmap(self.window.ctx.theme.icon(icon, "accent").pixmap(QSize(20, 20)))
        self.text.setText(f"<b>{site_name(permission.origin())}</b> vuole {what}.")
        self.show()

    def _decide(self, allow):
        view = self.window.current_view()
        if view and view.permissions:
            permission = view.permissions.pop(0)
            if permission.isValid():
                permission.grant() if allow else permission.deny()
        self.refresh()


class PermissionsDialog(QDialog):
    """Elenco dei permessi ricordati, con la possibilità di rimuoverli."""

    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.setWindowTitle("Permessi dei siti")
        self.resize(640, 440)
        heading = QLabel("Permessi dei siti")
        heading.setObjectName("DialogTitle")
        note = QLabel("Le scelte fatte con «Consenti» e «Blocca» vengono ricordate per ogni sito.")
        note.setObjectName("Muted")
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Sito", "Permesso", "Stato"])
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.setColumnWidth(0, 240)
        self.tree.setColumnWidth(1, 220)
        btn_remove = QPushButton("Rimuovi")
        btn_remove.clicked.connect(self._remove_selected)
        btn_clear = QPushButton("Rimuovi tutti")
        btn_clear.clicked.connect(self._remove_all)
        btn_close = QPushButton("Chiudi")
        btn_close.setDefault(True)
        btn_close.clicked.connect(self.accept)
        for b in (btn_remove, btn_clear):
            b.setAutoDefault(False)
        buttons = QHBoxLayout()
        buttons.addWidget(btn_clear)
        buttons.addStretch(1)
        buttons.addWidget(btn_remove)
        buttons.addWidget(btn_close)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(10)
        layout.addWidget(heading)
        layout.addWidget(note)
        layout.addWidget(self.tree)
        layout.addLayout(buttons)
        self.reload()

    def _permissions(self):
        return [p for p in self.profile.listAllPermissions() if p.state() in (State.Granted, State.Denied)]

    def reload(self):
        self.tree.clear()
        for p in sorted(self._permissions(), key=lambda p: site_name(p.origin())):
            item = QTreeWidgetItem([site_name(p.origin()), describe(p)[1], state_label(p.state())])
            item.setData(0, Qt.ItemDataRole.UserRole, p)
            self.tree.addTopLevelItem(item)
        if not self.tree.topLevelItemCount():
            item = QTreeWidgetItem(["Nessun permesso salvato", "", ""])
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.tree.addTopLevelItem(item)

    def _remove_selected(self):
        for item in self.tree.selectedItems():
            p = item.data(0, Qt.ItemDataRole.UserRole)
            if p is not None:
                p.reset()
        self.reload()

    def _remove_all(self):
        if QMessageBox.question(self, "Permessi", "Vuoi rimuovere tutti i permessi salvati?") \
                == QMessageBox.StandardButton.Yes:
            for p in self._permissions():
                p.reset()
            self.reload()


class ScreenPicker(QDialog):
    """Scelta di schermo o finestra da condividere (videochiamate)."""

    def __init__(self, request, parent=None):
        super().__init__(parent)
        self.request = request
        self.setWindowTitle("Condividi lo schermo")
        self.resize(460, 420)
        heading = QLabel("Cosa vuoi condividere?")
        heading.setObjectName("DialogTitle")
        self.list = QListWidget()
        screens, windows = request.screensModel(), request.windowsModel()
        for i in range(screens.rowCount()):
            idx = screens.index(i, 0)
            item = QListWidgetItem(f"Schermo intero — {screens.data(idx) or i + 1}")
            item.setData(Qt.ItemDataRole.UserRole, ("screen", idx))
            self.list.addItem(item)
        for i in range(windows.rowCount()):
            idx = windows.index(i, 0)
            item = QListWidgetItem(f"Finestra — {windows.data(idx)}")
            item.setData(Qt.ItemDataRole.UserRole, ("window", idx))
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)
        self.list.itemDoubleClicked.connect(lambda *_: self.accept())
        btn_cancel = QPushButton("Annulla")
        btn_cancel.setAutoDefault(False)
        btn_cancel.clicked.connect(self.reject)
        btn_share = QPushButton("Condividi")
        btn_share.setDefault(True)
        btn_share.clicked.connect(self.accept)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(btn_cancel)
        buttons.addWidget(btn_share)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.addWidget(heading)
        layout.addWidget(self.list)
        layout.addLayout(buttons)

    def run(self):
        item = self.list.currentItem() if self.exec() == QDialog.DialogCode.Accepted else None
        if item is None:
            self.request.cancel()
            return
        kind, index = item.data(Qt.ItemDataRole.UserRole)
        self.request.selectScreen(index) if kind == "screen" else self.request.selectWindow(index)
