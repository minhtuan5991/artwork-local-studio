"""Explicit light surfaces, including dialogs and popups under Windows dark mode."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette

FOREST="#1F6B3A"
INK="#153623"
MUTED="#3F594A"

STYLE = """
QWidget {font-family:'Segoe UI';font-size:13px;color:#153623;}
QMainWindow,QDialog,QMessageBox {background:#F5FBF7;}
QFrame#card {background:white;border:1px solid #CCDFD2;border-radius:12px;}
QFrame#sidebar {background:white;border-right:1px solid #CCDFD2;}
QFrame#sidebar QPushButton {background:transparent;border:0;padding:12px;}
QFrame#sidebar QPushButton:hover {background:#E5F5E9;}
QPushButton {background:white;color:#153623;border:1px solid #BDD4C5;border-radius:7px;padding:6px 12px;min-height:22px;}
QPushButton:hover {background:#E5F5E9;border-color:#6DA880;}
QPushButton:pressed {background:#D1ECD9;}
QPushButton:focus {border:1px solid #1F6B3A;}
QPushButton:disabled {color:#6F8376;background:#F0F8F2;border-color:#D5E6DA;}
QPushButton#primary {background:#1F6B3A;color:white;border:1px solid #1F6B3A;font-weight:600;}
QPushButton#primary:hover {background:#17532F;}
QPushButton#primary:pressed {background:#103F23;}
QPushButton#primary:disabled {background:#D4E8DA;border-color:#D4E8DA;color:#4C6755;}
QLabel#title {font-size:23px;font-weight:700;}
QLabel#muted {color:#3F594A;}
QLabel#section {font-size:12px;font-weight:700;color:#3F594A;}
QLabel#badge {background:#E5F5E9;color:#1F6B3A;border-radius:10px;padding:7px 12px;font-weight:600;}
QLineEdit,QSpinBox,QDoubleSpinBox,QComboBox {background:white;color:#153623;border:1px solid #BDD4C5;border-radius:6px;padding:6px;min-height:22px;selection-background-color:#1F6B3A;selection-color:white;}
QPlainTextEdit {background:white;color:#153623;border:1px solid #BDD4C5;border-radius:6px;padding:6px;selection-background-color:#1F6B3A;selection-color:white;}
QLineEdit:focus,QPlainTextEdit:focus,QComboBox:focus,QSpinBox:focus,QDoubleSpinBox:focus {border:1px solid #1F6B3A;}
QComboBox::drop-down {width:22px;border:0;}
QComboBox QAbstractItemView {background:white;color:#153623;border:1px solid #8BB79A;selection-background-color:#1F6B3A;selection-color:white;outline:0;}
QComboBox QAbstractItemView::item {min-height:28px;padding:4px 8px;}
QTabWidget::pane {background:white;border:1px solid #BDD4C5;border-radius:7px;top:-1px;}
QStackedWidget {background:white;}
QTabBar {background:transparent;}
QTabBar::tab {background:#F2FAF4;color:#345442;border:1px solid #BDD4C5;padding:10px 16px;min-height:18px;border-top-left-radius:6px;border-top-right-radius:6px;margin-right:4px;}
QTabBar::tab:selected {background:white;color:#174D2A;border-bottom-color:white;font-weight:600;}
QTabBar::tab:hover {background:#E5F5E9;color:#153623;}
QCheckBox {color:#153623;spacing:8px;}
QTableView {background:white;alternate-background-color:#F4FBF6;border:0;gridline-color:#DFEEE4;selection-background-color:#E0F2E6;selection-color:#153623;}
QHeaderView::section {background:#ECF7EF;border:0;border-bottom:1px solid #CCDFD2;padding:9px;font-weight:600;color:#345442;}
QProgressBar {border:0;background:#E1F0E6;border-radius:4px;text-align:center;min-height:8px;max-height:8px;}
QProgressBar::chunk {background:#1F6B3A;border-radius:4px;}
QSplitter::handle {background:transparent;}
QMenu {background:white;color:#153623;border:1px solid #BDD4C5;padding:5px;}
QMenu::item {padding:8px 18px;} QMenu::item:selected {background:#1F6B3A;color:white;}
QToolTip {background:#153623;color:white;padding:7px;border:0;}
"""


def apply_theme(app):
    app.setStyle("Fusion")
    app.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs,True)
    app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    palette=QPalette()
    colors={
        QPalette.ColorRole.Window:"#F5FBF7", QPalette.ColorRole.WindowText:INK,
        QPalette.ColorRole.Base:"#FFFFFF", QPalette.ColorRole.AlternateBase:"#F4FBF6",
        QPalette.ColorRole.Text:INK, QPalette.ColorRole.Button:"#FFFFFF",
        QPalette.ColorRole.ButtonText:INK, QPalette.ColorRole.Highlight:FOREST,
        QPalette.ColorRole.HighlightedText:"#FFFFFF", QPalette.ColorRole.PlaceholderText:"#587060",
        QPalette.ColorRole.ToolTipBase:INK, QPalette.ColorRole.ToolTipText:"#FFFFFF",
        QPalette.ColorRole.Link:FOREST, QPalette.ColorRole.LinkVisited:"#17532F",
        QPalette.ColorRole.Light:"#FFFFFF", QPalette.ColorRole.Midlight:"#F4FBF6",
        QPalette.ColorRole.Mid:"#A6C2B0", QPalette.ColorRole.Dark:"#557862",
        QPalette.ColorRole.Shadow:"#345442",
    }
    for role,value in colors.items():
        palette.setColor(role,QColor(value))
    for role in [QPalette.ColorRole.WindowText,QPalette.ColorRole.Text,QPalette.ColorRole.ButtonText]:
        palette.setColor(QPalette.ColorGroup.Disabled,role,QColor("#6F8376"))
    app.setPalette(palette)
    app.setStyleSheet(STYLE)
