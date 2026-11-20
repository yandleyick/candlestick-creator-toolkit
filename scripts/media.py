"""Reusable local-media commands. Sources are read-only; outputs must be new."""
import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import subprocess


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write('\n')


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def run(args):
    return subprocess.run([str(v) for v in args], check=True, capture_output=True)


def probe(path, ffprobe=None):
    return json.loads(run([ffprobe or os.environ.get('FFPROBE', 'ffprobe'),
        '-v', 'error', '-show_format', '-show_streams', '-of', 'json', path]).stdout)


def source_path(row, manifest):
    p = Path(row['source_path'])
    return p.resolve() if p.is_absolute() else (Path(manifest).resolve().parent / p).resolve()


def validate_clips(data, manifest, approved=False):
    rows = data['clips']
    if not rows:
        raise ValueError('The clip list is empty')
    seen = set()
    for row in rows:
        ident = row['id']
        if not re.fullmatch(r'[A-Za-z0-9_-]+', ident) or ident in seen:
            raise ValueError(f'Unsafe or duplicate clip id: {ident}')
        seen.add(ident)
        a, b = float(row['start']), float(row['end'])
        if not (math.isfinite(a) and math.isfinite(b) and 0 <= a < b):
            raise ValueError(f'Invalid interval: {ident}')
        if not source_path(row, manifest).is_file():
            raise ValueError(f'Missing source: {ident}')
        if approved and row.get('review_status') != 'approved':
            raise ValueError(f'{ident}: review_status must be approved before export')
    return rows


def qa(path, ffmpeg, ffprobe):
    info = probe(path, ffprobe)
    run([ffmpeg, '-nostdin', '-hide_banner', '-loglevel', 'error', '-xerror',
         '-i', path, '-map', '0:v?', '-map', '0:a?', '-f', 'null', '-'])
    return {'file': str(Path(path).resolve()), 'sha256': digest(path),
            'bytes': Path(path).stat().st_size, 'full_decode': 'passed',
            'probe': info, 'visual_review': 'not performed', 'listening_review': 'not performed'}


def export_clips(a):
    data = read(a.manifest)
    rows = validate_clips(data, a.manifest, approved=True)
    dest = Path(a.out)
    if dest.exists():
        raise ValueError('Choose a new output directory')
    # Preflight all ranges and color before writing any clip.
    for row in rows:
        info = probe(source_path(row, a.manifest), a.ffprobe)
        duration = float(info['format']['duration'])
        if float(row['end']) > duration + 0.05:
            raise ValueError(f"{row['id']}: interval exceeds source duration")
        if any(s.get('color_transfer') in ('smpte2084', 'arib-std-b67') for s in info['streams']):
            raise ValueError('This exporter is for SDR. Prepare a reviewed SDR working copy of HDR sources.')
    dest.mkdir(parents=True)
    summaries = []
    for row in rows:
        src = source_path(row, a.manifest)
        seconds = float(row['end']) - float(row['start'])
        out = dest / (row['id'] + '.mp4')
        temp = out.with_suffix('.partial.mp4')
        info = probe(src, a.ffprobe)
        has_video = any(s['codec_type'] == 'video' for s in info['streams'])
        cmd = [a.ffmpeg, '-nostdin', '-hide_banner', '-loglevel', 'error', '-n']
        if has_video:
            cmd += ['-ss', str(row['start']), '-i', str(src), '-map', '0:v:0', '-map', '0:a:0?']
        else:
            cmd += ['-f', 'lavfi', '-i', 'color=c=0x10151e:s=1280x720:r=30',
                    '-ss', str(row['start']), '-i', str(src), '-map', '0:v:0', '-map', '1:a:0']
        cmd += ['-t', str(seconds), '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1',
                '-c:v', 'libx264', '-preset', 'medium', '-crf', str(a.crf), '-pix_fmt', 'yuv420p',
                '-fps_mode', 'passthrough', '-c:a', 'aac', '-b:a', '192k',
                '-map_metadata', '-1', '-map_chapters', '-1', '-movflags', '+faststart', str(temp)]
        run(cmd)
        result = qa(temp, a.ffmpeg, a.ffprobe)
        actual = float(result['probe']['format']['duration'])
        if abs(actual - seconds) > 0.15:
            raise ValueError(f"{row['id']}: duration mismatch {actual} vs {seconds}")
        temp.rename(out)
        result.update(file=str(out.resolve()), id=row['id'], source_sha256=digest(src),
                      start=row['start'], end=row['end'], command=cmd, selection_review=row['review_status'])
        write(out.with_suffix('.json'), result)
        summaries.append({'id': row['id'], 'file': out.name, 'sha256': result['sha256']})
        print(json.dumps(summaries[-1]), flush=True)
    write(dest/'export-summary.json', {'clips': summaries, 'count': len(summaries)})


def transcribe(a):
    from faster_whisper import WhisperModel
    if Path(a.out).exists():
        raise ValueError('Output already exists')
    model = WhisperModel(a.model, device=a.device, compute_type=a.compute_type)
    segments, info = model.transcribe(str(a.input), language=a.language,
        word_timestamps=True, vad_filter=a.vad, condition_on_previous_text=False, beam_size=5)
    rows = []
    for s in segments:
        rows.append({'start': s.start, 'end': s.end, 'text': s.text,
                     'words': [{'start': w.start, 'end': w.end, 'word': w.word,
                                'confidence': w.probability} for w in s.words or []]})
        print(json.dumps({'processed_seconds': s.end, 'duration': info.duration}), flush=True)
    write(a.out, {'kind': 'automatic working transcript', 'source_path': str(Path(a.input).resolve()),
        'source_id': Path(a.input).stem, 'sha256': digest(a.input), 'model': a.model,
        'duration': info.duration, 'language': info.language, 'segments': rows,
        'limitations': 'Automatic words and boundaries require review. No performer identity is inferred.'})


