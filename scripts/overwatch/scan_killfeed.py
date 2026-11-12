"""Sequential 2-fps OCR/CV triage with retained evidence, not adjudicated kills.

Raw frames stay in memory. OCR records and source PTS are retained for every
sample; only own-name observations and sparse context frames become JPEGs.
Review candidate groups for hero attribution, entities, replay and life bounds.
"""
import argparse
import os
import base64
from difflib import SequenceMatcher
import json
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import time
import unicodedata

import cv2
import numpy as np
from sample_killfeed import FFMPEG

TOOLS = Path(__file__).resolve().parent


def normalize(text):
    return re.sub('[^A-Z0-9]', '', unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().upper()).replace('1', 'I').replace('0', 'O')


def similarity(text, name):
    text = normalize(text)
    if len(text) < 5:
        return 0
    return SequenceMatcher(None, text, name).ratio()


def score_template(image, template):
    if min(image.shape[:2]) < min(template.shape[:2]) or image.shape[0] < template.shape[0] or image.shape[1] < template.shape[1]:
        return 0.0, (0, 0)
    _, maximum, _, xy = cv2.minMaxLoc(cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED))
    return float(maximum), xy


def white_glyph_mask(image):
    blue,green,red=cv2.split(image)
    low=cv2.min(cv2.min(blue,green),red)
    high=cv2.max(cv2.max(blue,green),red)
    return cv2.bitwise_and(cv2.compare(low,160,cv2.CMP_GT),cv2.compare(cv2.subtract(high,low),75,cv2.CMP_LT))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('video', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--source-id', required=True)
    p.add_argument('--name', required=True,help='Comma-separated observed player aliases, if a VOD changes account/name')
    p.add_argument('--start', type=float, default=0)
    p.add_argument('--duration', type=float)
    p.add_argument('--source-offset', type=float, default=0)
    p.add_argument('--interval', type=float, default=0.5)
    p.add_argument('--context-interval', type=float, default=15)
    p.add_argument('--ffmpeg', default=FFMPEG)
    p.add_argument('--ffprobe', default=os.environ.get('FFPROBE', 'ffprobe'))
    p.add_argument('--cuda', action='store_true', help='Use NVDEC/CUDA for decode/scale; verify calibration first')
    p.add_argument('--decode-threads', type=int, default=2)
    p.add_argument('--decode-policy', default=str(TOOLS / 'decode_launch_policy.json'),
                   help='Optional exact-job decode settings for workers still waiting in the queue')
    p.add_argument('--fast-name-gate', action='store_true', help='Calibrated player-name glyph search each sample; OCR on matches plus a 5s heartbeat')
    p.add_argument('--name-template',type=Path,help='Explicit calibrated binary white-glyph template for the requested player')
    a = p.parse_args()
    a.decode_policy_applied = None
    policy_path = Path(a.decode_policy)
    if policy_path.is_file():
        rules = json.loads(policy_path.read_text(encoding='utf-8')).get('rules', [])
        matches = [r for r in rules if r['source_id'] == a.source_id
                   and abs(float(r['start']) - a.start) < .000001
                   and str(Path(r['out']).resolve()).casefold() == str(a.out.resolve()).casefold()]
        if len(matches) > 1:
            p.error('multiple decode policies match this exact job')
        if matches:
            rule = matches[0]
            a.cuda = bool(rule['cuda'])
            a.decode_threads = int(rule['decode_threads'])
            a.decode_policy_applied = rule
    from glyph_names import load_templates,find_names
    from identity_tools import name_score,hud_identity
    if not a.video.is_file(): p.error('input must be a local video')
    if a.interval <= 0 or a.start < 0 or (a.duration is not None and a.duration <= 0): p.error('invalid time range')
    if a.decode_threads < 1: p.error('decode threads must be positive')
    a.out.mkdir(parents=True, exist_ok=True)
    if (a.out / 'samples.jsonl').exists(): p.error('choose a fresh output directory; existing evidence is never overwritten')
    for directory in ('evidence', 'context'):
        (a.out / directory).mkdir(exist_ok=True)
    probe=subprocess.run([a.ffprobe,'-v','error','-select_streams','v:0','-show_entries','stream=start_time,duration,r_frame_rate','-of','json',str(a.video)],capture_output=True,text=True,check=True)
    stream=json.loads(probe.stdout)['streams'][0]
    video_end=float(stream.get('start_time',0))+float(stream['duration'])
    expected_end=a.source_offset+min(video_end,a.start+a.duration if a.duration else video_end)
    rate_n,rate_d=map(float,stream.get('r_frame_rate','0/1').split('/'))
    end_tolerance=max(a.interval+0.1,rate_d/rate_n+0.1 if rate_n else 2.1,1.1)
    cv2.setNumThreads(1)
    names = [normalize(value) for value in a.name.split(',') if value.strip()]
    active_alias=None
    active_alias_time=-1e30
    glyph_templates=load_templates(names)
    if not names: p.error('at least one player alias is required')
    name = names[0]
    def player_score(text):
        return max(similarity(text,alias) for alias in names)
    hud_template = cv2.imread(str(TOOLS / 'tracer_hud.png'))
    hud_template_paths=[TOOLS/'tracer_hud.png']+sorted(TOOLS.glob('tracer_hud_*.png'))
    hud_templates=[cv2.imread(str(path)) for path in hud_template_paths]
    feed_template = cv2.imread(str(TOOLS / 'tracer_feed.png'))
    if hud_template is None or feed_template is None: p.error('calibrated templates are missing')
    feed_templates = [cv2.resize(feed_template, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) for s in (0.9, 1.0, 1.1)]
    name_template_path=a.name_template or (TOOLS/('name_glyph.png' if name=='YANDLEYICK' else f'name_glyph_{name}.png'))
    name_template = cv2.imread(str(name_template_path), cv2.IMREAD_GRAYSCALE) if name_template_path.is_file() else None
    if a.fast_name_gate and any(n not in glyph_templates for n in names): p.error('fast gate requires calibrated glyph templates for every alias')
    ocr_err = (a.out / 'ocr.stderr.log').open('w', encoding='utf-8')
    ocr = subprocess.Popen(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(TOOLS / 'ocr_server.ps1')], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=ocr_err, text=True, encoding='utf-8', bufsize=1)
    greeting = ocr.stdout.readline()
    if not greeting or not json.loads(greeting).get('ready'): raise RuntimeError('OCR server failed to initialize')
    cmd = [a.ffmpeg, '-hide_banner', '-loglevel', 'info', '-xerror', '-threads', str(a.decode_threads), '-filter_threads', '1']
    if a.cuda: cmd += ['-hwaccel','cuda','-hwaccel_output_format','cuda']
    if a.start: cmd += ['-ss', str(a.start)]
    cmd += ['-i', str(a.video), '-an', '-sn']
    if a.duration: cmd += ['-t', str(a.duration)]
    scale_filter='scale_cuda=1920:1080,hwdownload,format=nv12,format=bgr24' if a.cuda else 'scale=1920:1080'
    # Preserve input-relative timestamps through dynamic stream reconfiguration.
    # STARTPTS resets on filter reinit and vfr may silently drop those frames.
    trim_filter=f'trim=duration={a.duration},' if a.duration else ''
    cmd += ['-vf', f"{trim_filter}select='isnan(prev_selected_t)+gte(t-prev_selected_t,{a.interval-0.00001:.8f})',{scale_filter},showinfo", '-fps_mode', 'passthrough', '-f', 'rawvideo', '-pix_fmt', 'bgr24', 'pipe:1']
    config = {**vars(a), 'video': str(a.video.resolve()), 'out': str(a.out.resolve()), 'name_template':str(name_template_path), 'command': cmd,
              'method': 'Normal sequential decode and actual selected PTS. Every-frame OCR, or (with fast-name-gate) dense calibrated name-glyph CV plus OCR on glyph matches and 5s heartbeat; every OCR result retained. Own large killer name + first hero portrait is a candidate final blow; victim name is a death boundary. No assists counted from small portraits.',
              'limitations': ['All groups require visual review.', 'OCR misses, displaced/occluded feed, deployables and replay/POTG remain review risks.', 'Sampled timestamps are observation times, not exact event frames.'],
              'templates': {'feed': str(TOOLS/'tracer_feed.png'), 'hud': str(TOOLS/'tracer_hud.png'),'hud_alternates':[str(path) for path in hud_template_paths]}, 'glyph_fallback':{'aliases':list(glyph_templates),'threshold':0.62,'purpose':'Recover calibrated large names omitted by OCR; all results still require visual review.'}}
    (a.out / 'config.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    pts_q = queue.Queue()
    def drain():
        with (a.out / 'decode.log').open('w', encoding='utf-8') as log:
            for raw in proc.stderr:
                line = raw.decode(errors='replace'); log.write(line)
                match = re.search(r'Parsed_showinfo.*? n:\s*\d+.*?pts_time:([-+\d.eE]+)', line)
                if match: pts_q.put(float(match[1]))
        pts_q.put(None)
    thread = threading.Thread(target=drain, daemon=True); thread.start()
    started = time.monotonic()
    count = ocr_errors = own_observations = 0
    ocr_frames = 0
    last_ocr_t = -1e30
    last_ocr_own_hud = False
    first = last = None
    max_gap = 0.0
    events = []
    recent_events = []
    last_context = -1e30
    last_self_tracer = -1e30
    not_tracer_since = None
    other_hero_boundary_active = False
    absent_boundary_active = False
    boundary_last = -1e30
    boundaries = []
    group_id = 0
    failure = None
    timing_audit = {'expected_end_seconds':expected_end,'negative_pts_count':0,'zero_pts_count':0,'filter_reconfig_count':None,'logged_selected_frames':None,'timing_validated':False}

    def boundary(t, reason):
        nonlocal group_id, boundary_last
        if t - boundary_last > 1:
            group_id += 1; boundary_last = t
            boundaries.append({'source_seconds': t, 'reason': reason, 'new_group': group_id})

    def write_summary(phase):
        qualified = [e for e in events if e['role']=='killer' and e['tracer_feed_score'] >= 0.63 and e['self_tracer_nearby']]
        groups = []
        for gid in sorted({e['group'] for e in qualified}):
            rows = [e for e in qualified if e['group']==gid]
            if len(rows) >= 3:
                groups.append({'group': gid, 'first_observation_seconds': min(e['first_seen'] for e in rows), 'last_observation_seconds': max(e['first_seen'] for e in rows), 'candidate_final_blows':len(rows), 'event_ids':[e['id'] for e in rows], 'status':'needs_visual_review', 'limitation':'Automated grouping; verify no missed death/round reset, replay, deployable or duplicated event.'})
        progress = {'source_id': a.source_id, 'phase': phase, 'samples': count, 'ocr_frames': ocr_frames, 'fast_name_gate':a.fast_name_gate, 'first_source_seconds': first, 'last_source_seconds': last, 'max_actual_gap_seconds': round(max_gap, 6), 'ocr_errors': ocr_errors, 'own_observations': own_observations, 'deduplicated_own_events': len(events), 'candidate_tracer_final_blows': len(qualified), 'candidate_3plus_groups': len(groups), 'elapsed_seconds': round(time.monotonic()-started, 2), 'failure': failure,'timing_audit':timing_audit}
        (a.out/'progress.json').write_text(json.dumps(progress, indent=2), encoding='utf-8')
        (a.out/'events.json').write_text(json.dumps(events, indent=2), encoding='utf-8')
        (a.out/'boundaries.json').write_text(json.dumps(boundaries, indent=2), encoding='utf-8')
        (a.out/'candidate_groups.json').write_text(json.dumps(groups, indent=2), encoding='utf-8')
        return progress

    try:
        with (a.out/'samples.jsonl').open('w', encoding='utf-8') as ledger:
            while True:
                raw = proc.stdout.read(1920*1080*3)
                if not raw: break
                if len(raw) != 1920*1080*3: raise RuntimeError('incomplete decoded frame')
                pts = pts_q.get(timeout=120)
                if pts is None: raise RuntimeError('missing decoded PTS')
                t = round(a.source_offset+a.start+pts, 6)
                frame = np.frombuffer(raw, np.uint8).reshape(1080,1920,3)
                feed = frame[:480,1152:1920]
                glyph_hits=find_names(feed,glyph_templates,.35)
                name_gate_score=max([g['glyph_score'] for g in glyph_hits],default=0.0)
                use_ocr=(not a.fast_name_gate or name_gate_score>=0.35 or t-last_ocr_t>=5)
                # OCR sees feed plus isolated own HUD. Word coordinates >=480
                # belong to the HUD and can never become killfeed events.
                if use_ocr:
                    packed = np.zeros((740,768,3), dtype=np.uint8)
                    packed[:480] = feed
                    packed[480:740,:500] = frame[820:1080,:500]
                    ok, encoded = cv2.imencode('.jpg', packed, [cv2.IMWRITE_JPEG_QUALITY,95])
                    if not ok: raise RuntimeError('JPEG encoding failed')
                    ocr.stdin.write(json.dumps({'id':count,'image':base64.b64encode(encoded).decode()})+'\n'); ocr.stdin.flush()
                    reply = ocr.stdout.readline()
                    if not reply: raise RuntimeError('OCR server exited')
                    record = json.loads(reply); ocr_frames+=1; last_ocr_t=t
                else:
                    record={'id':count,'words':[],'text':'','error':None,'skipped':'name_glyph_below_0.35_between_5s_heartbeats'}
                if record.get('error'): ocr_errors += 1
                words = record.get('words', [])
                hud_score = max(score_template(frame[850:1030,:190], template)[0] for template in hud_templates if template is not None)
                if use_ocr:
                    observed_alias=hud_identity(words,names)
                    last_ocr_own_hud=observed_alias is not None
                    if observed_alias is not None:active_alias=observed_alias;active_alias_time=t
                if t-active_alias_time>30:active_alias=None
                own_hud = last_ocr_own_hud
                own_tracer = own_hud and hud_score >= 0.70
                if own_tracer:
                    last_self_tracer = t; not_tracer_since = None
                    other_hero_boundary_active = False
                    absent_boundary_active = False
                elif own_hud and hud_score < 0.55:
                    if not_tracer_since is None: not_tracer_since = t
                    if t-not_tracer_since>=2 and not other_hero_boundary_active:
                        boundary(t,'observed_other_hero')
                        other_hero_boundary_active = True
                # A long absence of recognizable own Tracer breaks grouping
                # conservatively; sparse contexts allow reviewing such splits.
                if t-last_self_tracer > 20 and not absent_boundary_active:
                    boundary(t,'own_tracer_absent_20s')
                    absent_boundary_active = True
                fw = [w for w in words if 25<=w['y']<465]
                own = [w for w in fw if 8<=w['height']<=30 and name_score(w['text'],names,active_alias)>=0.65]
                for glyph in [g for g in glyph_hits if g['glyph_score']>=.62]:
                    if active_alias is not None and glyph['text']!=active_alias:continue
                    if not any(abs(glyph['y']+glyph['height']/2-w['y']-w['height']/2)<15 and abs(glyph['x']-w['x'])<60 for w in own):own.append(glyph)
                observations = []
                for w in own:
                    center = w['y']+w['height']/2
                    row_words = [other for other in fw if abs(other['y']+other['height']/2-center)<14 and other is not w]
                    right = [other for other in row_words if other['x']>w['x']+w['width']+70 and other['x']>550]
                    if w['x']>=560 and w['x']+w['width']>=685:
                        role='victim'
                        counterpart=' '.join(other['text'] for other in sorted(row_words,key=lambda z:z['x']) if other['x']<w['x']-55)
                    elif w['x']+w['width']<565:
                        role='killer'
                        counterpart=' '.join(other['text'] for other in sorted(right,key=lambda z:z['x']))
                    else:
                        role='uncertain'; counterpart=' '.join(other['text'] for other in row_words)
                    endpoint=int(w['x']+w['width'])
                    y0=max(0,int(center)-24); y1=min(480,int(center)+24)
                    x0=max(0,endpoint-1); x1=min(768,endpoint+72)
                    crop=feed[y0:y1,x0:x1]
                    feed_score=0.0
                    if role=='killer':
                        for template in feed_templates:
                            value, xy=score_template(crop,template)
                            if xy[0]<=30: feed_score=max(feed_score,value)
                    observations.append({'name_text':w['text'],'name_method':w.get('name_method','ocr'),'glyph_score':w.get('glyph_score'),'player_alias':max(names,key=lambda alias:similarity(w['text'],alias)),'name_similarity':round(player_score(w['text']),3),'role':role,'counterpart_text':counterpart,'tracer_feed_score':round(feed_score,4),'row_y':round(center,2),'name_box':{k:w[k] for k in ('x','y','width','height')}})
                # Feed stacks newest events above older ones; process bottom up
                # so a simultaneous sampled death follows preceding final blows.
                matched_this_frame=set()
                for observation in sorted(observations,key=lambda o:-o['row_y']):
                    own_observations += 1
                    counterpart=normalize(observation['counterpart_text'])
                    candidates=[]
                    for event in recent_events:
                        if event['id'] in matched_this_frame: continue
                        if event['role']!=observation['role'] or t-event['last_seen']>3 or t-event['first_seen']>9: continue
                        old=normalize(event['counterpart_text'])
                        sim=SequenceMatcher(None,counterpart,old).ratio() if counterpart and old else 0.5
                        dy=observation['row_y']-event.get('last_row_y',observation['row_y'])
                        dx=observation['name_box']['x']-event.get('last_name_x',observation['name_box']['x'])
                        if dy < -20 or dy > 130: continue
                        # A new top row must not inherit an earlier unnamed kill.
                        # Blank text is useful only with close spatial/temporal support.
                        if not counterpart or not old:
                            if abs(dy)>20 or abs(dx)>16 or t-event['last_seen']>1.0:continue
                        if sim>=0.65 or (sim==0.5 and (not counterpart or not old)):
                            candidates.append((sim-abs(dy)*.0001,event))
                    if candidates:
                        event=max(candidates,key=lambda z:z[0])[1]
                    else:
                        event={'id':len(events),'group':group_id,'role':observation['role'],'player_alias':observation['player_alias'],'counterpart_text':observation['counterpart_text'],'first_seen':t,'last_seen':t,'observations':0,'tracer_feed_score':0.0,'self_tracer_nearby':False,'max_hud_tracer_score':0.0,'evidence':[],'status':'unverified_event'}
                        events.append(event); recent_events.append(event)
                        if observation['role']=='victim': boundary(t,'own_name_on_victim_side')
                    event['last_seen']=t; event['observations']+=1
                    event['last_row_y']=observation['row_y'];event['last_name_x']=observation['name_box']['x']
                    if len(observation['counterpart_text'])>len(event['counterpart_text']): event['counterpart_text']=observation['counterpart_text']
                    old_score=event['tracer_feed_score']
                    event['tracer_feed_score']=max(old_score,observation['tracer_feed_score'])
                    event['self_tracer_nearby'] |= bool(t-last_self_tracer<=8)
                    event['max_hud_tracer_score']=max(event['max_hud_tracer_score'],round(hud_score,4))
                    if len(event['evidence'])==0 or (len(event['evidence'])<3 and observation['tracer_feed_score']>old_score+0.03):
                        stem=f"e{event['id']:05d}_{t:012.3f}"
                        path=a.out/'evidence'/f'{stem}_feed.jpg'
                        full=a.out/'evidence'/f'{stem}_full.jpg'
                        cv2.imwrite(str(path),feed,[cv2.IMWRITE_JPEG_QUALITY,96])
                        cv2.imwrite(str(full),frame,[cv2.IMWRITE_JPEG_QUALITY,91])
                        event['evidence'].append({'source_seconds':t,'feed':str(path),'full':str(full)})
                    observation['event_id']=event['id']
                    matched_this_frame.add(event['id'])
                recent_events=[e for e in recent_events if t-e['last_seen']<=9]
                if t-last_context>=a.context_interval:
                    context=a.out/'context'/f'{t:012.3f}.jpg'
                    cv2.imwrite(str(context),cv2.resize(frame,(960,540)),[cv2.IMWRITE_JPEG_QUALITY,75]);last_context=t
                row={'sample_index':count,'source_seconds':t,'local_pts':pts,'hud_tracer_score':round(hud_score,4),'own_hud_name':own_hud,'active_alias':active_alias,'hud_name_cached':not use_ocr,'name_glyph_score':round(name_gate_score,4) if name_gate_score is not None else None,'own_tracer':own_tracer,'group':group_id,'own_observations':observations,'ocr':record}
                ledger.write(json.dumps(row,separators=(',',':'))+'\n')
                if first is None: first=t
                if last is not None:
                    max_gap=max(max_gap,t-last)
                    if t<last: timing_audit['negative_pts_count']+=1
                    if t==last: timing_audit['zero_pts_count']+=1
                last=t;count+=1
                if count%120==0:
                    ledger.flush();print(json.dumps(write_summary('scanning')),flush=True)
    except BaseException as error:
        failure=str(error);proc.terminate();raise
    finally:
        rc=proc.wait();thread.join(timeout=5)
        try: ocr.stdin.close()
        except Exception: pass
        ocr.wait(timeout=15);ocr_err.close()
        if rc and failure is None: failure=f'FFmpeg exited {rc}'
        decode_text=(a.out/'decode.log').read_text(encoding='utf-8',errors='replace')
        timing_audit['filter_reconfig_count']=decode_text.count('Reconfiguring filter graph')
        timing_audit['logged_selected_frames']=len(re.findall(r'Parsed_showinfo.*? n:\s*\d+.*?pts_time:([-+\d.eE]+)',decode_text))
        timing_audit['timing_validated']=bool(count and timing_audit['negative_pts_count']==0 and timing_audit['zero_pts_count']==0 and timing_audit['logged_selected_frames']==count and last+end_tolerance>=expected_end)
        if failure is None and not timing_audit['timing_validated']:
            failure='Timing/coverage audit did not pass; inspect logged-vs-output frame count, timestamp monotonicity and expected end'
        print(json.dumps(write_summary('sampled_needs_review' if rc==0 and failure is None else 'failed')),flush=True)
    if rc or failure: raise SystemExit(rc or 1)


if __name__=='__main__': main()
