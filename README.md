# IMX704 Jetson Demo

Small C++ and Python examples for the current `imx704-library-driver` API. They are based on the older `lib/samples` examples, but use the current `arducam::depthsense` C++ namespace and an installed SDK/wheel rather than importing library source files. Neither demo reads or records EBD.

Both demos list cameras and capture point-cloud frames. After stream-on returns, they wait 2 seconds by default for the camera-board MCU to initialize; this can be changed from the command line. This is an application-level wait, before the first frame request.

## C++ demo on Jetson

Install the matching `libimx704-dev` arm64 package produced by `imx704-library-driver`, or point CMake to an existing SDK installation prefix:

```bash
sudo apt install ./libimx704-dev_0.5.0_arm64.deb
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
./build/imx704_cpp_demo --list
./build/imx704_cpp_demo --camera-index 0 --mode 311C --frames 10
```

If the SDK is not installed system-wide, configure with `-DIMX704_SDK_ROOT=/path/to/imx704-library-driver/dist/linux_aarch64_gcc`. The demo only uses public headers and `libimx704_camera.a`.

Options include `--timeout-ms`, `--startup-delay-ms` (default `2000`), and `--help`.

## Python demo on Jetson

Create a Python environment and install a wheel matching the Jetson architecture and Python version:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install --no-deps /path/to/arducam_imx704-0.5.0-cp312-cp312-linux_aarch64.whl
.venv/bin/python python/demo.py list
.venv/bin/python python/demo.py capture --camera-index 0 --mode 311C --frames 10
.venv/bin/python python/demo.py capture --frames 10 --output point_cloud.npy
```

Replace the wheel path with the wheel you actually built; its CPython tag must match the interpreter. A `manylinux` aarch64 wheel also works when compatible with the Jetson system. The saved `.npy` file contains the last frame's first-echo point cloud. `--startup-delay` is in seconds (default `2`); `--timeout-ms` controls each frame request.

Run one demo at a time because the camera is acquired exclusively. A connected IMX704 and working Jetson kernel driver are required for live capture. Build and syntax checks can run without camera hardware, but they do not prove live capture.

Chinese instructions: [README.zh-CN.md](README.zh-CN.md).
