# IMX704 Jetson Demo

[简体中文](README.zh-CN.md)

Minimal C++ and Python examples for IMX704 on Jetson. The C++ example prints point-cloud frame information. The Python example displays a live depth image and 3D point cloud side by side, and can save the last point cloud as a NumPy `.npy` file.

The camera board begins initializing after stream-on. Both examples therefore wait **2 seconds after starting the stream**, before requesting the first frame. You can adjust or disable that delay with a command-line option.

## Requirements

- A Jetson with a connected IMX704 camera and a working camera driver.
- For C++: a C++17 compiler, CMake 3.18+, and the `libimx704-dev` package (or an SDK prefix containing `include/imx704_camera` and `libimx704_camera.a`).
- For Python: Python 3.8+, a graphical desktop with OpenGL support, and an `arducam-imx704` wheel matching your Python version and aarch64 platform. [requirements.txt](requirements.txt) installs NumPy below version 2, VisPy, and PySide6.

Only one example can hold the camera at a time.

## C++ quick start

Install the arm64 development package you received. Replace `VERSION` with the package's actual version:

```bash
sudo apt install ./libimx704-dev_VERSION_arm64.deb
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
./build/imx704_cpp_demo --list
./build/imx704_cpp_demo --camera-index 0 --mode 311C --frames 10
```

If the SDK is not installed system-wide, pass its installation prefix when configuring:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
  -DIMX704_SDK_ROOT=/absolute/path/to/sdk-prefix
```

`--list` prints camera IDs and supported modes. The default capture mode is `311C`; select a mode listed for your camera if needed.

## Python quick start

Create a virtual environment and install a wheel built for the Jetson's architecture and the environment's Python version. Replace the example wheel path with your actual wheel file:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install --no-deps /absolute/path/to/compatible-wheel.whl
.venv/bin/python python/demo.py --list
.venv/bin/python python/demo.py
.venv/bin/python python/demo.py --frames 10 --output point_cloud.npy
```

By default, the Python example runs until you close its window. VisPy shows depth and point cloud in one OpenGL window. The depth image follows the viewer's camera orientation and marks invalid pixels red. Use `--frames 10` for a finite run, or `--no-display --frames 10` on a machine without a desktop. The saved `.npy` file contains the last frame's first-echo point cloud as an `(H, W, 3)` array. The `--no-deps` install keeps the NumPy version selected by `requirements.txt`.

## Common options

| Purpose | C++ | Python |
| --- | --- | --- |
| Camera index | `--camera-index 0` | `--camera-index 0` |
| Capture mode | `--mode 311C` | `--mode 311C` |
| Number of frames | `--frames 10` | `--frames 10` (`0` = until window closes) |
| Per-frame timeout | `--timeout-ms 100` | 1000 ms |
| Post-stream-on delay | `--startup-delay-ms 2000` | `--startup-delay 2` |

Use `--help` for the full CLI help. The C++ example returns a non-zero status if it cannot receive all requested frames; the Python example stops on the first frame error. Both release the camera on normal completion and handled errors.

## Validation

The C++ example can be compiled and the Python tests can run without a camera:

```bash
python3 -m unittest discover -s tests
```

Actual streaming and image quality must be checked on a Jetson with the target camera. No live-camera result is claimed by this repository.
