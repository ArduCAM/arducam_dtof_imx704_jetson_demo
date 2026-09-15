import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
import demo


class FakeCamera:
    def __init__(self, fail_frame=False):
        self.calls = []
        self.fail_frame = fail_frame

    def configure(self, **kwargs):
        self.calls.append("configure")

    def start(self):
        self.calls.append("start")

    def get_frame(self, timeout_ms):
        self.calls.append("get_frame")
        if self.fail_frame:
            raise RuntimeError("frame failed")
        return {"frame_id": 7, "point_cloud": [[(1, 2, 3)]]}

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
        return [{"id": "media0/IMX704"}]

    def camera(self, camera_id, mode, processing_flags):
        assert camera_id == "media0/IMX704"
        assert mode == 0x311C
        assert processing_flags == ["point_cloud"]
        return self.device


class DemoTests(unittest.TestCase):
    def test_capture_waits_after_start_and_cleans_up(self):
        device = FakeCamera()
        args = demo.build_parser().parse_args(["capture", "--frames", "2"])
        with patch.object(demo.time, "sleep") as sleep:
            demo.capture_frames(FakeApi(device), args)
        sleep.assert_called_once_with(2.0)
        self.assertEqual(device.calls,
                         ["configure", "start", "get_frame", "get_frame", "stop", "close"])

    def test_frame_failure_still_stops_and_closes(self):
        device = FakeCamera(fail_frame=True)
        args = demo.build_parser().parse_args(["capture", "--startup-delay", "0"])
        with self.assertRaisesRegex(RuntimeError, "frame failed"):
            demo.capture_frames(FakeApi(device), args)
        self.assertEqual(device.calls,
                         ["configure", "start", "get_frame", "stop", "close"])

    def test_invalid_camera_index(self):
        args = demo.build_parser().parse_args(["capture", "--camera-index", "2"])
        with self.assertRaisesRegex(ValueError, "out of range"):
            demo.capture_frames(FakeApi(FakeCamera()), args)


if __name__ == "__main__":
    unittest.main()
