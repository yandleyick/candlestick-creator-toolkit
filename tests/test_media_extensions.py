"""Optional OpenCV and Windows OCR integration checks on synthetic input."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_workflows import FF, HAS_FF, ROOT

HAS_CV = importlib.util.find_spec('cv2') is not None


@unittest.skipUnless(HAS_CV and HAS_FF, 'Requires OpenCV and FFmpeg')
class MediaExtensionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='creator-toolkit-extensions-')
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args):
        result = subprocess.run([str(x) for x in args], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr + '\n' + result.stdout)
        return result

    def fixture(self):
        source = self.d / 'blank.mp4'
        self.run_cli(FF, '-v', 'error', '-f', 'lavfi', '-i',
                     'color=c=black:size=320x180:rate=30', '-t', '4',
                     '-c:v', 'libx264', '-threads', '1', '-pix_fmt', 'yuv420p', source)
        return source

    def test_sampler_retains_observed_pts_and_source_offset(self):
        output = self.d / 'sampled'
        self.run_cli(sys.executable, ROOT / 'scripts/overwatch/sample_killfeed.py',
                     self.fixture(), '--out', output, '--start', '1', '--duration', '2',
                     '--source-offset', '100', '--interval', '0.5')
        rows = [json.loads(s) for s in (output / 'samples.jsonl').read_text().splitlines()]
        self.assertEqual(len(rows), 4)
        for i, row in enumerate(rows):
            self.assertAlmostEqual(row['decoded_local_pts'], i * 0.5, places=4)
            self.assertAlmostEqual(row['source_seconds'], 101 + i * 0.5, places=4)
            self.assertTrue(Path(row['path']).is_file())
        self.assertEqual(json.loads((output / 'progress.json').read_text())['phase'], 'sampled')

    def test_restore_preserves_dimensions_depth_and_originals(self):
        import cv2
        import numpy as np
        frames = self.d / 'frames'
        frames.mkdir()
        rng = np.random.default_rng(12)
        originals = {}
        for name, shape, dtype in [('portrait.png', (300, 160, 3), np.uint8),
                                   ('landscape.png', (160, 300, 3), np.uint16)]:
            array = rng.integers(0, np.iinfo(dtype).max, size=shape, dtype=dtype)
            self.assertTrue(cv2.imwrite(str(frames / name), array))
            originals[name] = array
        output = self.d / 'restored'
        self.run_cli(sys.executable, ROOT / 'scripts/restore_frames.py', frames, '--out', output)
        for name, original in originals.items():
            result = cv2.imread(str(output / name), cv2.IMREAD_UNCHANGED)
            self.assertEqual(result.shape, original.shape)
            self.assertEqual(result.dtype, original.dtype)
            self.assertTrue(np.array_equal(cv2.imread(str(frames / name), cv2.IMREAD_UNCHANGED), original))
        self.assertFalse(json.loads((output / 'settings.json').read_text())['visual_approval'])
        repeated = subprocess.run([sys.executable, str(ROOT / 'scripts/restore_frames.py'),
                                   str(frames), '--out', str(output)], capture_output=True, timeout=30)
        self.assertNotEqual(repeated.returncode, 0)

    @unittest.skipUnless(sys.platform == 'win32' and os.environ.get('TEST_WINDOWS_OCR') == '1',
                         'Set TEST_WINDOWS_OCR=1 with the English Windows OCR component installed')
    def test_windows_ocr_blank_video_has_no_kill_events(self):
        output = self.d / 'scanned'
        self.run_cli(sys.executable, ROOT / 'scripts/overwatch/scan_killfeed.py',
                     self.fixture(), '--out', output, '--source-id', 'synthetic-blank',
                     '--name', 'CANDLESTICK', '--start', '1', '--duration', '2', '--source-offset', '100')
        rows = [json.loads(s) for s in (output / 'samples.jsonl').read_text().splitlines()]
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(not row['own_observations'] for row in rows))
        self.assertTrue(all(not row['ocr'].get('error') for row in rows))
        self.assertEqual([row['source_seconds'] for row in rows], [101, 101.5, 102, 102.5])


if __name__ == '__main__':
    unittest.main()
