from __future__ import annotations
import json
import math
import os
import threading
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw
from PySide6.QtCore import Qt, Signal, QObject, QPointF, QRectF, QTimer, QAbstractTableModel, QModelIndex, QUrl, QSize
from PySide6.QtGui import QColor, QPainter, QPen, QImage, QPolygonF, QPainterPath, QDesktopServices, QKeySequence, QShortcut, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QPlainTextEdit, QSpinBox, QFormLayout, QFileDialog,
    QMessageBox, QSplitter, QTableView, QAbstractItemView, QProgressBar, QCheckBox,
    QDialog, QDialogButtonBox, QTabWidget, QHeaderView, QFrame, QGridLayout, QDoubleSpinBox, QMenu, QSizePolicy)
from .core import JobOptions, Store, Settings, STATUS_LABELS, ACTIVE, normalized_image, export_png
from .engine import QueueRunner, readiness
from .hardware import hardware_summary
from .image_ops import rotate_input, rotated_size
from . import __version__

STYLE = """
QWidget {font-family:'Segoe UI';font-size:13px;color:#1D2235;}
QMainWindow {background:#F3F4F8;}
QFrame#card {background:white;border:1px solid #E2E5EF;border-radius:12px;}
QFrame#sidebar {background:white;border-right:1px solid #E2E5EF;}
QFrame#sidebar QPushButton {background:transparent;border:0;padding:12px;}
QFrame#sidebar QPushButton:hover {background:#EDE8FF;}
QPushButton {background:#F6F7FB;border:1px solid #E2E5EF;border-radius:7px;padding:6px 12px;min-height:22px;}
QPushButton:hover {background:#EDE8FF;border-color:#C5B8FF;}
QPushButton:focus {border:1px solid #6D4AFF;}
QPushButton:disabled {color:#959BAB;background:#F6F7FB;}
QPushButton#primary {background:#6D4AFF;color:white;border:1px solid #6D4AFF;font-weight:600;}
QPushButton#primary:hover {background:#5937E6;}
QLabel#title {font-size:23px;font-weight:700;}
QLabel#muted {color:#626B80;}
QLabel#section {font-size:12px;font-weight:700;color:#626B80;}
QLabel#badge {background:#EDE8FF;color:#5937E6;border-radius:10px;padding:7px 12px;font-weight:600;}
QLineEdit,QSpinBox,QDoubleSpinBox,QComboBox {background:white;border:1px solid #D9DEEA;border-radius:6px;padding:6px;min-height:22px;}
QPlainTextEdit {background:white;border:1px solid #D9DEEA;border-radius:6px;padding:6px;}
QLineEdit:focus,QPlainTextEdit:focus,QComboBox:focus,QSpinBox:focus,QDoubleSpinBox:focus {border:1px solid #6D4AFF;}
QComboBox::drop-down {width:22px;border:0;}
QTableView {background:white;alternate-background-color:#F8F9FC;border:0;gridline-color:#EEF0F6;selection-background-color:#EDE8FF;selection-color:#392385;}
QHeaderView::section {background:#F8F9FC;border:0;border-bottom:1px solid #E2E5EF;padding:9px;font-weight:600;color:#626B80;}
QProgressBar {border:0;background:#EDEEF5;border-radius:4px;text-align:center;min-height:8px;max-height:8px;}
QProgressBar::chunk {background:#6D4AFF;border-radius:4px;}
QSplitter::handle {background:transparent;}
QMenu {background:white;border:1px solid #E2E5EF;padding:5px;}
QMenu::item {padding:8px 18px;} QMenu::item:selected {background:#EDE8FF;}
QToolTip {background:#1D2235;color:white;padding:7px;border:0;}
"""

def button(text, callback, primary=False):
    item=QPushButton(text)
    if primary: item.setObjectName("primary")
    item.clicked.connect(callback)
    return item

def muted(text):
    item=QLabel(text); item.setObjectName("muted"); item.setWordWrap(True)
    return item

def card():
    item=QFrame(); item.setObjectName("card"); return item

def combo(items):
    widget=QComboBox()
    for label,value in items: widget.addItem(label,value)
    return widget

class Bus(QObject):
    event=Signal(str,str)
    imported=Signal(object)
    setup=Signal(str,int)
    setup_done=Signal(str)
    update_done=Signal(object)

