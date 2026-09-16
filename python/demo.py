"""Show live IMX704 depth and point-cloud frames."""

import argparse
import math
import sys
import time
from pathlib import Path

import numpy as np


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="IMX704 depth and point-cloud demo")
    parser.add_argument("--list", action="store_true", help="List cameras and exit")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--mode", default="311C", help="Sensor mode in hex (default: 311C)")
    parser.add_argument("--frames", type=int, default=0,
                        help="Frames to capture; 0 runs until the window closes")
    parser.add_argument("--startup-delay", type=float, default=2.0,
                        help="Seconds to wait after stream-on (default: 2)")
    parser.add_argument("--no-display", action="store_true", help="Capture without opening a window")
    parser.add_argument("--output", type=Path, help="Save the last point cloud to a .npy file")
    return parser.parse_args(argv)


def draw_frame(depth, cloud, image, cloud_axis, figure, pyplot):
    valid_depth = depth[np.isfinite(depth) & (depth > 0)]
    image.set_data(depth)
    image.set_clim(0, max(1.0, float(np.percentile(valid_depth, 99))) if valid_depth.size else 1.0)

    points = cloud[np.isfinite(cloud).all(axis=2) & (cloud[:, :, 2] > 0)]
    cloud_axis.clear()
    if points.size:
        cloud_axis.scatter(points[:, 0], points[:, 1], points[:, 2],
                           c=points[:, 2], cmap="viridis", s=8)
    cloud_axis.set(title="Point cloud", xlabel="X (mm)", ylabel="Y (mm)", zlabel="Z (mm)")
    figure.canvas.draw_idle()
    pyplot.pause(0.001)


def run(camera_api, args):
    if (args.camera_index < 0 or args.frames < 0 or
            not math.isfinite(args.startup_delay) or args.startup_delay < 0):
        raise ValueError("Invalid camera index, frame count, or startup delay")
    if args.no_display and args.frames == 0 and not args.list:
        raise ValueError("--no-display requires --frames greater than 0")
    if args.output and args.output.suffix != ".npy":
        raise ValueError("--output must end in .npy")
    cameras = camera_api.camera_manager().get_camera_list()
    if not cameras:
        raise RuntimeError("No IMX704 camera found")
    if args.list:
        for index, info in enumerate(cameras):
            print("Camera #{}: {}".format(index, info))
        return
    if args.camera_index >= len(cameras):
        raise ValueError("Camera index out of range")

    try:
        mode = int(args.mode, 16)
    except ValueError as exc:
        raise ValueError("--mode must be a hexadecimal sensor mode") from exc

    info = cameras[args.camera_index]
    modes = info.get("supported_modes", {})
    supported = {key if isinstance(key, int) else int(str(key), 16) for key in modes}
    if modes and mode not in supported:
        raise ValueError("Mode {} is not supported by this camera".format(args.mode))

    camera = camera_api.camera(info["id"], mode,
                               processing_flags=["cartesian_depth", "point_cloud"])
    streaming = False
    figure = None
    pyplot = None
    try:
        camera.configure(sync_mode="master", number_of_echo=1)
        camera.start()
        streaming = True
        if args.startup_delay:
            time.sleep(args.startup_delay)

        if not args.no_display:
            import matplotlib.pyplot as pyplot
            if args.frames == 0 and pyplot.get_backend().lower() == "agg":
                raise RuntimeError("A graphical Matplotlib backend is required for live display")
            pyplot.ion()
            figure = pyplot.figure("IMX704", figsize=(11, 5))
            depth_axis = figure.add_subplot(1, 2, 1)
            cloud_axis = figure.add_subplot(1, 2, 2, projection="3d")
            image = depth_axis.imshow(np.zeros((24, 24)), cmap="viridis", vmin=0, vmax=1)
            depth_axis.set(title="Depth", xlabel="X", ylabel="Y")
            figure.tight_layout()
            pyplot.show(block=False)

        count = 0
        last_cloud = None
        started_at = time.monotonic()
        while args.frames == 0 or count < args.frames:
            if figure is not None and not pyplot.fignum_exists(figure.number):
                break
            frame = camera.get_frame(1000)
            depth, cloud = frame["cartesian_depth"][0], frame["point_cloud"][0]
            if depth.ndim != 2 or cloud.shape != depth.shape + (3,):
                raise RuntimeError("Unexpected depth or point-cloud shape")
            count += 1
            last_cloud = cloud
            if figure is not None:
                draw_frame(depth, cloud, image, cloud_axis, figure, pyplot)

        elapsed = time.monotonic() - started_at
        print("Captured {} frames ({:.2f} FPS)".format(count, count / elapsed if elapsed else 0.0))
        if args.output and last_cloud is not None:
            np.save(args.output, last_cloud)
            print("Saved {}".format(args.output))
    finally:
        if figure is not None:
            pyplot.close(figure)
        try:
            if streaming:
                camera.stop()
        finally:
            camera.close()


def main(argv=None):
    args = parse_args(argv)
    try:
        import imx704_processor as camera_api
        run(camera_api, args)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print("Error: {}".format(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
