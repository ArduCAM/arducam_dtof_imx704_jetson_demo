# IMX704 Jetson Demo

[简体中文](README.zh-CN.md)

IMX704 C++ and Python demos for Jetson. Both show live depth and 3D point cloud in one window. Python can save a point cloud as `.npy`.

## Requirements

- Jetson with an IMX704 camera and working driver. Only one demo can use the camera at a time.
- C++: C++17, CMake 3.18+, GLFW 3, OpenGL, `pkg-config`, and `libimx704-dev` or an SDK prefix.
- Python: Python 3.8+, an aarch64 `arducam-imx704` wheel for that Python version, and an OpenGL desktop. Dependencies: [python/requirements.txt](python/requirements.txt).

## C++

Replace `VERSION` with the package version:

```bash
sudo apt install libglfw3-dev libgl1-mesa-dev pkg-config
sudo apt install ./libimx704-dev_VERSION_arm64.deb
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
./build/imx704_cpp_demo --list
./build/imx704_cpp_demo
./build/imx704_cpp_demo --no-display --frames 10
```

For an SDK installed outside system paths:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
  -DIMX704_SDK_ROOT=/absolute/path/to/sdk-prefix
```

## Modes

| Code | Range class | Power |
| --- | --- | --- |
| `311C` (default) | 7.5 m | High |
| `321C` | 7.5 m | Low |
| `301C` | 7.5 m | Dual |
| `211C` | 20 m | High |
| `221C` | 20 m | Low |
| `201C` | 20 m | Dual |

Dual modes alternate high and low power. Range class is not a guaranteed measurement distance. Run `--list` to check supported modes; set one with `--mode 211C` (hexadecimal). Both demos use one echo.

## Python

Use a wheel matching Jetson aarch64 and your Python version:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r python/requirements.txt
.venv/bin/python -m pip install --no-deps /absolute/path/to/compatible-wheel.whl
.venv/bin/python python/demo.py --list
.venv/bin/python python/demo.py
.venv/bin/python python/demo.py --frames 10 --output point_cloud.npy
```

`--no-deps` keeps the NumPy version from `python/requirements.txt`. The `.npy` output is the last frame's first-echo cloud, shape `(H, W, 3)`.

## Controls

| Option | C++ | Python |
| --- | --- | --- |
| Camera | `--camera-index 0` | `--camera-index 0` |
| Mode | `--mode 311C` | `--mode 311C` |
| Frame limit | `--frames 10` | `--frames 10` |
| No window | `--no-display --frames 10` | `--no-display --frames 10` |
| Frame timeout | `--timeout-ms 1000` | 1000 ms |

Default: live until the window closes. C++: left-drag rotates the cloud, scroll zooms, Escape exits. Invalid depth pixels are red. See `--help` for more options.
