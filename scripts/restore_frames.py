"""Bounded luminance recovery adapted from Natural v3; compare before/after."""
import argparse
from functools import lru_cache
import json
from pathlib import Path
import cv2
import numpy as np

LUMA_BGR = np.array([.0722, .7152, .2126], np.float32)


@lru_cache(maxsize=8)
def recovery_gain(height, width, sigma, regularization, cap):
    fy = np.fft.fftfreq(height).astype(np.float32)[:, None]
    fx = np.fft.fftfreq(width).astype(np.float32)[None, :]
    response = np.exp(-2 * np.pi**2 * sigma**2 * (fx**2 + fy**2))
    inverse = (1 + regularization) * response / (response**2 + regularization)
    # Preserve the original high frequencies and bound the recovery gain.
    gain = 1 + (cap - 1) * np.tanh(np.maximum(inverse - 1, 0) / (cap - 1))
    return np.ascontiguousarray(gain[:, :, None])

def constrained_recovery(luma, sigma=.9, strength=1., regularization=.055, cap=2.25, maximum=.035, local_fraction=.18):
    padded = cv2.copyMakeBorder(luma, 48, 48, 48, 48, cv2.BORDER_REFLECT_101)
    spectrum = cv2.dft(padded, flags=cv2.DFT_COMPLEX_OUTPUT)
    spectrum *= recovery_gain(*padded.shape, sigma, regularization, cap)
    recovered = cv2.idft(spectrum, flags=cv2.DFT_SCALE | cv2.DFT_REAL_OUTPUT)[48:-48, 48:-48]
    correction = (recovered - luma) * strength
    low = cv2.erode(luma, np.ones((5, 5), np.uint8))
    high = cv2.dilate(luma, np.ones((5, 5), np.uint8))
    limit = np.minimum(maximum, .003 + local_fraction * (high - low))
    correction = np.clip(correction, -limit, limit)
    return np.clip(luma + correction, low, high) - luma

def process(image, mode='recovery'):
    height, width = image.shape[:2]
    scale = min(1.0, 1280 / max(height, width))
    small = cv2.resize(image, (max(1, round(width*scale)), max(1, round(height*scale))), interpolation=cv2.INTER_AREA)
    luma = np.sum(small * LUMA_BGR, axis=2)
    if mode == 'gentle':
        delta = constrained_recovery(luma, .75, .7)
    elif mode == 'recovery':
        delta = constrained_recovery(luma, .95, 1.)
    elif mode == 'stronger':
        delta = constrained_recovery(luma, 1.2, 1.15)
    elif mode == 'clarity':
        delta = constrained_recovery(luma, 1.5, 1., .03, 3., .045, .25)
    elif mode == 'softlens':
        delta = constrained_recovery(luma, 1.8, 1., .025, 3.3, .05, .28)
    else:
        raise ValueError(mode)
    delta = cv2.resize(delta, (width, height), interpolation=cv2.INTER_CUBIC)
    return np.clip(image + delta[:, :, None], 0, 1)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('frames',type=Path)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--mode',choices=['gentle','recovery','stronger','clarity','softlens'],default='gentle')
    a=p.parse_args()
    paths=sorted(a.frames.glob('*.png'))
    if not paths:raise ValueError('No PNG frames found')
    if a.out.exists():raise ValueError('Choose a new output folder')
    a.out.mkdir(parents=True)
    for path in paths:
        im=cv2.imread(str(path),cv2.IMREAD_UNCHANGED)
        if im is None or im.dtype not in (np.uint8,np.uint16) or im.ndim!=3 or im.shape[2]!=3:
            raise ValueError(f'Expected an 8/16-bit three-channel PNG: {path.name}')
        maximum=np.iinfo(im.dtype).max
        result=np.rint(process(im.astype(np.float32)/maximum,a.mode)*maximum).astype(im.dtype)
        if not cv2.imwrite(str(a.out/path.name),result):raise RuntimeError(f'Cannot write {path.name}')
    (a.out/'settings.json').write_text(json.dumps({'mode':a.mode,'frames':len(paths),'neural_model':False,'color_conversion':False,'visual_approval':False},indent=2))
    print(f'Processed {len(paths)} frames; compare visually before using.')

if __name__=='__main__':main()
