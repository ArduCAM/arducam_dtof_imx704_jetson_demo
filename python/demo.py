"""Capture IMX704 point-cloud frames with the installed Python library wheel."""

import argparse
import math
import sys
import time
from pathlib import Path


MODES = ("311C", "321C", "301C", "211C", "221C", "201C")


def build_parser():
    parser = argparse.ArgumentParser(description="IMX704 Jetson Python demo")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="List detected cameras")

    capture = subparsers.add_parser("capture", help="Capture point-cloud frames")
    capture.add_argument("--camera-index", type=int, default=0)
    capture.add_argument("--mode", choices=MODES, default="311C")
    capture.add_argument("--frames", type=int, default=10)
    capture.add_argument("--timeout-ms", type=int, default=100)
    capture.add_argument("--startup-delay", type=float, default=2.0,
                         help="Seconds to wait after stream-on (default: 2)")
    capture.add_argument("--output", type=Path,
                         help="Save the last first-echo point cloud to a .npy file")
    return parser


def get_cameras(camera_api):
    cameras = camera_api.camera_manager().get_camera_list()
    if not cameras:
        raise RuntimeError("No IMX704 camera found")
    return cameras


def capture_frames(camera_api, args):
    if (args.camera_index < 0 or args.frames < 1 or args.timeout_ms < 1 or
            not math.isfinite(args.startup_delay) or args.startup_delay < 0):
        raise ValueError("Invalid capture options")
    if args.output is not None and args.output.suffix != ".npy":
        raise ValueError("--output must end in .npy")

    cameras = get_cameras(camera_api)
    if args.camera_index >= len(cameras):
        raise ValueError("Camera index out of range ({} detected)".format(len(cameras)))

    selected = cameras[args.camera_index]
    supported_modes = selected.get("supported_modes", {})
    if supported_modes and args.mode.lower() not in {str(mode).lower() for mode in supported_modes}:
        raise ValueError("Mode {} is not supported by this camera".format(args.mode))
    camera = camera_api.camera(selected["id"], int(args.mode, 16),
                               processing_flags=["point_cloud"])
    streaming = False
    try:
        camera.configure(sync_mode="master", number_of_echo=1)
        camera.start()
        streaming = True
        if args.startup_delay:
            time.sleep(args.startup_delay)

        started_at = time.monotonic()
        last_frame = None
        for count in range(args.frames):
            last_frame = camera.get_frame(args.timeout_ms)
            if not last_frame.get("point_cloud"):
                raise RuntimeError("Frame has no point cloud")
            cloud = last_frame["point_cloud"][0]
            if cloud.ndim != 3 or cloud.shape[-1] != 3:
                raise RuntimeError("Unexpected point-cloud shape: {}".format(cloud.shape))
            print("Frame {}: id={}, points={}".format(
                count + 1, last_frame["frame_id"], cloud.shape[0] * cloud.shape[1]))

        elapsed = time.monotonic() - started_at
        print("Captured {} frames in {:.2f}s ({:.2f} FPS)".format(
            args.frames, elapsed, args.frames / elapsed if elapsed else 0.0))

        if args.output is not None:
            import numpy as np
            np.save(args.output, last_frame["point_cloud"][0])
            print("Saved point cloud to {}".format(args.output))
    finally:
        try:
            if streaming:
                camera.stop()
        finally:
            camera.close()


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        import imx704_processor as camera_api
    except ImportError as exc:
        print("IMX704 Python wheel is not installed: {}".format(exc), file=sys.stderr)
        return 1
    try:
        if args.command == "list":
            for index, camera in enumerate(get_cameras(camera_api)):
                print("Camera #{}: {}".format(index, camera))
        else:
            capture_frames(camera_api, args)
    except Exception as exc:
        print("Error: {}".format(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
