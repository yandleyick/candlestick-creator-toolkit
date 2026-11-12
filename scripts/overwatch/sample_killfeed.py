"""Read-only video sampling for killfeed evidence; does not classify events.

Keeps actual decoded PTS and logs coverage. No keyframe-only decode, synthetic
fps timestamps, or source modification. Run a calibration window first.
"""
import argparse
import os
import json
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import time

import cv2
import numpy as np

FFMPEG = os.environ.get('FFMPEG', 'ffmpeg')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('video', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--start', type=float, default=0)
    p.add_argument('--duration', type=float)
    p.add_argument('--source-offset', type=float, default=0, help='Original VOD timestamp of this file start')
    p.add_argument('--interval', type=float, default=0.5)
    p.add_argument('--width', type=int, default=1920)
    p.add_argument('--height', type=int, default=1080)
    p.add_argument('--crop', default='768:324:1152:0', help='w:h:x:y after scale')
    p.add_argument('--ffmpeg', default=FFMPEG)
    p.add_argument('--jpeg-quality', type=int, default=94)
    p.add_argument('--full-every', type=float, default=0, help='Save occasional full frames; 0 disables')
    a = p.parse_args()
    if not a.video.is_file():
        p.error('video must be a local file')
    if a.interval <= 0 or a.start < 0 or (a.duration is not None and a.duration <= 0):
        p.error('invalid time range')
    cw, ch, cx, cy = map(int, a.crop.split(':'))
    if min(cw, ch) <= 0 or min(cx, cy) < 0 or cx + cw > a.width or cy + ch > a.height:
        p.error('crop is outside scaled video')
    a.out.mkdir(parents=True, exist_ok=True)
    samples = a.out / 'samples.jsonl'
    if samples.exists():
        p.error('output samples.jsonl already exists; choose a new output directory')
    (a.out / 'feed').mkdir(exist_ok=True)
    if a.full_every:
        (a.out / 'full').mkdir(exist_ok=True)
    cv2.setNumThreads(1)
    selected = f"select='isnan(prev_selected_t)+gte(t-prev_selected_t,{a.interval - 0.00001:.8f})',scale={a.width}:{a.height}"
    pipe_w, pipe_h = a.width, a.height
    if not a.full_every:
        selected += f',crop={a.crop}'
        pipe_w, pipe_h = cw, ch
    selected += ',showinfo'
    cmd = [a.ffmpeg, '-hide_banner', '-loglevel', 'info', '-threads', '2', '-filter_threads', '1']
    if a.start:
        cmd += ['-ss', str(a.start)]
    cmd += ['-i', str(a.video), '-an', '-sn']
    if a.duration is not None:
        cmd += ['-t', str(a.duration)]
    cmd += ['-vf', selected, '-fps_mode', 'passthrough', '-f', 'rawvideo', '-pix_fmt', 'bgr24', 'pipe:1']
    config = {**vars(a), 'video': str(a.video.resolve()), 'out': str(a.out.resolve()), 'method': 'Normal sequential decode; actual selected decoded-frame PTS; visual evidence only', 'command': cmd}
    (a.out / 'config.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
    pts_q = queue.Queue()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    def drain():
        with (a.out / 'decode.log').open('w', encoding='utf-8') as log:
            for raw in proc.stderr:
                line = raw.decode(errors='replace')
                log.write(line)
                match = re.search(r'Parsed_showinfo.*? n:\s*\d+.*?pts_time:([-+\d.eE]+)', line)
                if match:
                    pts_q.put(float(match[1]))
        pts_q.put(None)
    stderr_thread = threading.Thread(target=drain, daemon=True)
    stderr_thread.start()
    count = 0
    first = last = None
    maximum_gap = 0.0
    last_full = -1e30
    started = time.monotonic()
    error = None
    try:
        with samples.open('w', encoding='utf-8') as ledger:
            while True:
                raw = proc.stdout.read(pipe_w * pipe_h * 3)
                if not raw:
                    break
                if len(raw) != pipe_w * pipe_h * 3:
                    raise RuntimeError('Incomplete raw frame')
                pts = pts_q.get(timeout=120)
                if pts is None:
                    raise RuntimeError('Decoded frame has no recorded PTS')
                source_seconds = a.source_offset + a.start + pts
                frame = np.frombuffer(raw, np.uint8).reshape(pipe_h, pipe_w, 3)
                feed = frame[cy:cy+ch, cx:cx+cw] if a.full_every else frame
                stem = f'{count:07d}_{source_seconds:012.3f}'
                path = a.out / 'feed' / (stem + '.jpg')
                if not cv2.imwrite(str(path), feed, [cv2.IMWRITE_JPEG_QUALITY, a.jpeg_quality]):
                    raise RuntimeError(f'Failed saving {path}')
                row = {'sample_index': count, 'source_seconds': round(source_seconds, 6), 'decoded_local_pts': pts, 'path': str(path.resolve())}
                if a.full_every and pts - last_full >= a.full_every - 0.001:
                    full_path = a.out / 'full' / (stem + '.jpg')
                    if not cv2.imwrite(str(full_path), frame, [cv2.IMWRITE_JPEG_QUALITY, a.jpeg_quality]):
                        raise RuntimeError(f'Failed saving {full_path}')
                    row['full_path'] = str(full_path.resolve())
                    last_full = pts
                ledger.write(json.dumps(row) + '\n')
                if first is None:
                    first = source_seconds
                if last is not None:
                    maximum_gap = max(maximum_gap, source_seconds - last)
                last = source_seconds
                count += 1
                if count % 120 == 0:
                    ledger.flush()
                    status = {'phase': 'sampling', 'samples': count, 'source_seconds': last, 'first_source_seconds': first, 'max_actual_gap_seconds': maximum_gap, 'elapsed_seconds': round(time.monotonic()-started, 2)}
                    (a.out / 'progress.json').write_text(json.dumps(status, indent=2), encoding='utf-8')
                    print(json.dumps(status), flush=True)
    except BaseException as ex:
        error = str(ex)
        proc.terminate()
        raise
    finally:
        rc = proc.wait()
        stderr_thread.join(timeout=10)
        final = {'phase': 'sampled' if rc == 0 and error is None else 'failed', 'samples': count, 'first_source_seconds': first, 'last_source_seconds': last, 'max_actual_gap_seconds': maximum_gap, 'ffmpeg_exit': rc, 'error': error, 'elapsed_seconds': round(time.monotonic()-started, 2), 'limitation': 'Sampling alone cannot establish final blows, deaths, or exhaustive coverage. Review attribution and interval gaps.'}
        (a.out / 'progress.json').write_text(json.dumps(final, indent=2), encoding='utf-8')
        print(json.dumps(final), flush=True)
    if rc:
        raise SystemExit(rc)


if __name__ == '__main__':
    main()
