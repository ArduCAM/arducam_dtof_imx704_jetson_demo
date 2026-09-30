# IMX704 Jetson Demo

[English](README.md)

Jetson 上的 IMX704 C++ 和 Python 示例。两个程序都在同一窗口显示实时深度图和 3D 点云；Python 可保存 `.npy` 点云。

## 运行前准备

- Jetson 已连接 IMX704 相机，驱动正常。两个示例不能同时占用相机。
- C++：C++17、CMake 3.18+、GLFW 3、OpenGL、`pkg-config`，以及 `libarducam-imx704-dev` 或 SDK 安装目录。
- Python：Python 3.8+、匹配该版本的 aarch64 `arducam_imx704` wheel，以及支持 OpenGL 的桌面环境。依赖见 [python/requirements.txt](python/requirements.txt)。

## C++

确保 APT 软件源提供 `libarducam-imx704-dev`。

```bash
sudo apt install libarducam-imx704-dev libglfw3-dev libgl1-mesa-dev pkg-config
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
./build/imx704_cpp_demo --list
./build/imx704_cpp_demo
./build/imx704_cpp_demo --no-display --frames 10
```

SDK 不在系统路径时：

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
  -DIMX704_SDK_ROOT=/absolute/path/to/sdk-prefix
```

## 取图模式

| 编号 | 距离档位 | 功率 |
| --- | --- | --- |
| `311C`（默认） | 7.5 m | 高 |
| `321C` | 7.5 m | 低 |
| `301C` | 7.5 m | 双功率 |
| `211C` | 20 m | 高 |
| `221C` | 20 m | 低 |
| `201C` | 20 m | 双功率 |

双功率模式交替使用高、低功率。距离档位不保证实际测量距离。用 `--list` 查看相机支持的模式，再用十六进制参数指定，例如 `--mode 211C`。两个示例都配置单回波。

## Python

确保 pip 软件源提供匹配 Jetson aarch64 和当前 Python 版本的 `arducam_imx704` wheel：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r python/requirements.txt
.venv/bin/python python/demo.py --list
.venv/bin/python python/demo.py
.venv/bin/python python/demo.py --frames 10 --output point_cloud.npy
```

`.npy` 保存最后一帧第一回波的点云，形状为 `(H, W, 3)`。

## 操作

| 参数 | C++ | Python |
| --- | --- | --- |
| 相机 | `--camera-index 0` | `--camera-index 0` |
| 模式 | `--mode 311C` | `--mode 311C` |
| 帧数限制 | `--frames 10` | `--frames 10` |
| 不显示窗口 | `--no-display --frames 10` | `--no-display --frames 10` |
| 单帧超时 | `--timeout-ms 1000` | 固定 1000 ms |

默认持续运行，直到关闭窗口。在任一示例窗口按 Q 可退出。C++ 可按住左键旋转点云、滚轮缩放，也可按 Escape 退出；无效深度像素显示为红色。其他参数见 `--help`。
