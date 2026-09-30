# Third-party software

Keep the full license notices in this folder when sharing the portable application.

- Qwen-Image-2.1 weights: Qwen Research License, noncommercial research/evaluation; QWEN-LICENSE.txt.
- Qwen3-VL-8B-Instruct-GGUF and vision projector: Apache-2.0; APACHE-2.0.txt and corresponding Hugging Face model card.
- stable-diffusion.cpp: MIT; STABLE-DIFFUSION-LICENSE.txt.
- ggml: MIT; GGML-LICENSE.txt.
- NVIDIA CUDA runtime: NVIDIA redistribution terms, CUDA-EULA.html. Runtime is downloaded from the backend's release; model-free app archive does not include CUDA DLLs.
- PySide6/Shiboken6/Qt: LGPL-3.0/GPL alternatives; LGPL-3.0.txt. Qt DLLs remain separately replaceable in _internal. Source: https://code.qt.io/cgit/pyside/pyside-setup.git/ and https://code.qt.io/cgit/qt/ . No app restriction on modifying/replacing LGPL libraries or reverse engineering for debugging those changes.
- Pillow: HPND; PILLOW-LICENSE.txt.
- NumPy: BSD and bundled notices; NUMPY-LICENSE.txt.
- CPython: PSF License; PYTHON-LICENSE.txt.
- PyInstaller bootloader: GPL with bootloader exception; PYINSTALLER-LICENSE.txt.

Project source and build scripts are available at https://github.com/minhtuan5991/artwork-local-studio .
Packaging installs separately replaceable Qt DLLs in _internal, allowing library replacement.
