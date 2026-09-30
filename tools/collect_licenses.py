import urllib.request
from pathlib import Path
root=Path(__file__).resolve().parents[1]
licenses=root/"licenses"
sources={
    "STABLE-DIFFUSION-LICENSE.txt":"https://raw.githubusercontent.com/leejet/stable-diffusion.cpp/3f8527a/LICENSE",
    "GGML-LICENSE.txt":"https://raw.githubusercontent.com/ggml-org/ggml/master/LICENSE",
    "APACHE-2.0.txt":"https://www.apache.org/licenses/LICENSE-2.0.txt",
    "LGPL-3.0.txt":"https://www.gnu.org/licenses/lgpl-3.0.txt",
    "GPL-3.0.txt":"https://www.gnu.org/licenses/gpl-3.0.txt",
    "CUDA-EULA.html":"https://docs.nvidia.com/cuda/eula/index.html"
}
for name,url in sources.items():
    request=urllib.request.Request(url,headers={"User-Agent":"ArtworkLocalStudio/0.1.0"})
    with urllib.request.urlopen(request,timeout=45) as response:
        (licenses/name).write_bytes(response.read(2*1024*1024))
    print(name,flush=True)
