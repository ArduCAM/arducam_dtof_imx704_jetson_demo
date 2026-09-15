# IMX704 Jetson Demo

这个独立仓库提供基于当前 `imx704-library-driver` 公共 API 的 C++ 和 Python 示例。旧版 `lib/samples` 仅作参考；C++ 使用新的 `arducam::depthsense` 命名空间。示例不读取或录制 EBD。

两个示例都可以列出相机并抓取点云。stream-on 返回后默认等待 2 秒，让相机板单片机完成初始化；可通过参数调整。这段等待位于应用层、首次取帧之前。

## C++

在 Jetson 上安装匹配的 `libimx704-dev` arm64 包，或用 `IMX704_SDK_ROOT` 指向库的安装目录：

```bash
sudo apt install ./libimx704-dev_0.5.0_arm64.deb
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
./build/imx704_cpp_demo --list
./build/imx704_cpp_demo --camera-index 0 --mode 311C --frames 10
```

若未安装到系统路径，配置时加入 `-DIMX704_SDK_ROOT=/path/to/imx704-library-driver/dist/linux_aarch64_gcc`。`--startup-delay-ms` 默认 `2000`，`--timeout-ms` 指定单帧超时。

## Python

选择与 Jetson 架构及 Python 版本匹配的库 wheel：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install --no-deps /path/to/arducam_imx704-0.5.0-cp312-cp312-linux_aarch64.whl
.venv/bin/python python/demo.py list
.venv/bin/python python/demo.py capture --camera-index 0 --mode 311C --frames 10
.venv/bin/python python/demo.py capture --frames 10 --output point_cloud.npy
```

示例中的 wheel 文件名仅为示意，请换成实际构建出的文件。保存的 `.npy` 是最后一帧第一回波的点云。`--startup-delay` 单位为秒，默认 `2`。

相机只能被一个程序独占使用，因此不要同时运行两个示例。实时取帧需要已连接的 IMX704 和正常工作的 Jetson 内核驱动；本机编译或语法检查不能代替设备验证。

English README: [README.md](README.md).
