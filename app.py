
# Provjerava postoji li FFmpeg (backend), pa otvara prozor (frontend).

import sys

from PyQt6.QtWidgets import QApplication, QMessageBox

import backend
from frontend import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    ffmpeg = backend.find_ffmpeg()
    if not ffmpeg:
        QMessageBox.critical(
            None,
            "FFmpeg nije pronađen",
            "FFmpeg nije instaliran.\n\n"
            "Najlakše rješenje:\n    pip install imageio-ffmpeg\n\n"
            "ili instaliraj FFmpeg s https://ffmpeg.org i dodaj ga u PATH.",
        )
        return 1

    window = MainWindow(ffmpeg)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
