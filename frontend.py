"""
frontend.py - PyQt6 sučelje za MP4 -> MP3 konverter.
Sva stvarna logika je u backend.py; ovdje je samo GUI i nit za konverziju.
"""

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import backend

STYLE = """
QMainWindow, QWidget { background: #10151e; color: #e7edf5; font-size: 13px; }
QLabel#title { font-size: 25px; font-weight: 700; color: #f4f7fb; }
QLabel#subtitle, QLabel#hint { color: #94a3b8; }
QLabel#section { font-size: 14px; font-weight: 600; color: #d9e2ef; }
QListWidget { background: #171f2b; border: 1px solid #293648; border-radius: 12px; padding: 8px; }
QListWidget::item { padding: 9px 10px; border-radius: 7px; }
QListWidget::item:hover { background: #202c3b; }
QListWidget::item:selected { background: #173d48; color: #c9fbf3; }
QLineEdit, QComboBox { background: #171f2b; border: 1px solid #293648; border-radius: 8px; padding: 9px 11px; selection-background-color: #16a394; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #22b8a8; }
QPushButton { background: #202b39; border: 1px solid #2b394c; border-radius: 8px; padding: 9px 14px; color: #dce6f2; }
QPushButton:hover { background: #2a394a; border-color: #40556d; }
QPushButton:disabled { color: #697789; background: #18212c; border-color: #222e3c; }
QPushButton#primary { background: #12a594; border: 1px solid #12a594; color: #071a1a; font-weight: 700; padding: 10px 20px; }
QPushButton#primary:hover { background: #21c3ae; border-color: #21c3ae; }
QPushButton#primary:disabled { background: #245b59; border-color: #245b59; color: #9cbdb7; }
QProgressBar { background: #202b39; border: none; border-radius: 5px; text-align: center; height: 9px; color: transparent; }
QProgressBar::chunk { background: #19b5a2; border-radius: 5px; }
QComboBox QAbstractItemView { background: #171f2b; selection-background-color: #173d48; border: 1px solid #293648; }
"""


class ConvertWorker(QThread):
    """Radi konverziju u pozadini da GUI ostane responzivan."""

    file_started = pyqtSignal(int)
    file_progress = pyqtSignal(int, int)          # index, postotak
    file_finished = pyqtSignal(int, bool, str)    # index, uspjeh, poruka
    all_finished = pyqtSignal()

    def __init__(self, ffmpeg, files, output_dir, bitrate, parent=None):
        super().__init__(parent)
        self.ffmpeg = ffmpeg
        self.files = files
        self.output_dir = output_dir
        self.bitrate = bitrate
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        for i, file in enumerate(self.files):
            if self._cancelled:
                break
            self.file_started.emit(i)
            try:
                out = backend.build_output_path(file, self.output_dir)
                backend.convert(
                    self.ffmpeg,
                    file,
                    out,
                    self.bitrate,
                    on_progress=lambda p, i=i: self.file_progress.emit(i, p),
                    should_cancel=lambda: self._cancelled,
                )
                self.file_finished.emit(i, True, str(out))
            except backend.ConversionCancelled:
                break
            except Exception as e:  # noqa: BLE001
                self.file_finished.emit(i, False, str(e))
        self.all_finished.emit()