def candidates(a):
    from phrase_tools import split_passage
    t = read(a.input)
    clips = []
    last_end = 0.0
    for start, end in split_passage(t['segments'], 0, t['duration']):
        start = max(start, last_end)
        if end - start < 20:
            continue
        clips.append({'id': f'candidate-{len(clips)+1:04d}', 'source_id': t['source_id'],
            'source_path': t['source_path'], 'start': start, 'end': end,
            'review_status': 'pending', 'performer': None, 'attribution_basis': None,
            'notes': 'Automatic 20–30 second phrase window; timing and artistic merit are unreviewed.'})
        last_end = end
    write(a.out, {'title': 'Freestyle candidates', 'clips': clips,
        'method': 'Phrase/pause boundaries; not lyrical ranking or proof of improvisation.'})


def timestamp(seconds):
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'


def captions(a):
    t = read(a.input)
    end = a.end if a.end is not None else float('inf')
    rows = []
    for seg in t['segments']:
        if seg['end'] <= a.start or seg['start'] >= end:
            continue
        words = [w for w in seg.get('words', []) if a.start <= (w['start']+w['end'])/2 < end]
        if seg.get('words') and not words:
            continue
        text = ''.join(w['word'] for w in words).strip() if words else seg['text'].strip()
        first = max(a.start, words[0]['start'] if words else seg['start']) - a.start
        last = min(end, words[-1]['end'] if words else seg['end']) - a.start
        if last > first and text:
            rows.append(f'{len(rows)+1}\n{timestamp(first)} --> {timestamp(last)}\n{text}\n')
    with Path(a.out).open('x', encoding='utf-8') as f:
        f.write('\n'.join(rows))


def sheet(a):
    from PIL import Image, ImageDraw
    info = probe(a.input, a.ffprobe)
    duration = float(info['format']['duration'])
    end = min(a.end if a.end is not None else duration, duration)
    if not 0 <= a.start < end or a.count < 1:
        raise ValueError('Invalid sheet interval/count')
    if Path(a.out).exists():
        raise ValueError('Output already exists')
    cols = min(4, a.count)
    canvas = Image.new('RGB', (cols*400, math.ceil(a.count/cols)*255), '#10151e')
    draw = ImageDraw.Draw(canvas)
    seeks = []
    for i in range(a.count):
        t = a.start + (end-a.start)*(i+0.5)/a.count
        raw = run([a.ffmpeg,'-v','error','-ss',str(t),'-i',a.input,'-frames:v','1',
                   '-vf','scale=400:225:force_original_aspect_ratio=decrease','-f','image2pipe','-c:v','png','-']).stdout
        im = Image.open(io.BytesIO(raw)).convert('RGB')
        x, y = i%cols*400, i//cols*255
        canvas.paste(im,(x,y))
        draw.text((x+5,y+232),f'Seek {t:.3f}s',fill='white')
        seeks.append(t)
    canvas.save(a.out)
    write(str(a.out)+'.json',{'source_path':str(Path(a.input).resolve()),'requested_seek_seconds':seeks,
        'limitation':'Overview samples only. Labels are requested seek positions, not frame-accurate event timestamps.'})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ffmpeg', default=os.environ.get('FFMPEG','ffmpeg'))
    p.add_argument('--ffprobe', default=os.environ.get('FFPROBE','ffprobe'))
    sub = p.add_subparsers(dest='command', required=True)
    for name in ('probe','qa'):
        q=sub.add_parser(name);q.add_argument('input',type=Path);q.add_argument('--out',required=True)
    q=sub.add_parser('export');q.add_argument('manifest',type=Path);q.add_argument('--out',required=True);q.add_argument('--crf',type=int,default=18)
    q=sub.add_parser('transcribe');q.add_argument('input',type=Path);q.add_argument('--out',required=True)
    q.add_argument('--model',default='small');q.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    q.add_argument('--compute-type',default='int8');q.add_argument('--language',default='en');q.add_argument('--vad',action='store_true')
    q=sub.add_parser('candidates');q.add_argument('input',type=Path);q.add_argument('--out',required=True)
    q=sub.add_parser('captions');q.add_argument('input',type=Path);q.add_argument('--out',required=True);q.add_argument('--start',type=float,default=0);q.add_argument('--end',type=float)
    q=sub.add_parser('sheet');q.add_argument('input',type=Path);q.add_argument('--out',required=True)
    q.add_argument('--start',type=float,default=0);q.add_argument('--end',type=float);q.add_argument('--count',type=int,default=12)
    a=p.parse_args()
    if a.command=='probe':write(a.out,probe(a.input,a.ffprobe))
    elif a.command=='qa':write(a.out,qa(a.input,a.ffmpeg,a.ffprobe))
    else:{'export':export_clips,'transcribe':transcribe,'candidates':candidates,'captions':captions,'sheet':sheet}[a.command](a)


if __name__=='__main__':
    main()
