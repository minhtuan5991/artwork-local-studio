"""Isolated visual QA; never reads the user's Queue or starts inference."""
import json,os,sys
from dataclasses import replace
os.environ["QT_QPA_PLATFORM"]="offscreen"
from pathlib import Path
root=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(root))
from PIL import Image,ImageDraw
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from artwork_local.core import Settings,JobOptions
from artwork_local.ui import MainWindow,STYLE
from artwork_local.theme import apply_theme
from artwork_local import __version__
folder=root/"test-output"/("ui-v"+__version__); folder.mkdir(parents=True,exist_ok=True)
app=QApplication([]); app.setStyle("Fusion")
QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeui.ttf"); apply_theme(app)
settings=Settings(root,folder/"data"); settings.values["check_updates"]=False
settings.values["output_dir"]=str(folder/"export")
window=MainWindow(settings,json.loads((root/"model-manifest.json").read_text()))
image=Image.new("RGBA",(640,960),"#dddce4"); draw=ImageDraw.Draw(image)
draw.rounded_rectangle((100,160,540,800),30,fill="#222e32")
draw.ellipse((220,300,420,500),fill="#ffba36"); draw.text((240,550),"ARTWORK 42",fill="white")
path=folder/"mockup.png"; image.save(path)
prepared=window.store.prepare(path); result=window.store.enqueue(prepared,JobOptions(),settings.values["output_dir"])
window.refresh(); window.source.load(path)
master=root/"test-output"/"benchmark-pod-clone"/"qwen.png"
if master.is_file(): window.result.load(master)
for width,height in [(1280,800),(1920,1080)]:
    window.resize(width,height); window.show(); app.processEvents()
    assert window.source.width()>180 and window.source.height()>=140
    preview_bottom=window.source.mapTo(window.centralWidget(),window.source.rect().bottomLeft()).y()
    status_top=window.source_status.mapTo(window.centralWidget(),window.source_status.rect().topLeft()).y()
    assert status_top>preview_bottom,(preview_bottom,status_top)
    for widget in [window.size,window.background,window.chroma,window.steps,window.seed]:
        assert widget.height()>=34,(width,widget.height())
    assert window.table.geometry().height()>250
    window.grab().save(str(folder/(str(width)+"x"+str(height)+".png")))
window.close(); print("Desktop screenshots and layout bounds passed at 1280×800 and 1920×1080.")
statuses=["completed","needs_review","canceled","queued","completed","failed","queued","completed"]
for i,status in enumerate(statuses):
    item={**prepared,"name":f"Artwork {i+1:02d}.png"}
    added=window.store.enqueue(item,replace(JobOptions(),seed=100+i),settings.values["output_dir"])
    jid=added.get("job_id") or added["job"]["id"]
    window.store.update(jid,status=status)
window.refresh(); window.table.selectRow(0); window.show(); app.processEvents()
from PySide6.QtCore import QItemSelectionModel
selection=window.table.selectionModel()
selection.select(window.model.index(1,0),QItemSelectionModel.SelectionFlag.Select|QItemSelectionModel.SelectionFlag.Rows)
for width,height in [(1280,800),(1920,1080)]:
    window.resize(width,height); app.processEvents()
    assert window.table.height()>250
    for control in [window.select_all_button,window.clear_selection_button,window.remove_button,window.undo_remove_button]:
        assert control.width()>=control.fontMetrics().horizontalAdvance(control.text())+20,(control.text(),control.width())
    window.grab().save(str(folder/(str(width)+"x"+str(height)+"-queue-selection.png")))
assert len(window.selected_ids())==2
window.hide_selected(); assert window.undo_remove_button.isEnabled()
window.undo_remove(); assert len(window.selected_ids())==2
window.close(); print("Queue selection/removal/undo screenshots and control widths passed.")
