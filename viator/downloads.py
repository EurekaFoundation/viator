"""Gestore dei download."""

from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWebEngineCore import QWebEngineDownloadRequest
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

State = QWebEngineDownloadRequest.DownloadState


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


class DownloadItem(QFrame):
    def __init__(self, download, theme):
        super().__init__()
        self.setObjectName("DownloadItem")
        self.download = download
        self.directory = download.downloadDirectory()

        self.icon = QLabel()
        self.icon.setFixedSize(QSize(28, 28))
        self.name = QLabel(download.downloadFileName())
        font = self.name.font()
        font.setBold(True)
        self.name.setFont(font)
        self.info = QLabel()
        self.info.setObjectName("Muted")
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(6)
        self.button = QPushButton("Annulla")
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.button.clicked.connect(self._on_button)

        text = QVBoxLayout()
        text.setSpacing(5)
        text.addWidget(self.name)
        text.addWidget(self.bar)
        text.addWidget(self.info)
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 12, 14, 12)
        row.setSpacing(12)
        row.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignTop)
        row.addLayout(text, 1)
        row.addWidget(self.button)

        self.apply_theme(theme)
        download.receivedBytesChanged.connect(self.refresh)
        download.totalBytesChanged.connect(self.refresh)
        download.stateChanged.connect(self.refresh)
        self.refresh()

    def apply_theme(self, theme):
        self.icon.setPixmap(theme.icon("download", "accent").pixmap(QSize(24, 24)))

    def _state(self):
        try:
            return self.download.state()
        except RuntimeError:  # il download apparteneva a una finestra privata ormai chiusa
            return None

    def refresh(self, *args):
        state = self._state()
        if state is None:
            return
        d = self.download
        received, total = d.receivedBytes(), d.totalBytes()
        if state in (State.DownloadRequested, State.DownloadInProgress):
            if total > 0:
                self.bar.setRange(0, 100)
                self.bar.setValue(int(received * 100 / total))
                self.info.setText(f"{human_size(received)} di {human_size(total)}")
            else:
                self.bar.setRange(0, 0)
                self.info.setText(human_size(received))
            self.button.setText("Annulla")
        elif state == State.DownloadCompleted:
            self.bar.hide()
            self.info.setText(f"Completato · {human_size(received)}")
            self.button.setText("Mostra nella cartella")
        elif state == State.DownloadCancelled:
            self.bar.hide()
            self.info.setText("Annullato")
            self.button.hide()
        elif state == State.DownloadInterrupted:
            self.bar.hide()
            self.info.setText("Interrotto: " + d.interruptReasonString())
            self.button.hide()

    def _on_button(self):
        state = self._state()
        if state == State.DownloadCompleted or state is None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.directory))
        else:
            self.download.cancel()


class DownloadManager(QDialog):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.items = []
        self.setWindowTitle("Download")
        self.resize(560, 460)

        title = QLabel("Download")
        title.setObjectName("DialogTitle")
        self.btn_folder = QToolButton()
        self.btn_folder.setText("Apri cartella")
        self.btn_folder.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_folder.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self.ctx.settings.get("download_dir")))
        )
        header = QHBoxLayout()
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.btn_folder)

        container = QWidget()
        self.list_layout = QVBoxLayout(container)
        self.list_layout.setContentsMargins(0, 0, 4, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.empty = QLabel("Nessun download per ora.\nI file scaricati compariranno qui.")
        self.empty.setObjectName("Muted")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setMinimumHeight(200)
        self.list_layout.addWidget(self.empty)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(12)
        layout.addLayout(header)
        layout.addWidget(scroll)
        self.apply_theme()

    def apply_theme(self):
        self.btn_folder.setIcon(self.ctx.theme.icon("window"))
        for item in self.items:
            item.apply_theme(self.ctx.theme)

    def add_download(self, download):
        self.empty.hide()
        item = DownloadItem(download, self.ctx.theme)
        self.items.append(item)
        self.list_layout.insertWidget(0, item)
