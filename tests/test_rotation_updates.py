import io,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from artwork_local.image_ops import rotate_input,rotated_size
from artwork_local.updates import check_latest,parse_release
from artwork_local.core import Settings
from artwork_local.native_host import accept_payload

class RotationUpdateTests(unittest.TestCase):
    def test_dimensions_match_actual_pillow_rotation(self):
        for size in [(400,200),(101,69),(16,17),(3011,2047)]:
            image=Image.new("RGBA",size,"red")
            for angle in [0,90,-90,180,12.3,-16.7,45,179.9]:
                self.assertEqual(rotated_size(size,angle),rotate_input(image,angle).size,(size,angle))

    def test_clockwise_pixels_and_transparent_expansion(self):
        image=Image.new("RGBA",(80,40),"red"); image.putpixel((0,0),(0,255,0,255))
        rotated=rotate_input(image,90)
        self.assertEqual(rotated.size,(40,80)); self.assertEqual(rotated.getpixel((39,0)),(0,255,0,255))
        tilted=rotate_input(image,12); self.assertEqual(tilted.getpixel((0,0))[3],0)
        for value in [float("nan"),float("inf"),361]:
            with self.assertRaises(ValueError): rotate_input(image,value)

    def test_installed_defaults_stay_outside_install_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp); root=base/"program"; root.mkdir(); (root/"installation.json").write_text("{}")
            with patch.dict(os.environ,{"LOCALAPPDATA":str(base/"local")}):
                settings=Settings(root)
                self.assertEqual(settings.data,base/"local"/"ArtworkLocalStudio")
                settings.save()
                self.assertFalse((root/"data").exists())
                self.assertTrue(Path(settings.values["model_dir"]).is_relative_to(settings.data))

    def test_release_version_and_trusted_url(self):
        payload={"tag_name":"v0.3.0","body":"New features","html_url":"https://evil.invalid/"}
        self.assertEqual(parse_release(payload,"0.2.0")["url"],"https://github.com/minhtuan5991/artwork-local-studio/releases/tag/v0.3.0")
        self.assertEqual(parse_release({"tag_name":"v0.2.0"},"0.2.0")["state"],"current")
        self.assertEqual(parse_release({"tag_name":"v0.1.0"},"0.2.0")["state"],"current")
        self.assertEqual(parse_release({"tag_name":"v1.0.0","prerelease":True},"0.2.0")["state"],"current")
        with self.assertRaises(ValueError): parse_release({"tag_name":"v2/../../attack"},"0.2.0")

    def test_network_failure_does_not_prevent_startup(self):
        def broken(*args,**kwargs): raise OSError("offline")
        self.assertEqual(check_latest("0.2.0",broken)["state"],"error")
        def fake(request,timeout):
            self.assertEqual(timeout,10); self.assertNotIn("Authorization",request.headers)
            return io.BytesIO(json.dumps({"tag_name":"v0.3.0"}).encode())
        self.assertEqual(check_latest("0.2.0",fake)["state"],"available")

if __name__=="__main__": unittest.main()
