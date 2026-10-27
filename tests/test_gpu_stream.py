"""CPU-only checks for the bridge and publication tooling, not CUDA benchmarks."""

import ast
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bridge = load_module("gpu_stream", ROOT / "gpu/gpu_stream.py")
runtime_setup = load_module("prepare_runtime", ROOT / "scripts/prepare_runtime.py")


class BridgeTests(unittest.TestCase):
    def test_leader_log_pattern(self):
        match = bridge.LEADER_RE.search("Leader: POS(1.0,-2.0) SPD=40.0")
        self.assertEqual(tuple(map(float, match.groups())), (1.0, -2.0, 40.0))

    def test_follower_log_with_and_without_direction(self):
        for direction in ("", " [DIR: N]"):
            line = f"[STATE: CRUISE] [POS: 1.0,-10.0] [SPD: 12.0]{direction} [GAP: 10.0]"
            self.assertEqual(bridge.FOLLOWER_RE.search(line).groups(), ("CRUISE", "1.0", "-10.0", "12.0", "10.0"))

    def test_http_round_trip_with_two_followers(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            logs = [directory / name for name in ("leader.log", "follower1.log", "follower2.log")]
            for path in logs:
                path.touch()
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            url = f"http://127.0.0.1:{port}"
            command = [
                sys.executable, "-u", str(ROOT / "gpu/gpu_stream.py"),
                "--leader-log", str(logs[0]),
                "--follower-log", f"1:{logs[1]}",
                "--follower-log", f"2:{logs[2]}",
                "--out", str(directory / "latest.json"),
                "--csv", str(directory / "stream.csv"),
                "--intruder-out", str(directory / "intruder_{id}.txt"),
                "--serve", "--port", str(port),
            ]
            with (directory / "bridge-output.log").open("w+") as output:
                process = subprocess.Popen(command, cwd=ROOT, stdout=output, stderr=output)
                try:
                    self.wait_for(lambda: self.get(url + "/"))
                    # The bridge tails new complete lines rather than replaying old logs.
                    with logs[0].open("a") as file:
                        file.write("Leader: POS(0.0,20.0) SPD=40.0\n")
                    time.sleep(0.15)
                    for fid in (1, 2):
                        with logs[fid].open("a") as file:
                            file.write(f"[STATE: CRUISE] [POS: 0.0,-{fid}.0] [SPD: 39.0] [DIR: N] [GAP: 10.0]\n")
                    payload = self.wait_for(lambda: self.aggregate(url, 2))
                    self.assertEqual(payload["followers"]["2"]["follower_id"], 2)
                    self.assertEqual(payload["followers"]["1"]["leader_speed"], 40.0)

                    body = {"seq": 7, "target_id": 2, "active": True, "speed": 40, "length": 10, "duration_ms": 5000}
                    request = urllib.request.Request(url + "/intruder", json.dumps(body).encode(), {"Content-Type": "application/json"})
                    self.assertEqual(json.loads(self.get(request)), {"ok": True})
                    fields = (directory / "intruder_2.txt").read_text().split()
                    self.assertEqual(fields[:6], ["7", "2", "1", "40", "10", "5000"])
                    self.assertEqual(len(fields), 7)
                    self.assertGreater(float(fields[6]), 0)

                    with self.assertRaises(urllib.error.HTTPError) as error:
                        self.get(urllib.request.Request(url + "/intruder", b"not-json"))
                    self.assertEqual(error.exception.code, 400)
                    error.exception.close()
                    with self.assertRaises(urllib.error.HTTPError) as error:
                        self.get(urllib.request.Request(url + "/missing", b"{}"))
                    self.assertEqual(error.exception.code, 404)
                    error.exception.close()

                    with logs[1].open("a") as file:
                        file.write("[FOLLOWER] Shutdown requested (tcp recv closed)\n")
                    stopped = self.wait_for(lambda: self.disconnected(url))
                    self.assertTrue(stopped["followers"]["1"]["disconnected"])
                    self.assertFalse(stopped["followers"]["2"]["disconnected"])
                finally:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)

    @staticmethod
    def get(request):
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.read()

    def aggregate(self, url, count):
        payload = json.loads(self.get(url + "/latest.json"))
        return payload if len(payload.get("followers", {})) == count else None

    def disconnected(self, url):
        payload = self.aggregate(url, 2)
        return payload if payload and payload["followers"]["1"].get("disconnected") else None

    def wait_for(self, function):
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            try:
                result = function()
                if result:
                    return result
            except (OSError, ValueError):
                pass
            time.sleep(0.05)
        self.fail("Bridge did not produce the expected HTTP result within eight seconds")


class PublicationTests(unittest.TestCase):
    def test_notebook_is_clean_and_syntactically_valid(self):
        notebook = json.loads((ROOT / "gpu/colab_gpu_cruise_demo.ipynb").read_text(encoding="utf-8"))
        self.assertEqual(notebook["nbformat"], 4)
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                self.assertFalse(cell.get("outputs"))
                self.assertIsNone(cell.get("execution_count"))
                ast.parse("".join(cell["source"]))

    def test_python_sources_parse(self):
        for folder in ("gpu", "scripts", "tests"):
            for path in (ROOT / folder).glob("*.py"):
                with self.subTest(path=path.name):
                    ast.parse(path.read_text(encoding="utf-8-sig"))

    def test_prepare_runtime_preserves_existing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "leader.log").write_text("keep me")
            runtime_setup.prepare(directory)
            self.assertEqual((directory / "leader.log").read_text(), "keep me")
            self.assertEqual((directory / "intruder_3.txt").read_text(), "0 3 0 0 0 0 0\n")

    def test_reset_runtime_only_changes_named_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "notes.txt").write_text("keep me")
            (directory / "latest.json").write_text("old data")
            runtime_setup.prepare(directory, reset=True)
            self.assertEqual((directory / "notes.txt").read_text(), "keep me")
            self.assertFalse((directory / "latest.json").exists())
            self.assertEqual((directory / "leader.log").read_text(), "")


if __name__ == "__main__":
    unittest.main()