class ImageCanvas(QWidget):
    dropped=Signal(object)
    angle_changed=Signal(float)
    def __init__(self, editable=False):
        super().__init__()
        self.editable=editable; self.path=None; self.image=QImage(); self.original=(1,1)
        self.points=[]; self.mode="view"; self.zoom=1.; self.pan=QPointF(); self.bg="checker"
        self.dragging=False; self.panning=False; self.last=QPointF()
        self.angle=0.; self.base_original=(1,1); self.base_thumb=None
        self.setMinimumSize(160,140); self.setAcceptDrops(editable)
        self.setToolTip("Cuộn: zoom · Giữ Alt hoặc chuột giữa: pan · Rectangle/Lasso: chọn artwork")
    def load(self,path):
        self.path=Path(path) if path else None; self.points=[]; self.zoom=1; self.pan=QPointF()
        self.image=QImage(); self.angle=0.; self.base_thumb=None
        if self.path and self.path.is_file():
            with Image.open(self.path) as im:
                self.original=im.size; self.base_original=im.size
                thumb=im.convert("RGBA"); thumb.thumbnail((1600,1600))
                self.base_thumb=thumb.copy()
                self.set_angle(0)
        self.angle_changed.emit(0.)
        self.update()
    def set_angle(self,value):
        if self.base_thumb is None: return
        self.angle=float(value)
        self.original=rotated_size(self.base_original,self.angle)
        thumb=rotate_input(self.base_thumb,self.angle); raw=thumb.tobytes()
        self.image=QImage(raw,thumb.width,thumb.height,thumb.width*4,QImage.Format.Format_RGBA8888).copy()
        self.points=[]; self.zoom=1; self.pan=QPointF()
        self.angle_changed.emit(self.angle); self.update()
    def image_rect(self):
        if self.image.isNull(): return QRectF()
        fit=min((self.width()-24)/self.original[0],(self.height()-24)/self.original[1])*self.zoom
        w,h=self.original[0]*fit,self.original[1]*fit
        return QRectF((self.width()-w)/2+self.pan.x(),(self.height()-h)/2+self.pan.y(),w,h)
    def source_point(self,point):
        rect=self.image_rect()
        return QPointF(max(0,min(self.original[0],(point.x()-rect.x())/rect.width()*self.original[0])),
                      max(0,min(self.original[1],(point.y()-rect.y())/rect.height()*self.original[1])))
    def screen_point(self,point):
        rect=self.image_rect()
        return QPointF(rect.x()+point.x()/self.original[0]*rect.width(),rect.y()+point.y()/self.original[1]*rect.height())
    def paintEvent(self,event):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(),QColor("#F4F5F9" if self.bg!="dark" else "#222635"))
        if self.bg=="checker":
            for y in range(0,self.height(),16):
                for x in range(0,self.width(),16):
                    if (x//16+y//16)%2: painter.fillRect(x,y,16,16,QColor("#E5E7EE"))
        if self.image.isNull():
            painter.setPen(QColor("#626B80" if self.bg!="dark" else "#B1B8CC"))
            painter.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,
                "Kéo ảnh vào đây\nhoặc Chọn ảnh / Ctrl+V" if self.editable else "Kết quả RGBA\nhiển thị sau khi xử lý")
            return
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(self.image_rect(),self.image)
        if len(self.points)>=2:
            points=[self.screen_point(p) for p in self.points]
            path=QPainterPath()
            if self.mode=="rectangle" and len(points)==2:
                path.addRect(QRectF(points[0],points[1]).normalized())
            else: path.addPolygon(QPolygonF(points)); path.closeSubpath()
            shade=QPainterPath(); shade.addRect(self.image_rect())
            painter.fillPath(shade.subtracted(path),QColor(13,38,23,90))
            painter.setPen(QPen(QColor("#8E76FF"),2)); painter.drawPath(path)
        if self.editable and self.angle:
            painter.setPen(QPen(QColor(255,255,255,65),1))
            for fraction in (1/3,2/3):
                painter.drawLine(QPointF(self.width()*fraction,0),QPointF(self.width()*fraction,self.height()))
                painter.drawLine(QPointF(0,self.height()*fraction),QPointF(self.width(),self.height()*fraction))
    def mousePressEvent(self,event):
        if self.image.isNull(): return
        self.last=event.position()
        self.panning=event.button()==Qt.MouseButton.MiddleButton or bool(event.modifiers()&Qt.KeyboardModifier.AltModifier)
        if self.panning: return
        if self.editable and self.mode!="view" and event.button()==Qt.MouseButton.LeftButton:
            self.dragging=True; point=self.source_point(event.position())
            self.points=[point,point] if self.mode=="rectangle" else [point]
            self.update()
    def mouseMoveEvent(self,event):
        if self.panning:
            self.pan+=event.position()-self.last; self.last=event.position(); self.update()
        elif self.dragging:
            point=self.source_point(event.position())
            if self.mode=="rectangle": self.points[1]=point
            elif len(self.points)<10000: self.points.append(point)
            self.update()
    def mouseReleaseEvent(self,event):
        self.dragging=False; self.panning=False; self.update()
    def wheelEvent(self,event):
        self.zoom=max(.5,min(8,self.zoom*(1.15 if event.angleDelta().y()>0 else 1/1.15))); self.update()
    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
    def dropEvent(self,event):
        paths=[Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        if paths: self.dropped.emit(paths)
    def crop_to(self,target):
        image=rotate_input(normalized_image(self.path),self.angle)
        if len(self.points)>=2:
            xy=[(p.x(),p.y()) for p in self.points]
            box=(max(0,math.floor(min(p[0] for p in xy))),max(0,math.floor(min(p[1] for p in xy))),
                 min(image.width,math.ceil(max(p[0] for p in xy))),min(image.height,math.ceil(max(p[1] for p in xy))))
            if min(box[2]-box[0],box[3]-box[1])<16: raise ValueError("Vùng chọn cần ít nhất 16 pixel mỗi chiều.")
            if self.mode=="lasso":
                if len(xy)<3: raise ValueError("Lasso cần ít nhất ba điểm.")
                mask=Image.new("L",image.size,0); ImageDraw.Draw(mask).polygon(xy,fill=255)
                image.putalpha(ImageChops.multiply(image.getchannel("A"),mask))
            image=image.crop(box)
        image.save(target,"PNG")

class QueueModel(QAbstractTableModel):
    headers=["Ảnh nguồn","Trạng thái","Kích thước","Nền","Thời gian","QC nội dung"]
    def __init__(self): super().__init__(); self.jobs=[]
    def rowCount(self,parent=QModelIndex()): return 0 if parent.isValid() else len(self.jobs)
    def columnCount(self,parent=QModelIndex()): return 6
    def headerData(self,section,orientation,role):
        if role==Qt.ItemDataRole.DisplayRole and orientation==Qt.Orientation.Horizontal: return self.headers[section]
    def data(self,index,role):
        if not index.isValid(): return None
        job=self.jobs[index.row()]; options=json.loads(job["options"])
        if role==Qt.ItemDataRole.DisplayRole:
            return [job["name"],STATUS_LABELS.get(job["status"],job["status"]),f'{options["size"]} × {options["size"]}',
                {"transparent":"Trong suốt","white":"Trắng","chroma":"Chroma"}[options["background"]],
                f'{job["elapsed"]:.0f}s' if job["elapsed"] else "—",
                {"pending":"Chưa duyệt","passed":"Đã duyệt","failed":"Cần sửa"}.get(json.loads(job["metadata"]).get("quality_review","pending"),"Chưa duyệt")][index.column()]
        if role==Qt.ItemDataRole.ToolTipRole: return job["error"] or job["message"] or job["source_url"]
        if role==Qt.ItemDataRole.ForegroundRole and index.column()==1:
            return QColor("#B25137" if job["status"] in {"failed","save_failed","needs_review"} else "#215D46")
    def replace(self,jobs): self.beginResetModel(); self.jobs=jobs; self.endResetModel()

class MainWindow(QMainWindow):
    def __init__(self,settings: Settings,manifest):
        super().__init__()
        self.settings=settings; self.manifest=manifest; self.store=Store(settings.data); self.store.recover()
        for stale in self.store.inbox.glob("*.processing"):
            stale.rename(stale.with_suffix(".json"))
        self.bus=Bus(); self.runner=None; self.setup_running=False; self.setup_cancel=threading.Event()
        self.source_name="artwork.png"; self.preview_id=None; self.import_count=0
        self.bus.event.connect(self.worker_event); self.bus.imported.connect(self.import_done)
        self.bus.setup.connect(self.setup_progress); self.bus.setup_done.connect(self.setup_done)
        self.setWindowTitle("Artwork Local Studio · Qwen-Image-2.1")
        self.setWindowIcon(QIcon(str(settings.root/"assets"/"app.ico")))
        self.resize(1480,900); self.setMinimumSize(1180,760)
        root=QWidget(); self.setCentralWidget(root)
        layout=QHBoxLayout(root); layout.setContentsMargins(0,0,0,0); layout.setSpacing(0)
        sidebar=QFrame(); sidebar.setObjectName("sidebar"); sidebar.setFixedWidth(80)
        side=QVBoxLayout(sidebar); side.setContentsMargins(12,20,12,16); side.setSpacing(14)
        logo=QLabel(); logo.setPixmap(QPixmap(str(settings.root/"assets"/"logo-128.png")).scaled(48,48,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter); logo.setToolTip("Artwork Local Studio"); side.addWidget(logo); side.addSpacing(24)
        for icon,tip,callback in [("workspace","Không gian làm việc",lambda:None),("settings","Cài đặt",self.open_settings),
                ("web","Nhận ảnh website",lambda:self.open_settings(1)),("folder","Thư mục kết quả",self.open_output)]:
            item=button("",callback); item.setIcon(QIcon(str(settings.root/"assets"/"icons"/(icon+".svg"))))
            item.setIconSize(QSize(24,24)); item.setToolTip(tip); item.setAccessibleName(tip); item.setMinimumHeight(44); side.addWidget(item)
        side.addStretch()
        version=muted("v"+__version__); version.setAlignment(Qt.AlignmentFlag.AlignCenter); side.addWidget(version)
        layout.addWidget(sidebar)
        main=QVBoxLayout(); main.setContentsMargins(20,18,20,14); main.setSpacing(14); layout.addLayout(main,1)
        header=QHBoxLayout(); headline=QVBoxLayout(); headline.setSpacing(3)
        title=QLabel("Artwork Local Studio"); title.setObjectName("title"); headline.addWidget(title)
        subtitle=muted("Tách artwork • Khôi phục chi tiết • Xuất PNG"); subtitle.setWordWrap(False)
        headline.addWidget(subtitle); header.addLayout(headline); header.addStretch()
        badge=QLabel("QWEN 2.1  /  LOCAL"); badge.setObjectName("badge"); header.addWidget(badge); main.addLayout(header)
        self.hardware=muted(hardware_summary()); main.addWidget(self.hardware)
        split=QSplitter(Qt.Orientation.Horizontal); split.setChildrenCollapsible(False); split.setHandleWidth(14); main.addWidget(split,1)
        left=QWidget(); leftbox=QVBoxLayout(left); leftbox.setContentsMargins(0,0,0,0); leftbox.setSpacing(14)
        editor=card(); edit=QVBoxLayout(editor); edit.setContentsMargins(16,12,16,12); edit.setSpacing(8)
        tools=QHBoxLayout(); tools.setSpacing(8)
        tools.addWidget(button("Chọn ảnh",self.choose_files)); tools.addWidget(button("Dán ảnh",self.paste))
        self.mode=combo([("Xem / pan","view"),("Rectangle","rectangle"),("Lasso","lasso")]); self.mode.currentIndexChanged.connect(self.change_mode)
        tools.addWidget(self.mode); tools.addWidget(button("Bỏ vùng chọn",self.clear_crop)); tools.addStretch(); edit.addLayout(tools)
        self.source=ImageCanvas(True); self.result=ImageCanvas(); self.source.dropped.connect(self.receive_files)
        rotation=QHBoxLayout(); rotation.setSpacing(8); rotation.addWidget(muted("Xoay nguồn"))
        rotation.addWidget(button("−90°",lambda:self.source.set_angle((self.source.angle-90+180)%360-180)))
        self.angle=QDoubleSpinBox(); self.angle.setRange(-180,180); self.angle.setDecimals(1); self.angle.setSingleStep(.1); self.angle.setSuffix("°"); self.angle.setFixedWidth(96)
        self.angle.setToolTip("Góc dương xoay theo chiều kim đồng hồ. Xoay trước khi khoanh vùng.")
        self.angle.valueChanged.connect(self.source.set_angle); self.source.angle_changed.connect(self.sync_angle)
        rotation.addWidget(self.angle); rotation.addWidget(button("+90°",lambda:self.source.set_angle((self.source.angle+90+180)%360-180)))
        rotation.addWidget(button("Đặt lại",lambda:self.source.set_angle(0))); rotation.addStretch()
        edit.addLayout(rotation)
        previews=QHBoxLayout(); previews.setSpacing(10)
        for caption,canvas in [("01   ẢNH NGUỒN",self.source),("02   KẾT QUẢ RGBA",self.result)]:
            col=QVBoxLayout(); label=QLabel(caption); label.setObjectName("section"); col.addWidget(label); col.addWidget(canvas,1); previews.addLayout(col,1)
        edit.addLayout(previews,1)
        self.source_status=muted("Chọn ảnh → Xoay thẳng → Khoanh vùng."); self.source_status.setMaximumHeight(36)
        bgline=QHBoxLayout(); bgline.addWidget(muted("Nền xem trước"))
        bg=combo([("Ô caro","checker"),("Sáng","light"),("Tối","dark")]); bg.currentIndexChanged.connect(lambda:self.preview_background(bg.currentData()))
        bgline.addWidget(bg); bgline.addWidget(button("Reset zoom",self.reset_zoom)); bgline.addWidget(self.source_status,1); edit.addLayout(bgline)
        leftbox.addWidget(editor,1)
        options=card(); formbox=QVBoxLayout(options); formbox.setContentsMargins(16,14,16,14); formbox.setSpacing(10)
        caption=QLabel("THIẾT LẬP ĐẦU RA"); caption.setObjectName("section"); formbox.addWidget(caption)
        fields=QGridLayout(); fields.setHorizontalSpacing(10); fields.setVerticalSpacing(5)
        self.size=combo([("1K · 1024",1024),("2K · 2048",2048)])
        self.background=combo([("Trong suốt","transparent"),("Trắng","white"),("Chroma","chroma")])
        self.chroma=QLineEdit("#00FF00"); self.chroma.setMaxLength(7)
        self.detail=combo([("Giữ thiết kế","preserve"),("Khôi phục","restore")])
        self.steps=QSpinBox(); self.steps.setRange(5,80); self.steps.setValue(20); self.seed=QLineEdit("42")
        for col,(label,widget) in enumerate([("Kích thước",self.size),("Nền",self.background),("Chroma",self.chroma),("Chi tiết",self.detail),("Số bước",self.steps),("Seed",self.seed)]):
            fields.addWidget(muted(label),0,col); fields.addWidget(widget,1,col); fields.setColumnStretch(col,1)
            widget.setMinimumWidth(0); widget.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed)
        formbox.addLayout(fields)
        texts=QHBoxLayout(); texts.setSpacing(10)
        self.exact=QPlainTextEdit(); self.exact.setPlaceholderText("Chữ chính xác trong artwork (tùy chọn)")
        self.prompt=QPlainTextEdit(); self.prompt.setPlaceholderText("Yêu cầu sửa thêm (tùy chọn)")
        for label,field in [("Chữ xác nhận",self.exact),("Yêu cầu sửa thêm",self.prompt)]:
            column=QVBoxLayout(); column.setSpacing(4); caption=muted(label); column.addWidget(caption)
            field.setAccessibleName(label); field.setFixedHeight(58); column.addWidget(field); texts.addLayout(column,1)
        formbox.addLayout(texts)
        outputrow=QHBoxLayout(); self.output_label=QLabel(); self.output_label.setObjectName("muted"); self.output_label.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        outputrow.addWidget(self.output_label,1); outputrow.addWidget(button("Thư mục lưu",self.choose_output))
        outputrow.addWidget(button("Thêm vào Queue",self.add_current,True)); formbox.addLayout(outputrow)
        leftbox.addWidget(options); split.addWidget(left)
        queuecard=card(); queuecard.setMinimumWidth(340); queuecard.setMaximumWidth(520); q=QVBoxLayout(queuecard); q.setContentsMargins(16,16,16,16); q.setSpacing(12)
        self.count_label=QLabel("QUEUE"); self.count_label.setObjectName("section"); q.addWidget(self.count_label)
        controls=QHBoxLayout(); self.run_button=button("Chạy Queue",lambda:self.start_queue(),True); controls.addWidget(self.run_button,1)
        controls.addWidget(button("Chạy đã chọn",lambda:self.start_queue(self.selected_ids())),1); q.addLayout(controls)
        pause=QHBoxLayout(); pause.addWidget(button("Dừng sau ảnh này",self.pause_queue),1); pause.addWidget(button("Hủy ảnh",self.cancel_job),1); q.addLayout(pause)
        self.progress=QProgressBar(); self.progress.setRange(0,100); self.progress.setValue(0); self.progress.setTextVisible(False); q.addWidget(self.progress)
        self.filter=combo([("Tất cả ảnh","all"),("Đang chờ","queued"),("Đã lưu","completed"),("Lỗi / gián đoạn","errors")]); self.filter.currentIndexChanged.connect(self.refresh); q.addWidget(self.filter)
        self.model=QueueModel(); self.table=QTableView(); self.table.setModel(self.model); self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setShowGrid(False); self.table.verticalHeader().hide(); self.table.verticalHeader().setDefaultSectionSize(54)
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch); self.table.setColumnWidth(1,120)
        for column in [2,3,4,5]: self.table.setColumnHidden(column,True)
        self.table.selectionModel().selectionChanged.connect(self.selection_changed); q.addWidget(self.table,1)
        self.queue_info=muted("Chọn ảnh trong Queue để xem nguồn và kết quả."); q.addWidget(self.queue_info)
        actions=QHBoxLayout(); actions.addWidget(button("Duyệt QC",self.review_selected),1); actions.addWidget(button("Nhật ký",self.show_logs),1)
        more=QPushButton("Thao tác"); menu=QMenu(more)
        for label,callback in [("Thử lại / lưu tiếp",self.retry_selected),("Chạy lại AI",lambda:self.retry_selected(True)),("Xuất nền đang chọn",self.export_selected),
                ("Di chuyển lên",lambda:self.move_selected(-1)),("Di chuyển xuống",lambda:self.move_selected(1)),("Ẩn khỏi Queue",self.hide_selected)]:
            action=menu.addAction(label); action.triggered.connect(lambda checked=False,fn=callback:fn())
        more.setMenu(menu); actions.addWidget(more,1); q.addLayout(actions); split.addWidget(queuecard); split.setSizes([960,380]); split.setStretchFactor(0,1)
        footer=QHBoxLayout(); self.status=muted(""); footer.addWidget(self.status,1)
        self.update_button=button("Kiểm tra cập nhật",lambda:self.check_updates(True)); footer.addWidget(self.update_button)
        self.setup_button=button("Thiết lập Qwen",self.install_models); footer.addWidget(self.setup_button); main.addLayout(footer)
        self.update_busy=False; self.bus.update_done.connect(self.updates_received)
        QShortcut(QKeySequence("Ctrl+O"),self,activated=self.choose_files); QShortcut(QKeySequence("Ctrl+V"),self,activated=self.paste)
        self.load_defaults(); self.refresh(); self.update_readiness()
        self.timer=QTimer(self); self.timer.timeout.connect(self.scan_inbox); self.timer.start(1500)
        if self.settings.values.get("check_updates",True): QTimer.singleShot(1800,self.check_updates)

    def load_defaults(self):
        data=self.settings.values["defaults"]
        for widget,key in [(self.size,"size"),(self.background,"background"),(self.detail,"detail")]:
            idx=widget.findData(data.get(key)); widget.setCurrentIndex(max(0,idx))
        self.chroma.setText(data.get("chroma","#00FF00")); self.steps.setValue(data.get("steps",20))
        self.seed.setText(str(data.get("seed",42))); self.exact.setPlainText(data.get("exact_text","")); self.prompt.setPlainText(data.get("manual_prompt",""))
        self.show_output_path()
    def show_output_path(self):
        path=self.settings.values["output_dir"]
        self.output_label.setToolTip(path)
        self.output_label.setText("Lưu: "+path)
    def sync_angle(self,value):
        self.angle.blockSignals(True); self.angle.setValue(value); self.angle.blockSignals(False)
    def check_updates(self,manual=False):
        if self.update_busy: return
        if getattr(self,"latest_release",None):
            self.show_update(); return
        self.update_busy=True; self.update_button.setEnabled(False)
        def work():
            from .updates import check_latest
            result=check_latest(__version__); result["manual"]=manual
            self.bus.update_done.emit(result)
        threading.Thread(target=work,daemon=True).start()
    def updates_received(self,result):
        self.update_busy=False; self.update_button.setEnabled(True)
        if result["state"]=="available":
            self.latest_release=result
            self.update_button.setText("Có bản "+result["version"]); self.update_button.setObjectName("primary")
            self.update_button.style().unpolish(self.update_button); self.update_button.style().polish(self.update_button)
            if result.get("manual"): self.show_update()
        elif result.get("manual"):
            messages={"current":"Bạn đang dùng bản mới nhất: "+__version__,"unpublished":"Chưa có release công khai. Hãy kiểm tra lại sau.",
                      "error":result.get("message","Không kiểm tra được cập nhật.")}
            QMessageBox.information(self,"Cập nhật ứng dụng",messages[result["state"]])
    def show_update(self):
        from .updates import RELEASES_URL
        result=getattr(self,"latest_release",None)
        if not result: QDesktopServices.openUrl(QUrl(RELEASES_URL)); return
        dialog=QDialog(self); dialog.setWindowTitle("Có phiên bản "+result["version"]); dialog.resize(620,420)
        box=QVBoxLayout(dialog); box.addWidget(QLabel("Bản đang dùng: "+__version__+"  →  "+result["version"]))
        text=QPlainTextEdit(); text.setReadOnly(True); text.setPlainText(result["notes"]); box.addWidget(text,1)
        box.addWidget(muted("Tải bộ cài từ GitHub Releases. Hoàn tất Queue và đóng app trước khi cài bản mới. Queue, cài đặt và model vẫn được giữ."))
        box.addWidget(button("Mở trang tải bộ cài",lambda:QDesktopServices.openUrl(QUrl(result["url"])),True))
        box.addWidget(button("Đóng",dialog.accept)); dialog.exec()
    def current_options(self):
        return JobOptions.from_dict(dict(size=self.size.currentData(),background=self.background.currentData(),chroma=self.chroma.text().strip(),
            detail=self.detail.currentData(),steps=self.steps.value(),seed=int(self.seed.text()),exact_text=self.exact.toPlainText(),manual_prompt=self.prompt.toPlainText()))
    def error(self,message): QMessageBox.warning(self,"Artwork Local Studio",str(message)[:7000])
    def choose_files(self):
        paths,_=QFileDialog.getOpenFileNames(self,"Chọn ảnh nguồn","","Ảnh (*.png *.jpg *.jpeg *.webp)")
        if paths: self.receive_files([Path(p) for p in paths])
    def receive_files(self,paths):
        try:
            opts=self.current_options()
        except Exception as exc: self.error(exc); return
        self.import_files(paths,opts, preview_only=len(paths)==1)
    def paste(self):
        mime=QApplication.clipboard().mimeData()
        if mime.hasUrls():
            self.receive_files([Path(u.toLocalFile()) for u in mime.urls() if u.isLocalFile()]); return
        image=QApplication.clipboard().image()
        if image.isNull(): self.error("Clipboard chưa có ảnh. Có thể dùng Copy image trong trình duyệt."); return
        path=self.settings.data/("clipboard-"+uuid.uuid4().hex+".png")
        image.save(str(path)); self.receive_files([path])
    def import_files(self,paths,options,metadata=None,preview_only=False,name=None,spool=None):
        self.import_count+=1; self.status.setText("Đang nhập ảnh…")
        output=self.settings.values["output_dir"]
        def work():
            prepared=[]; errors=[]
            for path in paths:
                try:
                    item=self.store.prepare(Path(path))
                    if name: item["name"]=name
                    prepared.append(item)
                except Exception as exc: errors.append(f"{Path(path).name}: {exc}")
            self.bus.imported.emit(dict(prepared=prepared,errors=errors,options=options,metadata=metadata or {},
                preview=preview_only,output=output,spool=spool))
        threading.Thread(target=work,daemon=True).start()
    def import_done(self,payload):
        self.import_count-=1
        added=duplicates=0
        for item in payload["prepared"]:
            if payload["preview"]:
                self.table.clearSelection(); self.preview_id=None
                self.source.load(item["source_path"]); self.source_name=item["name"]
                self.source_status.setText(f'{item["name"]} · {self.source.original[0]} × {self.source.original[1]}'); continue
            result=self.store.enqueue(item,payload["options"],payload["output"],payload["metadata"])
            if result.get("duplicate")=="exact":
                self.store.update(result["job"]["id"],visible=1)
            if result.get("duplicate")=="similar":
                answer=QMessageBox.question(self,"Ảnh gần giống",f'{item["name"]}\ngần giống {result["job"]["name"]}.\nVẫn thêm ảnh này?',
                    QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
                if answer==QMessageBox.StandardButton.Yes:
                    result=self.store.enqueue(item,payload["options"],payload["output"],payload["metadata"],accept_similar=True)
            if result.get("job_id"): added+=1
            else: duplicates+=1
        if payload["spool"]:
            path=Path(payload["spool"])
            path.rename(path.with_suffix(".received" if payload["prepared"] else ".rejected"))
        self.refresh()
        self.status.setText(f"Đã thêm {added} ảnh · bỏ qua {duplicates} ảnh trùng." if not payload["preview"] else "Ảnh nguồn đã sẵn sàng. Chọn vùng và thêm vào Queue.")
        if payload["errors"]: self.error("\n".join(payload["errors"]))
    def add_current(self):
        if not self.source.path: self.error("Chọn ảnh nguồn trước."); return
        try:
            options=self.current_options()
            path=self.settings.data/("crop-"+uuid.uuid4().hex+".png")
            self.source.crop_to(path)
            self.settings.values["defaults"]=asdict(options); self.settings.save()
            self.import_files([path],options,name=self.source_name,metadata={"source_rotation_degrees":self.source.angle})
        except Exception as exc: self.error(exc)
    def change_mode(self):
        if hasattr(self,"source"): self.source.mode=self.mode.currentData(); self.source.points=[]; self.source.update()
    def clear_crop(self): self.source.points=[]; self.source.update()
    def reset_zoom(self):
        for canvas in [self.source,self.result]: canvas.zoom=1; canvas.pan=QPointF(); canvas.update()
    def preview_background(self,value):
        for canvas in [self.source,self.result]: canvas.bg=value; canvas.update()
    def selected_ids(self):
        return [self.model.jobs[i.row()]["id"] for i in self.table.selectionModel().selectedRows()]
    def refresh(self,*args):
        selected=set(self.selected_ids()); rows=self.store.all(10000); choice=self.filter.currentData()
        total=len(rows); waiting=sum(j["status"]=="queued" for j in rows)
        self.count_label.setText(f"QUEUE   {waiting} chờ / {total} ảnh")
        if choice!="all": rows=[j for j in rows if j["status"]==choice or choice=="errors" and j["status"] in {"failed","save_failed","needs_review","interrupted","canceled"}]
        selection=self.table.selectionModel(); selection.blockSignals(True)
        self.model.replace(rows)
        from PySide6.QtCore import QItemSelectionModel
        for i,job in enumerate(rows):
            if job["id"] in selected: selection.select(self.model.index(i,0),QItemSelectionModel.SelectionFlag.Select|QItemSelectionModel.SelectionFlag.Rows)
        selection.blockSignals(False)
        active=next((j for j in rows if j["status"] in ACTIVE),None)
        if active: self.progress.setValue(active["progress"]); self.status.setText(active["message"])
        elif not self.runner or not self.runner.is_alive(): self.progress.setValue(0)
        self.selection_changed()
    def selection_changed(self,*args):
        ids=self.selected_ids()
        if len(ids)!=1: return
        job=self.store.get(ids[0]); key=(job["id"],job["master_path"])
        if self.preview_id==key: return
        if not self.preview_id or self.preview_id[0]!=key[0]:
            self.source_name=job["name"]; self.source.load(job["source_path"])
        self.preview_id=key
        self.result.load(job["master_path"] or None); self.source_status.setText(job["name"]+" · "+(job["message"] or STATUS_LABELS[job["status"]]))
        opts=json.loads(job["options"]); meta=json.loads(job["metadata"])
        self.queue_info.setText(str(opts["size"])+" px · "+{"transparent":"Trong suốt","white":"Trắng","chroma":"Chroma"}[opts["background"]]+
            " · "+str(round(job["elapsed"]))+"s\nQC: "+{"pending":"Chưa duyệt","passed":"Đã duyệt","failed":"Cần sửa"}.get(meta.get("quality_review","pending"),"Chưa duyệt"))
    def start_queue(self,ids=None):
        if self.runner and self.runner.is_alive(): self.status.setText("Queue đang chạy."); return
        if self.setup_running: self.error("Đợi tải model hoàn tất."); return
        if ids is not None and not ids: self.error("Chọn ảnh trong Queue."); return
        pending=[j for j in self.store.all(10000) if j["status"]=="queued" and (ids is None or j["id"] in ids)]
        if not pending: self.error("Chưa có ảnh đang chờ."); return
        if any(not j["master_path"] for j in pending):
            problems=readiness(self.settings.values,self.manifest)
            if problems: self.error("\n".join(problems)); return
        self.runner=QueueRunner(self.store,self.settings.values,self.manifest,self.bus.event.emit,ids)
        self.run_button.setEnabled(False); self.runner.start()
    def worker_event(self,kind,job_id):
        self.refresh()
        if kind=="finished": self.run_button.setEnabled(True); self.status.setText("Queue đã dừng. Kết quả và nhật ký được giữ trên máy.")
    def pause_queue(self):
        if self.runner: self.runner.stop_after.set(); self.status.setText("Sẽ dừng khi ảnh hiện tại hoàn tất.")
    def cancel_job(self):
        if self.runner: self.runner.cancel_current.set()
    def retry_selected(self,rerun=False):
        for job_id in self.selected_ids():
            job=self.store.get(job_id)
            if job["status"]=="save_failed": self.store.update(job_id,output_dir=self.settings.values["output_dir"])
            self.store.retry(job_id,rerun=rerun)
        self.refresh()
    def hide_selected(self): self.store.hide(self.selected_ids()); self.refresh()
    def move_selected(self,direction):
        ids=self.selected_ids()
        if len(ids)==1: self.store.move(ids[0],direction); self.refresh()
    def export_selected(self):
        try:
            opts=self.current_options()
            paths=[]
            for job_id in self.selected_ids():
                job=self.store.get(job_id)
                if job["status"] in ACTIVE: raise ValueError("Đợi ảnh này xử lý xong.")
                if not job["master_path"]: raise ValueError("Ảnh chưa có bản RGBA để xuất.")
                path,_=export_png(Path(job["master_path"]),opts,Path(self.settings.values["output_dir"]),job["name"],metadata=json.loads(job["metadata"]))
                paths.append(str(path))
            if not paths: raise ValueError("Chọn ít nhất một ảnh đã có kết quả.")
            self.status.setText(f"Đã xuất {len(paths)} PNG vào thư mục đã chọn.")
        except Exception as exc: self.error(exc)
    def show_logs(self):
        ids=self.selected_ids()
        if len(ids)!=1: self.error("Chọn một ảnh để xem nhật ký."); return
        job=self.store.get(ids[0]); dialog=QDialog(self); dialog.setWindowTitle("Nhật ký · "+job["name"]); dialog.resize(950,650)
        box=QVBoxLayout(dialog); text=QPlainTextEdit(); text.setReadOnly(True)
        text.setPlainText((job["error"]+"\n\n" if job["error"] else "")+"\n".join(r["message"] for r in self.store.logs(ids[0])))
        box.addWidget(text); box.addWidget(button("Đóng",dialog.accept)); dialog.exec()
    def review_selected(self):
        ids=self.selected_ids()
        if len(ids)!=1: self.error("Chọn một ảnh đã có kết quả để duyệt nội dung."); return
        job=self.store.get(ids[0])
        if not job["master_path"] or job["status"] in ACTIVE: self.error("Đợi có kết quả RGBA trước khi duyệt."); return
        dialog=QDialog(self); dialog.setWindowTitle("QC CLONE · "+job["name"]); dialog.resize(630,430)
        box=QVBoxLayout(dialog)
        box.addWidget(muted("Xem nguồn và kết quả trên nền sáng/tối. Kiểm tra alpha tự động chưa xác nhận các mục bên dưới."))
        checks=[]
        for text in ["Chữ, số, viết hoa và dấu câu khớp nguồn","Đủ chủ thể, bố cục và tỷ lệ thiết kế",
                "Không cắt chữ hoặc chi tiết ở mép ảnh","Không còn áo, sản phẩm, fabric hoặc bóng mockup",
                "Không halo; giữ lỗ âm và nét mảnh đúng","Màu mực và texture/distress có chủ ý được giữ","Không có chi tiết mới hoặc biến dạng ngoài yêu cầu"]:
            check=QCheckBox(text); box.addWidget(check); checks.append(check)
        box.addStretch(); actions=QHBoxLayout()
        def save(passed):
            if passed and not all(check.isChecked() for check in checks):
                self.error("Cần kiểm tra đủ các mục trước khi đánh dấu đạt."); return
            metadata=json.loads(job["metadata"])
            metadata.update(quality_review="passed" if passed else "failed",quality_reviewed_at=time.time(),
                quality_checks={check.text():check.isChecked() for check in checks})
            self.store.update(job["id"],metadata=json.dumps(metadata,ensure_ascii=False)); self.refresh(); dialog.accept()
        actions.addWidget(button("Đánh dấu cần sửa",lambda:save(False)))
        actions.addWidget(button("Xác nhận đạt",lambda:save(True),True)); actions.addWidget(button("Đóng",dialog.reject))
        box.addLayout(actions); dialog.exec()
    def choose_output(self):
        path=QFileDialog.getExistingDirectory(self,"Chọn thư mục lưu PNG",self.settings.values["output_dir"])
        if path: self.settings.values["output_dir"]=path; self.settings.save(); self.show_output_path()
    def open_output(self):
        path=Path(self.settings.values["output_dir"]); path.mkdir(parents=True,exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
    def update_readiness(self):
        problems=readiness(self.settings.values,self.manifest)
        self.status.setText("Qwen local sẵn sàng · Không gửi ảnh tới dịch vụ AI." if not problems else "Chưa đủ runtime/model · Bấm Thiết lập Qwen.")
    def open_settings(self,tab=0):
        if self.runner and self.runner.is_alive() or self.setup_running: self.error("Dừng Queue/tải model trước khi thay đổi cài đặt."); return
        dialog=SettingsDialog(self)
        dialog.tabs.setCurrentIndex(tab if isinstance(tab,int) else 0)
        if dialog.exec(): self.load_defaults(); self.update_readiness()
    def install_models(self):
        if self.setup_running: self.setup_cancel.set(); self.status.setText("Đang dừng tải; dữ liệu tải dở được giữ."); return
        if self.runner and self.runner.is_alive(): self.error("Dừng Queue trước khi tải model."); return
        from .paths import resource_base
        path=QFileDialog.getExistingDirectory(self,"Chọn nơi lưu runtime và model (~12 GB)",str(resource_base(self.settings.root)))
        if not path: return
        self.setup_running=True; self.setup_cancel.clear(); self.setup_button.setText("Dừng tải")
        def work():
            try:
                from .downloads import provision
                base=Path(path)
                def report(name,done,total):
                    self.bus.setup.emit(name,int(done*100/total) if total else 0)
                provision(self.settings.root/"model-manifest.json",base,report,self.setup_cancel)
                self.bus.setup_done.emit(str(base))
            except Exception as exc: self.bus.setup_done.emit("ERROR:"+str(exc))
        threading.Thread(target=work,daemon=True).start()
    def setup_progress(self,name,percent): self.status.setText(name); self.progress.setValue(percent)
    def setup_done(self,value):
        self.setup_running=False; self.setup_button.setText("Thiết lập Qwen"); self.progress.setValue(0)
        if value.startswith("ERROR:"): self.error(value[6:]); self.update_readiness(); return
        base=Path(value); self.settings.values.update(model_dir=str(base/"models"),runtime_exe=str(base/"runtime"/"sd-cli.exe"))
        self.settings.save(); self.update_readiness()
    def scan_inbox(self):
        if self.import_count: return
        for path in list(self.store.inbox.glob("*.json"))[:10]:
            processing=path.with_suffix(".processing")
            try:
                path.rename(processing)
                data=json.loads(processing.read_text(encoding="utf-8"))
                image=self.store.inbox/data["image"]
                if image.parent.resolve()!=self.store.inbox.resolve() or not image.is_file(): raise ValueError("Ảnh inbox không hợp lệ.")
                opts=JobOptions.from_dict({**self.settings.values["defaults"],**data.get("options",{})})
                self.import_files([image],opts,metadata=data,spool=str(processing),name=data.get("name","web-artwork.png"))
            except Exception as exc:
                if processing.exists(): processing.rename(processing.with_suffix(".rejected"))
                self.status.setText("Không nhận được ảnh web: "+str(exc))
    def closeEvent(self,event):
        if self.runner and self.runner.is_alive():
            answer=QMessageBox.question(self,"Đóng ứng dụng","Hủy ảnh đang xử lý và đóng app? Queue vẫn được giữ.",
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
            if answer!=QMessageBox.StandardButton.Yes: event.ignore(); return
            self.runner.stop_after.set(); self.runner.cancel_current.set(); self.runner.join(4)
        if self.import_count: self.error("Đợi nhập ảnh hoàn tất trước khi đóng."); event.ignore(); return
        self.setup_cancel.set(); self.settings.save(); event.accept()

class SettingsDialog(QDialog):
    def __init__(self,window):
        super().__init__(window); self.window=window; self.setWindowTitle("Cài đặt Artwork Local Studio"); self.resize(780,580)
        layout=QVBoxLayout(self); self.tabs=QTabWidget(); layout.addWidget(self.tabs)
        runtime=QWidget(); form=QFormLayout(runtime); config=window.settings.values
        self.models=QLineEdit(config["model_dir"]); self.runtime=QLineEdit(config["runtime_exe"]); self.output=QLineEdit(config["output_dir"])
        for label,widget,directory in [("Thư mục model",self.models,True),("Runtime sd-cli.exe",self.runtime,False),("Thư mục PNG",self.output,True)]:
            row=QHBoxLayout(); row.addWidget(widget)
            def pick(checked=False,w=widget,d=directory):
                path=QFileDialog.getExistingDirectory(self,"Chọn thư mục",w.text()) if d else QFileDialog.getOpenFileName(self,"Chọn runtime",w.text(),"Runtime (*.exe)")[0]
                if path: w.setText(path)
            row.addWidget(button("Chọn",pick)); form.addRow(label,row)
        self.device=combo([("NVIDIA CUDA","cuda0"),("CPU (chậm)","cpu")]); self.device.setCurrentIndex(max(0,self.device.findData(config["device"])))
        self.profile=combo([("Ít VRAM · VAE tiling","low"),("GPU nhiều VRAM","standard")]); self.profile.setCurrentIndex(max(0,self.profile.findData(config["profile"])))
        self.cache=combo([("Tự động","auto"),("Q8 cache · thử nghiệm","q8_0"),("F16 cache","f16"),("Tắt cache","disabled")]); self.cache.setCurrentIndex(max(0,self.cache.findData(config["cache_type"])))
        self.timeout=QSpinBox(); self.timeout.setRange(120,7200); self.timeout.setValue(config["timeout"])
        self.vram=QLineEdit(str(config["max_vram"]))
        self.auto_updates=QCheckBox("Kiểm tra phiên bản mới khi mở app (GitHub)"); self.auto_updates.setChecked(config.get("check_updates",True))
        for label,w in [("Thiết bị",self.device),("Bộ nhớ",self.profile),("Prefix cache",self.cache),("Giới hạn / ảnh (giây)",self.timeout),("VRAM GiB (âm = dự trữ)",self.vram)]: form.addRow(label,w)
        form.addRow(muted("Model Q4 + encoder Q4 khoảng 11.6 GB. Máy ít RAM có thể rất chậm do paging. 2K cần nhiều tài nguyên hơn 1K."))
        form.addRow(self.auto_updates)
        self.tabs.addTab(runtime,"Model & lưu ảnh")
        web=QWidget(); box=QVBoxLayout(web)
        box.addWidget(QLabel("Kết nối Chrome / Edge bằng Native Messaging"))
        box.addWidget(muted("1. Bấm Đăng ký kết nối.\n2. Mở chrome://extensions hoặc edge://extensions, bật Developer mode.\n3. Load unpacked và chọn thư mục browser-extension.\n4. Chuột phải ảnh → Artwork Local Studio. Chọn Rectangle/Lasso rồi Gửi vào Queue."))
        def register():
            try:
                from .native_host import register_host
                register_host(window.settings.root,window.settings.data)
                QMessageBox.information(self,"Kết nối","Đã đăng ký Chrome / Edge cho tài khoản Windows này.")
            except Exception as exc: window.error(exc)
        box.addWidget(button("Đăng ký kết nối",register))
        box.addWidget(button("Mở thư mục extension",lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(window.settings.root/"browser-extension")))))
        box.addWidget(muted("Không có API AI. Trình duyệt chỉ tải ảnh từ website và chuyển ảnh vào app local."))
        box.addStretch(); self.tabs.addTab(web,"Ảnh website")
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save); buttons.rejected.connect(self.reject); layout.addWidget(buttons)
    def save(self):
        try:
            budget=float(self.vram.text())
            if not -64<=budget<=128: raise ValueError("VRAM budget không hợp lệ.")
            self.window.settings.values.update(model_dir=self.models.text(),runtime_exe=self.runtime.text(),output_dir=self.output.text(),
                device=self.device.currentData(),profile=self.profile.currentData(),cache_type=self.cache.currentData(),timeout=self.timeout.value(),max_vram=budget,check_updates=self.auto_updates.isChecked())
            self.window.settings.save(); self.accept()
        except Exception as exc: self.window.error(exc)
