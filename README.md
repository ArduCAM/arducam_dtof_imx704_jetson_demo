# IMX704 Jetson Demo

[简体中文](README.zh-CN.md)

IMX704 C++ and Python demos for Jetson. Both show live depth and 3D point cloud in one window. Python can save a point cloud as `.npy`.

## Requirements

- Jetson with an IMX704 camera and working driver. Only one demo can use the camera at a time.
- C++: C++17, CMake 3.18+, GLFW 3, OpenGL, `pkg-config`, and `libarducam-imx704-dev` or an SDK prefix.
- Python: Python 3.8+, an aarch64 `arducam_imx704` wheel for that Python version, and an OpenGL desktop. Dependencies: [python/requirements.txt](python/requirements.txt).

## Install SDK and dependencies

Run the following commands from the repository root.

### C++

Ensure your APT source provides `libarducam-imx704-dev`.

```bash
sudo apt install libarducam-imx704-dev
sudo apt install libglfw3-dev libgl1-mesa-dev pkg-config
```

### Python

Ensure your pip package index provides an `arducam_imx704` wheel matching Jetson aarch64 and your Python version. The requirements file includes the SDK and display dependencies.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r python/requirements.txt
```

## Build and run the demos

### C++

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
```

For an SDK installed outside system paths, replace the CMake configuration command above with:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
  -DIMX704_SDK_ROOT=/absolute/path/to/sdk-prefix
```

```bash
./build/imx704_cpp_demo --list
./build/imx704_cpp_demo
./build/imx704_cpp_demo --no-display --frames 10
```

### Python

```bash
.venv/bin/python python/demo.py --list
.venv/bin/python python/demo.py
.venv/bin/python python/demo.py --frames 10 --output point_cloud.npy
```

The `.npy` output is the last frame's first-echo cloud, shape `(H, W, 3)`.

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

## Controls

| Option | C++ | Python |
| --- | --- | --- |
| Camera | `--camera-index 0` | `--camera-index 0` |
| Mode | `--mode 311C` | `--mode 311C` |
| Frame limit | `--frames 10` | `--frames 10` |
| No window | `--no-display --frames 10` | `--no-display --frames 10` |
| Frame timeout | `--timeout-ms 1000` | 1000 ms |

Default: live until the window closes. Press Q in either window to exit. C++: left-drag rotates the cloud, scroll zooms, and Escape also exits. Invalid depth pixels are red. See `--help` for more options.
