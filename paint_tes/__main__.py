from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Paint.Tes — local Volta image editor")
    parser.add_argument("images", nargs="*")
    parser.add_argument("--smoke-screenshot", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    # Offline flags must be set before the AI libraries are imported by any worker.
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication, QMessageBox

    from .app import MainWindow
    from .config import Settings
    from .imageops import load_image
    from .theme import STYLE

    app = QApplication(sys.argv[:1])
    app.setApplicationName("Paint.Tes")
    app.setOrganizationName("PaintTes")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    icon = Path(__file__).resolve().parents[1] / "resources" / "paint-tes.svg"
    app.setWindowIcon(QIcon(str(icon)))
    try:
        settings = Settings.load()
    except Exception as error:
        QMessageBox.warning(
            None,
            "Ustawienia Paint.Tes",
            f"Nie udało się odczytać ustawień: {error}\nPlik nie zostanie nadpisany. Popraw go lub przenieś przed uruchomieniem.",
        )
        return 1
    window = MainWindow(settings)
    for name in args.images:
        try:
            window.add_document(load_image(name), Path(name).name, Path(name), clean=True)
        except Exception as error:
            QMessageBox.warning(window, "Obraz", str(error))
    window.show()
    if args.smoke_screenshot:

        def screenshot():
            args.smoke_screenshot.parent.mkdir(parents=True, exist_ok=True)
            window.grab().save(str(args.smoke_screenshot))
            for i in range(window.tabs.count()):
                doc = window.tabs.widget(i).document
                doc.saved_revision = doc.revision
            window.close()
            app.quit()

        QTimer.singleShot(1500, screenshot)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
