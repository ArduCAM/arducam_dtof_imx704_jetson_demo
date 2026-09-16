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


class LiveDisplay:
    """Update two persistent GPU visuals in one window."""

    def __init__(self):
        from vispy import color, scene

        self.cmap = color.get_colormap("viridis")
        self.canvas = scene.SceneCanvas(title="IMX704 Depth and Point Cloud",
                                        size=(1100, 550), keys="interactive", show=False)
        self.app = self.canvas.app
        self.closed = False
        self.canvas.events.close.connect(self._on_close)
        grid = self.canvas.central_widget.add_grid()
        depth_view = grid.add_view(row=0, col=0)
        depth_view.camera = scene.PanZoomCamera(aspect=1)
        depth_view.camera.rect = (0, 0, 24, 24)
        self.depth_view = depth_view
        self.image = scene.visuals.Image(np.zeros((24, 24, 4), dtype=np.float32),
                                         interpolation="nearest", parent=depth_view.scene)
        self.depth_shape = (24, 24)

        cloud_view = grid.add_view(row=0, col=1)
        cloud_view.camera = scene.TurntableCamera(fov=45, elevation=30, azimuth=30)
        cloud_view.camera.scale_factor = 2500.0
        self.markers = scene.visuals.Markers(parent=cloud_view.scene)
        self.canvas.show()
        self.app.process_events()

    def _on_close(self, event):
        self.closed = True

    def update(self, depth, cloud):
        self.image.set_data(colorize_depth(depth, self.cmap))
        if depth.shape != self.depth_shape:
            height, width = depth.shape
            self.depth_view.camera.set_range(x=(0, width), y=(0, height), margin=0)
            self.depth_shape = depth.shape

        points = cloud[np.isfinite(cloud).all(axis=2) & (cloud[:, :, 2] > 0)]
        if points.size:
            z_min, z_max = float(points[:, 2].min()), float(points[:, 2].max())
            z = normalize(points[:, 2], z_min, z_max)
            colors = self.cmap.map(z.astype(np.float32))
            self.markers.set_data(points.astype(np.float32), face_color=colors,
                                  edge_width=0, size=7)
        else:
            self.markers.set_data(np.empty((0, 3), dtype=np.float32), edge_width=0)
        self.app.process_events()

    def close(self):
        self.canvas.close()


def normalize(values, low, high):
    if high <= low:
        return np.zeros_like(values, dtype=np.float32)
    return np.clip((values - low) / (high - low), 0, 1).astype(np.float32)


def colorize_depth(depth, cmap):
    """Match the viewer's mirrored, auto-ranged depth image and red invalid pixels."""
    mirrored = np.flip(depth, axis=1)
    finite = np.isfinite(mirrored)
    safe = np.where(finite, mirrored, 0)
    low, high = float(safe.min()), float(safe.max())
    normalized = normalize(safe, low, high)
    rgba = cmap.map(normalized.ravel()).reshape(*depth.shape, 4)
    rgba[~finite | (mirrored == 0)] = (1, 0, 0, 1)
    return rgba.astype(np.float32)


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
    display = None
    try:
        camera.configure(sync_mode="master", number_of_echo=1)
        camera.start()
        streaming = True
        if args.startup_delay:
            time.sleep(args.startup_delay)

        if not args.no_display:
            display = LiveDisplay()

        count = 0
        last_cloud = None
        started_at = time.monotonic()
        while args.frames == 0 or count < args.frames:
            if display is not None:
                display.app.process_events()
            if display is not None and display.closed:
                break
            frame = camera.get_frame(1000)
            depth, cloud = frame["cartesian_depth"][0], frame["point_cloud"][0]
            if depth.ndim != 2 or cloud.shape != depth.shape + (3,):
                raise RuntimeError("Unexpected depth or point-cloud shape")
            count += 1
            last_cloud = cloud
            if display is not None:
                display.update(depth, cloud)

        elapsed = time.monotonic() - started_at
        print("Captured {} frames ({:.2f} FPS)".format(count, count / elapsed if elapsed else 0.0))
        if args.output and last_cloud is not None:
            np.save(args.output, last_cloud)
            print("Saved {}".format(args.output))
    finally:
        if display is not None:
            display.close()
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
