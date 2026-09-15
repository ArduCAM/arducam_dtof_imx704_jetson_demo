# IMX704 Jetson Demo

[English](README.md)

这个仓库提供两个简洁示例：在 Jetson 上用 C++ 或 Python 发现 IMX704 相机并抓取点云帧。Python 示例还可以将最后一帧第一回波的点云保存为 NumPy `.npy` 文件。示例不使用嵌入式数据（EBD）。

相机板会在 stream-on 后开始初始化，因此两个示例均在**启动视频流后等待 2 秒**，再请求第一帧。等待时间可通过命令行参数调整或设为 0。

## 运行前准备

- 已连接 IMX704 相机、相机驱动正常工作的 Jetson。
- C++：支持 C++17 的编译器、CMake 3.18+，以及 `libimx704-dev` 开发包；也可使用含 `include/imx704_camera` 和 `libimx704_camera.a` 的 SDK 安装目录。
- Python：Python 3.8+、与该 Python 版本和 aarch64 平台匹配的 `arducam-imx704` wheel。[requirements.txt](requirements.txt) 将 NumPy 限定在 2 以下。

相机只能被一个示例独占使用，不要同时运行 C++ 与 Python 程序。

## C++ 快速开始

安装收到的 arm64 开发包，将 `VERSION` 换成实际版本号：

```bash
sudo apt install ./libimx704-dev_VERSION_arm64.deb
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
./build/imx704_cpp_demo --list
./build/imx704_cpp_demo --camera-index 0 --mode 311C --frames 10
```

若 SDK 没有安装到系统路径，配置时指定其安装前缀：

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
  -DIMX704_SDK_ROOT=/absolute/path/to/sdk-prefix
```

`--list` 会打印相机 ID 和支持的模式。默认抓取模式为 `311C`；如相机不支持，请选择列表中的模式。

## Python 快速开始

创建虚拟环境并安装与 Jetson 架构、Python 版本匹配的 wheel；将示意路径换成实际 wheel 文件：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install --no-deps /absolute/path/to/compatible-wheel.whl
.venv/bin/python python/demo.py list
.venv/bin/python python/demo.py capture --camera-index 0 --mode 311C --frames 10
.venv/bin/python python/demo.py capture --frames 10 --output point_cloud.npy
```

保存的 `.npy` 文件是最后一帧第一回波的点云，数组形状为 `(H, W, 3)`。`--no-deps` 用于保留 `requirements.txt` 指定的 NumPy 版本。

## 常用参数

| 用途 | C++ | Python |
| --- | --- | --- |
| 相机索引 | `--camera-index 0` | `--camera-index 0` |
| 取图模式 | `--mode 311C` | `--mode 311C` |
| 帧数 | `--frames 10` | `--frames 10` |
| 单帧超时 | `--timeout-ms 100` | `--timeout-ms 100` |
| stream-on 后等待 | `--startup-delay-ms 2000` | `--startup-delay 2` |

完整命令行帮助见 `--help`。C++ 示例未收到全部请求帧时会返回非零状态；Python 示例遇到取帧错误即停止。正常完成或处理错误后，两个程序都会释放相机。

## 验证范围

无相机时可以编译 C++ 示例并运行 Python 测试：

```bash
python3 -m unittest discover -s tests
```

实际视频流和图像质量仍须在目标 Jetson 与相机上验证；本仓库不声明已经完成实机取帧测试。
