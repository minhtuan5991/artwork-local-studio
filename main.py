import argparse
import json
import sys
from pathlib import Path
from PySide6.QtCore import QLockFile, QTimer
from PySide6.QtGui import QFontDatabase, QFont, QIcon
from PySide6.QtWidgets import QApplication, QMessageBox
from artwork_local.core import Settings, app_root
from artwork_local.ui import MainWindow, STYLE

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--data-dir")
    parser.add_argument("--screenshot")
    args=parser.parse_args()
    app=QApplication(sys.argv[:1]); app.setApplicationName("Artwork Local Studio")
    for name in ["segoeui.ttf","segoeuib.ttf","seguisym.ttf"]:
        font=Path("C:/Windows/Fonts")/name
        if font.is_file(): QFontDatabase.addApplicationFont(str(font))
    app.setFont(QFont("Segoe UI",10))
    app.setStyle("Fusion"); app.setStyleSheet(STYLE)
    try:
        root=app_root(); settings=Settings(root,Path(args.data_dir) if args.data_dir else None)
        app.setWindowIcon(QIcon(str(root/"assets"/"app.ico")))
        lock=QLockFile(str(settings.data/"app.lock")); lock.setStaleLockTime(30000)
        if not lock.tryLock(100):
            return 0
        import ctypes
        from ctypes import wintypes
        kernel=ctypes.windll.kernel32
        kernel.CreateEventW.restype=wintypes.HANDLE
        event=kernel.CreateEventW(None,True,False,"Local\\ArtworkLocalStudio-"+str(settings.data.resolve()).replace("\\","_"))
        manifest=json.loads((root/"model-manifest.json").read_text(encoding="utf-8"))
        window=MainWindow(settings,manifest); window.show()
        if args.screenshot:
            def capture(): window.grab().save(args.screenshot); app.quit()
            QTimer.singleShot(1200,capture)
        result=app.exec()
        kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        if event: kernel.CloseHandle(event)
        return result
    except Exception as exc:
        QMessageBox.critical(None,"Không mở được app",str(exc))
        return 1

if __name__=="__main__": sys.exit(main())
