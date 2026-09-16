import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
import demo


class FakeCamera:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def configure(self, **kwargs):
        self.calls.append("configure")

    def start(self):
        self.calls.append("start")

    def get_frame(self, timeout_ms):
        self.calls.append("get_frame")
        if self.fail:
            raise RuntimeError("frame failed")
        cloud = np.ones((2, 3, 3), dtype=np.float32)
        return {"cartesian_depth": [np.ones((2, 3), dtype=np.float32)],
                "point_cloud": [cloud]}

    def stop(self):
        self.calls.append("stop")

    def close(self):
        self.calls.append("close")


class FakeApi:
    def __init__(self, camera):
        self.device = camera

    def camera_manager(self):
        return self

    def get_camera_list(self):
        return [{"id": "media0/IMX704", "supported_modes": {"311c": {}}}]

    def camera(self, camera_id, mode, processing_flags):
        assert camera_id == "media0/IMX704"
        assert mode == 0x311C
        assert processing_flags == ["cartesian_depth", "point_cloud"]
        return self.device


class DemoTests(unittest.TestCase):
    def test_headless_capture_waits_after_start_and_cleans_up(self):
        camera = FakeCamera()
        args = demo.parse_args(["--frames", "2", "--no-display"])
        with patch.object(demo.time, "sleep") as sleep:
            demo.run(FakeApi(camera), args)
        sleep.assert_called_once_with(2.0)
        self.assertEqual(camera.calls,
                         ["configure", "start", "get_frame", "get_frame", "stop", "close"])

    def test_frame_failure_still_stops_and_closes(self):
        camera = FakeCamera(fail=True)
        args = demo.parse_args(["--frames", "1", "--no-display", "--startup-delay", "0"])
        with self.assertRaisesRegex(RuntimeError, "frame failed"):
            demo.run(FakeApi(camera), args)
        self.assertEqual(camera.calls,
                         ["configure", "start", "get_frame", "stop", "close"])

    def test_list_does_not_open_camera(self):
        camera = FakeCamera()
        with patch("builtins.print") as printed:
            demo.run(FakeApi(camera), demo.parse_args(["--list"]))
        self.assertIn("Camera #0", printed.call_args_list[0].args[0])
        self.assertEqual(camera.calls, [])

    def test_headless_capture_requires_frame_count(self):
        with self.assertRaisesRegex(ValueError, "requires --frames"):
            demo.run(FakeApi(FakeCamera()), demo.parse_args(["--no-display"]))

    def test_saves_last_cloud(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "cloud.npy"
            args = demo.parse_args(["--frames", "1", "--no-display", "--startup-delay", "0",
                                    "--output", str(output)])
            demo.run(FakeApi(FakeCamera()), args)
            self.assertEqual(np.load(output).shape, (2, 3, 3))

    def test_depth_and_point_cloud_share_one_figure(self):
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as pyplot
        except Exception as exc:
            self.skipTest("Matplotlib is unavailable: {}".format(exc))
        camera = FakeCamera()
        args = demo.parse_args(["--frames", "1", "--startup-delay", "0"])
        with patch.object(pyplot, "show"), patch.object(pyplot, "pause"):
            demo.run(FakeApi(camera), args)
        self.assertIn("stop", camera.calls)
        self.assertIn("close", camera.calls)

        figure = pyplot.figure()
        depth_axis = figure.add_subplot(1, 2, 1)
        cloud_axis = figure.add_subplot(1, 2, 2, projection="3d")
        image = depth_axis.imshow(np.zeros((2, 3)))
        frame = FakeCamera().get_frame(1000)
        with patch.object(pyplot, "pause"):
            demo.draw_frame(frame["cartesian_depth"][0], frame["point_cloud"][0],
                            image, cloud_axis, figure, pyplot)
        self.assertEqual(image.get_array().shape, (2, 3))
        self.assertEqual(len(cloud_axis.collections), 1)
        pyplot.close(figure)

    def test_hex_mode_with_prefix(self):
        camera = FakeCamera()
        args = demo.parse_args(["--mode", "0x311C", "--frames", "1", "--no-display",
                                "--startup-delay", "0"])
        demo.run(FakeApi(camera), args)
        self.assertIn("get_frame", camera.calls)

    def test_default_live_mode_needs_a_gui_backend(self):
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as pyplot
        except Exception as exc:
            self.skipTest("Matplotlib is unavailable: {}".format(exc))
        camera = FakeCamera()
        with self.assertRaisesRegex(RuntimeError, "graphical Matplotlib backend"):
            demo.run(FakeApi(camera), demo.parse_args(["--startup-delay", "0"]))
        self.assertEqual(camera.calls, ["configure", "start", "stop", "close"])


if __name__ == "__main__":
    unittest.main()
