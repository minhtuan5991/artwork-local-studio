import os
os.environ["QT_QPA_PLATFORM"]="offscreen"
import json,tempfile,unittest
from dataclasses import replace
from pathlib import Path
from PIL import Image
from PySide6.QtCore import QPointF,Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from artwork_local.core import Settings,JobOptions
from artwork_local.ui import MainWindow,STYLE,SettingsDialog
from artwork_local.theme import apply_theme
ROOT=Path(__file__).resolve().parents[1]
APP=QApplication.instance() or QApplication([])
QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeui.ttf")
apply_theme(APP)
class UiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.settings=Settings(ROOT,Path(self.temp.name)/"data")
        self.settings.values["output_dir"]=str(Path(self.temp.name)/"output")
        self.settings.values["check_updates"]=False
        self.window=MainWindow(self.settings,json.loads((ROOT/"model-manifest.json").read_text()))
        self.window.show(); APP.processEvents()
        self.source=Path(self.temp.name)/"source.png"; Image.new("RGBA",(400,400),"red").save(self.source)
    def tearDown(self): self.window.close(); APP.processEvents(); self.temp.cleanup()
    def test_rectangle_lasso_original_pixels(self):
        canvas=self.window.source; canvas.load(self.source); canvas.mode="rectangle"; canvas.points=[QPointF(50,50),QPointF(250,250)]
        crop=Path(self.temp.name)/"rect.png"; canvas.crop_to(crop)
        with Image.open(crop) as im: self.assertEqual(im.size,(200,200)); self.assertEqual(im.getpixel((10,10)),(255,0,0,255))
        canvas.mode="lasso"; canvas.points=[QPointF(50,50),QPointF(250,50),QPointF(150,250)]
        crop=Path(self.temp.name)/"lasso.png"; canvas.crop_to(crop)
        with Image.open(crop) as im: self.assertEqual(im.getpixel((0,199))[3],0); self.assertEqual(im.getpixel((100,80))[3],255)
    def test_queue_selection_and_filter(self):
        jid=self.window.store.enqueue(self.window.store.prepare(self.source),JobOptions(),self.settings.values["output_dir"])["job_id"]
        self.window.refresh(); self.window.table.selectRow(0); APP.processEvents()
        self.assertEqual(self.window.selected_ids(),[jid]); self.assertEqual(self.window.source.original,(400,400))
        self.window.filter.setCurrentIndex(self.window.filter.findData("completed")); APP.processEvents(); self.assertEqual(self.window.model.rowCount(),0)
        self.window.filter.setCurrentIndex(0); self.window.table.selectRow(0)
        self.window.store.update(jid,status="generating"); self.window.store.hide([jid]); self.window.refresh(); self.assertEqual(self.window.model.rowCount(),1)
    def test_settings_and_default_options(self):
        self.assertEqual(self.window.current_options(),JobOptions()); self.window.size.setCurrentIndex(1); self.window.background.setCurrentIndex(2)
        options=self.window.current_options(); self.assertEqual(options.size,2048); self.assertEqual(options.background,"chroma")
    def add_jobs(self,count=3):
        prepared=self.window.store.prepare(self.source)
        ids=[self.window.store.enqueue(prepared,replace(JobOptions(),seed=42+i),self.settings.values["output_dir"])["job_id"] for i in range(count)]
        self.window.refresh(); return ids
    def test_select_all_clear_and_selection_survives_refresh(self):
        ids=self.add_jobs(); self.assertFalse(self.window.remove_button.isEnabled())
        QTest.mouseClick(self.window.select_all_button,Qt.MouseButton.LeftButton)
        self.assertEqual(set(self.window.selected_ids()),set(ids))
        self.assertEqual(self.window.selection_count.text(),"3 đã chọn")
        self.window.refresh(); self.assertEqual(set(self.window.selected_ids()),set(ids))
        QTest.mouseClick(self.window.clear_selection_button,Qt.MouseButton.LeftButton)
        self.assertEqual(self.window.selected_ids(),[]); self.assertFalse(self.window.remove_button.isEnabled())
        self.window.table.setFocus(); QTest.keyClick(self.window.table,Qt.Key.Key_A,Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(set(self.window.selected_ids()),set(ids))
    def test_remove_preview_and_undo_with_keyboard(self):
        ids=self.add_jobs(1); self.window.table.selectRow(0); APP.processEvents()
        self.assertIsNotNone(self.window.source.path)
        self.window.table.setFocus(); QTest.keyClick(self.window.table,Qt.Key.Key_Delete); APP.processEvents()
        self.assertEqual(self.window.model.rowCount(),0)
        self.assertIsNone(self.window.source.path); self.assertIsNone(self.window.result.path)
        self.assertEqual(self.window.angle.value(),0)
        self.assertTrue(self.window.undo_remove_button.isEnabled())
        QTest.keyClick(self.window.table,Qt.Key.Key_Z,Qt.KeyboardModifier.ControlModifier); APP.processEvents()
        self.assertEqual(self.window.selected_ids(),ids)
        self.assertEqual(self.window.store.get(ids[0])["status"],"canceled")
        self.assertIsNotNone(self.window.source.path)
    def test_filtered_bulk_remove_keeps_unselected_and_active_rows(self):
        ids=self.add_jobs(4)
        self.window.store.update(ids[0],status="completed"); self.window.store.update(ids[1],status="generating")
        self.window.filter.setCurrentIndex(self.window.filter.findData("completed"))
        self.window.select_all_queue(); self.window.hide_selected()
        self.assertFalse(self.window.store.get(ids[0])["visible"])
        self.assertTrue(all(self.window.store.get(jid)["visible"] for jid in ids[1:]))
        self.window.undo_remove(); self.assertEqual(self.window.filter.currentData(),"all")
        self.assertEqual(self.window.selected_ids(),[ids[0]])
        self.window.select_all_queue(); self.window.hide_selected()
        self.assertEqual([job["id"] for job in self.window.model.jobs],[ids[1]])
        self.assertIn("đang xử lý",self.window.status.text())
        self.assertFalse(self.window.remove_button.isEnabled())
    def test_delete_shortcut_does_not_steal_text_input(self):
        ids=self.add_jobs(1); self.window.table.selectRow(0)
        self.window.seed.setText("123"); self.window.seed.setFocus(); self.window.seed.selectAll()
        QTest.keyClick(self.window.seed,Qt.Key.Key_Delete)
        self.assertEqual(self.window.seed.text(),"")
        self.assertTrue(self.window.store.get(ids[0])["visible"])
    def test_remove_preserves_unrelated_source_preview(self):
        self.add_jobs(1); self.window.table.selectRow(0)
        other=Path(self.temp.name)/"other.png"; Image.new("RGBA",(80,120),"green").save(other)
        self.window.source.load(other); self.window.preview_id=None
        self.window.hide_selected(); self.assertEqual(self.window.source.path,other)
    def test_multiple_remove_batches_undo_independently(self):
        ids=self.add_jobs(2)
        self.window.table.selectRow(0); self.window.hide_selected()
        self.window.table.selectRow(0); self.window.hide_selected()
        self.window.undo_remove(); self.assertEqual(self.window.selected_ids(),[ids[1]])
        self.window.undo_remove(); self.assertEqual(self.window.selected_ids(),[ids[0]])
        self.assertEqual(self.window.model.rowCount(),2); self.assertFalse(self.window.undo_remove_button.isEnabled())
    def test_rotated_roi_is_the_actual_queued_input(self):
        image=Image.new("RGBA",(400,200),"red")
        for x in range(200,400):
            for y in range(200): image.putpixel((x,y),(0,255,0,255))
        image.save(self.source); canvas=self.window.source; canvas.load(self.source)
        canvas.set_angle(90); self.assertEqual(canvas.original,(200,400)); self.assertEqual(self.window.angle.value(),90)
        canvas.mode="rectangle"; canvas.points=[QPointF(0,200),QPointF(200,400)]
        crop=Path(self.temp.name)/"rotated-input.png"; canvas.crop_to(crop)
        prepared=self.window.store.prepare(crop)
        jid=self.window.store.enqueue(prepared,JobOptions(),self.settings.values["output_dir"],{"source_rotation_degrees":90})["job_id"]
        with Image.open(self.window.store.get(jid)["source_path"]) as im:
            self.assertEqual(im.size,(200,200)); self.assertEqual(im.getpixel((100,100)),(0,255,0,255))
        canvas.set_angle(0); self.assertEqual(canvas.points,[]); self.assertEqual(canvas.original,(400,200))
    def test_widget_screenshot(self):
        self.window.source.load(ROOT/"test-output"/"benchmark"/"mockup.png"); self.window.source_name="mockup.png"
        self.window.mode.setCurrentIndex(1); self.window.source.points=[QPointF(350,250),QPointF(680,620)]; self.window.source.update(); APP.processEvents()
        folder=ROOT/"test-output"; folder.mkdir(exist_ok=True); self.assertTrue(self.window.grab().save(str(folder/"ui-workspace.png")))
    def test_corner_drag_changes_actual_input_pixels(self):
        image=Image.new("RGBA",(400,400),"red")
        image.paste((0,255,0,255),(200,0,400,400)); image.save(self.source)
        canvas=self.window.source; canvas.load(self.source); APP.processEvents()
        rect=canvas.image_rect()
        QTest.mousePress(canvas,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,rect.topRight().toPoint())
        self.assertIsNotNone(canvas.rotating)
        QTest.mouseMove(canvas,rect.bottomRight().toPoint(),10)
        QTest.mouseRelease(canvas,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,rect.bottomRight().toPoint())
        self.assertAlmostEqual(canvas.angle,90,delta=.5)
        self.assertIsNone(canvas.rotating)
        target=Path(self.temp.name)/"anchor-rotated.png"; canvas.crop_to(target)
        with Image.open(target) as rotated:
            self.assertEqual(rotated.getpixel((200,70)),(255,0,0,255))
            self.assertEqual(rotated.getpixel((200,330)),(0,255,0,255))
    def test_settings_background_stays_light_under_dark_system_palette(self):
        from PySide6.QtGui import QPalette,QColor
        dark=QPalette(); dark.setColor(QPalette.ColorRole.Window,QColor("#202020")); dark.setColor(QPalette.ColorRole.Base,QColor("#494949"))
        APP.styleHints().setColorScheme(Qt.ColorScheme.Dark); APP.setPalette(dark)
        apply_theme(APP)
        dialog=SettingsDialog(self.window); dialog.tabs.setCurrentIndex(1); dialog.show(); APP.processEvents()
        page=dialog.tabs.widget(1); pixel=page.grab().toImage().pixelColor(20,page.height()-20)
        self.assertGreater(min(pixel.red(),pixel.green(),pixel.blue()),230)
        # The offscreen platform has no OS color-scheme preference; rendered pixels
        # and the explicit palette are the relevant light-theme guarantees.
        self.assertEqual(APP.palette().color(QPalette.ColorRole.Base).name(),"#ffffff")
        dialog.reject()
if __name__=="__main__": unittest.main()