class MainWindow(QMainWindow):
    def __init__(self, ffmpeg: str):
        super().__init__()
        self.ffmpeg = ffmpeg
        self.worker = None
        self.files: list[Path] = []
        self.done: set[int] = set()

        self.setWindowTitle("MP4 → MP3 konverter")
        self.resize(760, 680)
        self.setMinimumSize(620, 580)
        self.setAcceptDrops(True)
        self.setStyleSheet(STYLE)

        self._build_ui()

    # ---------- UI ----------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        title = QLabel("Video u MP3")
        title.setObjectName("title")
        subtitle = QLabel("Izdvoji zvuk iz svojih video datoteka u nekoliko klikova.")
        subtitle.setObjectName("subtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        files_header = QHBoxLayout()
        files_title = QLabel("Datoteke za pretvorbu")
        files_title.setObjectName("section")
        self.file_count = QLabel("0 datoteka")
        self.file_count.setObjectName("hint")
        files_header.addWidget(files_title)
        files_header.addStretch()
        files_header.addWidget(self.file_count)
        root.addLayout(files_header)

        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list.setSpacing(3)
        self.list.setToolTip("Povucite video datoteke ovdje ili ih dodajte gumbom ispod.")
        root.addWidget(self.list, 1)

        row = QHBoxLayout()
        self.btn_add = QPushButton("Dodaj datoteke")
        self.btn_remove = QPushButton("Ukloni odabrane")
        self.btn_clear = QPushButton("Očisti sve")
        self.btn_add.clicked.connect(self.add_files_dialog)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear.clicked.connect(self.clear_all)
        for b in (self.btn_add, self.btn_remove, self.btn_clear):
            row.addWidget(b)
        row.addStretch()
        root.addLayout(row)

        # Izlazna mapa
        out_row = QHBoxLayout()
        out_label = QLabel("Izlazna mapa")
        out_label.setObjectName("section")
        out_row.addWidget(out_label)
        self.out_edit = QLineEdit()
        self.out_edit.setReadOnly(True)
        self.out_edit.setPlaceholderText("Ista mapa kao izvorna datoteka")
        btn_out = QPushButton("Odaberi…")
        btn_out_reset = QPushButton("Reset")
        btn_out.clicked.connect(self.choose_output_dir)
        btn_out_reset.clicked.connect(lambda: self.out_edit.clear())
        out_row.addWidget(self.out_edit, 1)
        out_row.addWidget(btn_out)
        out_row.addWidget(btn_out_reset)
        root.addLayout(out_row)

        # Kvaliteta
        q_row = QHBoxLayout()
        quality_label = QLabel("Kvaliteta zvuka")
        quality_label.setObjectName("section")
        q_row.addWidget(quality_label)
        self.bitrate = QComboBox()
        for b in backend.BITRATES:
            self.bitrate.addItem(f"{b} kbps", b)
        self.bitrate.setCurrentIndex(backend.BITRATES.index(backend.DEFAULT_BITRATE))
        q_row.addWidget(self.bitrate)
        q_row.addStretch()
        root.addLayout(q_row)

        # Progress
        self.status = QLabel("Spremno za pretvorbu")
        self.status.setObjectName("hint")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        root.addWidget(self.status)
        root.addWidget(self.progress)

        # Akcije
        act = QHBoxLayout()
        act.addStretch()
        self.btn_cancel = QPushButton("Prekini")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel)
        self.btn_convert = QPushButton("Pretvori u MP3")
        self.btn_convert.setObjectName("primary")
        self.btn_convert.clicked.connect(self.start)
        act.addWidget(self.btn_cancel)
        act.addWidget(self.btn_convert)
        root.addLayout(act)

    # ---------- Datoteke ----------
    def add_files(self, paths):
        existing = set(self.files)
        added = 0
        for p in paths:
            p = Path(p)
            if p in existing or not p.is_file() or not backend.is_supported(p):
                continue
            self.files.append(p)
            existing.add(p)
            self.list.addItem(QListWidgetItem(f"⏳  {p.name}"))
            added += 1
        if added:
            self.status.setText("Datoteke su spremne za pretvorbu")
            self.file_count.setText(f"{len(self.files)} datoteka")

    def add_files_dialog(self):
        exts = " ".join(f"*{e}" for e in sorted(backend.SUPPORTED_EXTENSIONS))
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Odaberi videe", "", f"Video datoteke ({exts});;Sve datoteke (*)"
        )
        self.add_files(paths)

    def remove_selected(self):
        rows = sorted((self.list.row(i) for i in self.list.selectedItems()), reverse=True)
        for r in rows:
            self.list.takeItem(r)
            del self.files[r]
        self.file_count.setText(f"{len(self.files)} datoteka")

    def clear_all(self):
        self.list.clear()
        self.files.clear()
        self.file_count.setText("0 datoteka")
        self.progress.setValue(0)
        self.status.setText("Spremno.")

    def choose_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Odaberi izlaznu mapu")
        if folder:
            self.out_edit.setText(folder)

    # ---------- Drag & drop ----------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        self.add_files(paths)

    # ---------- Konverzija ----------
    def _set_busy(self, busy: bool):
        self.btn_convert.setEnabled(not busy)
        self.btn_cancel.setEnabled(busy)
        for w in (self.btn_add, self.btn_remove, self.btn_clear, self.bitrate):
            w.setEnabled(not busy)

    def start(self):
        if not self.files:
            QMessageBox.information(self, "Nema datoteka", "Prvo dodaj barem jednu datoteku.")
            return

        self.done.clear()
        for i, f in enumerate(self.files):
            self.list.item(i).setText(f"⏳  {f.name}")
        self.progress.setValue(0)
        self._set_busy(True)

        self.worker = ConvertWorker(
            self.ffmpeg,
            list(self.files),
            self.out_edit.text().strip() or None,
            self.bitrate.currentData(),
            self,
        )
        self.worker.file_started.connect(self.on_file_started)
        self.worker.file_progress.connect(self.on_file_progress)
        self.worker.file_finished.connect(self.on_file_finished)
        self.worker.all_finished.connect(self.on_all_finished)
        self.worker.start()

    def cancel(self):
        if self.worker:
            self.status.setText("Prekidam…")
            self.worker.cancel()

    def on_file_started(self, i):
        self.list.item(i).setText(f"🔄  {self.files[i].name}")
        self.status.setText(f"Pretvaram ({i + 1}/{len(self.files)}): {self.files[i].name}")

    def on_file_progress(self, i, percent):
        total = len(self.files)
        self.progress.setValue(int((i + percent / 100) / total * 100))

    def on_file_finished(self, i, ok, message):
        self.done.add(i)
        name = self.files[i].name
        if ok:
            self.list.item(i).setText(f"✅  {name}")
            self.list.item(i).setToolTip(message)
        else:
            self.list.item(i).setText(f"❌  {name}")
            self.list.item(i).setToolTip(message)

    def on_all_finished(self):
        cancelled = self.worker._cancelled if self.worker else False
        self._set_busy(False)
        if cancelled:
            for i, f in enumerate(self.files):
                if i not in self.done:
                    self.list.item(i).setText(f"⏹  {f.name}")
            self.status.setText("Prekinuto.")
        else:
            self.progress.setValue(100)
            self.status.setText("Gotovo! (zadrži miš iznad stavke kako bi vidio putanju)")
        self.worker = None

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(3000)
        event.accept()
