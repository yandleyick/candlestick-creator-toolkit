"""Synthetic-fixture checks; no real footage, network, or model downloads."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from media import validate_clips, timestamp

FF=os.environ.get('FFMPEG','ffmpeg')
FP=os.environ.get('FFPROBE','ffprobe')
HAS_FF=bool(shutil.which(FF) or Path(FF).is_file()) and bool(shutil.which(FP) or Path(FP).is_file())


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='creator-toolkit-')
        self.d=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def execute(self,*args,ok=True):
        r=subprocess.run([str(x) for x in args],capture_output=True,text=True)
        if ok:self.assertEqual(r.returncode,0,r.stderr+'\n'+r.stdout)
        else:self.assertNotEqual(r.returncode,0)
        return r
    def cli(self,*args,ok=True):return self.execute(sys.executable,ROOT/'scripts/media.py',*args,ok=ok)
    def fixture(self):
        p=self.d/'source with spaces.mp4'
        self.execute(FF,'-v','error','-f','lavfi','-i','testsrc2=size=320x180:rate=30',
            '-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','4',
            '-c:v','libx264','-threads','1','-pix_fmt','yuv420p','-c:a','aac',p)
        return p
    def manifest(self,source,status='approved'):
        p=self.d/'clips.json';p.write_text(json.dumps({'title':'Synthetic','clips':[{
            'id':'clip-001','source_id':'fixture','source_path':str(source),
            'start':1.0,'end':3.0,'review_status':status,'notes':''}]}))
        return p

    def test_python_syntax_and_catalog(self):
        for p in ROOT.rglob('*.py'):
            if '.venv' not in p.parts:ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
        tools=json.loads((ROOT/'catalog/tools.json').read_text())['tools']
        self.assertEqual(len(tools),len({t['id'] for t in tools}))
        self.assertTrue(all(t['url'].startswith('https://') for t in tools))

    def test_selection_guards(self):
        source=self.d/'source.mp4';source.touch();p=self.manifest(source,'pending');data=json.loads(p.read_text())
        with self.assertRaises(ValueError):validate_clips(data,p,approved=True)
        data['clips'][0]['review_status']='approved'
        self.assertEqual(len(validate_clips(data,p,approved=True)),1)
        for value in (-1,float('nan'),float('inf')):
            data['clips'][0]['start']=value
            with self.assertRaises(ValueError):validate_clips(data,p)
        data['clips'][0]['start']=1;data['clips'][0]['id']='../escape'
        with self.assertRaises(ValueError):validate_clips(data,p)

    def test_transcript_candidates_and_captions(self):
        words=[{'start':i,'end':i+.8,'word':' word.' if i%5==4 else ' word'} for i in range(60)]
        p=self.d/'transcript.json';p.write_text(json.dumps({'source_id':'synthetic','source_path':str(self.d/'input.mp4'),
            'duration':60,'segments':[{'start':0,'end':60,'text':'synthetic words','words':words}]}))
        out=self.d/'candidates.json';self.cli('candidates',p,'--out',out)
        rows=json.loads(out.read_text())['clips'];self.assertGreater(len(rows),0)
        for i,r in enumerate(rows):
            self.assertTrue(20<=r['end']-r['start']<=30)
            self.assertEqual(r['review_status'],'pending')
            if i:self.assertGreaterEqual(r['start'],rows[i-1]['end'])
        srt=self.d/'clip.srt';self.cli('captions',p,'--start','10','--end','15','--out',srt)
        text=srt.read_text();self.assertIn('00:00:00,000 --> 00:00:04,800',text)
        self.assertEqual(timestamp(3661.234),'01:01:01,234')

    @unittest.skipUnless(HAS_FF,'FFmpeg/ffprobe unavailable')
    def test_export_qa_and_no_overwrite(self):
        source=self.fixture();p=self.manifest(source);out=self.d/'render'
        original=source.read_bytes();self.cli('export',p,'--out',out)
        result=json.loads((out/'clip-001.json').read_text())
        self.assertEqual(result['full_decode'],'passed')
        self.assertAlmostEqual(float(result['probe']['format']['duration']),2,delta=.15)
        self.assertTrue(any(s['codec_type']=='audio' for s in result['probe']['streams']))
        self.assertEqual(source.read_bytes(),original)
        exported=(out/'clip-001.mp4').read_bytes()
        self.cli('export',p,'--out',out,ok=False)
        self.assertEqual((out/'clip-001.mp4').read_bytes(),exported)
        self.execute(sys.executable,ROOT/'scripts/handoff.py',p,'--out',self.d/'handoff')
        self.assertTrue((self.d/'handoff/cuts.csv').is_file())

    @unittest.skipUnless(HAS_FF,'FFmpeg/ffprobe unavailable')
    def test_audio_only_and_contact_sheet(self):
        source=self.fixture();self.cli('sheet',source,'--out',self.d/'sheet.jpg','--count','4')
        self.assertTrue((self.d/'sheet.jpg').stat().st_size>100)
        wav=self.d/'source.wav';self.execute(FF,'-v','error','-i',source,'-vn',wav)
        p=self.manifest(wav);self.cli('export',p,'--out',self.d/'audio-render')
        self.assertTrue((self.d/'audio-render/clip-001.mp4').is_file())

    def test_life_grouping_retains_spaced_kills(self):
        spec=importlib.util.spec_from_file_location('lives',ROOT/'scripts/overwatch/build_life_candidates.py')
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        events=[{'id':i,'role':'killer','first_seen':t,'last_seen':t+1,'tracer_feed_score':.9,'self_tracer_nearby':True} for i,t in enumerate((1,3,90))]
        (self.d/'events.json').write_text(json.dumps(events));(self.d/'boundaries.json').write_text('[]')
        mod.build(self.d);r=json.loads((self.d/'life_candidates.json').read_text())
        self.assertEqual(len(r['candidate_lives']),1)
        events.append({'id':3,'role':'victim','first_seen':50,'last_seen':51})
        (self.d/'events.json').write_text(json.dumps(events));mod.build(self.d)
        self.assertEqual(len(json.loads((self.d/'life_candidates.json').read_text())['candidate_lives']),0)

    @unittest.skipUnless(HAS_FF,'FFmpeg/ffprobe unavailable')
    def test_review_routes_range_and_decisions(self):
        import socket
        source=self.fixture();p=self.manifest(source,'pending');dest=self.d/'decisions.json'
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        proc=subprocess.Popen([sys.executable,str(ROOT/'scripts/review.py'),str(p),'--decisions',str(dest),'--port',str(port)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        base=f'http://127.0.0.1:{port}'
        try:
            for _ in range(50):
                try:
                    with urllib.request.urlopen(base+'/catalog',timeout=1) as r:data=json.load(r)
                    break
                except (urllib.error.URLError,ConnectionError):time.sleep(.1)
            else:self.fail('Review server did not start')
            req=urllib.request.Request(base+'/media/0',headers={'Range':'bytes=0-31'})
            with urllib.request.urlopen(req) as r:self.assertEqual(r.status,206);self.assertEqual(len(r.read()),32)
            with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(base+'/media/../secret')
            data['clips'][0]['review_status']='approved'
            payload=json.dumps(data).encode()
            with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(urllib.request.Request(base+'/decisions',data=payload,method='POST'))
            req=urllib.request.Request(base+'/decisions',data=payload,headers={'Origin':base},method='POST')
            with urllib.request.urlopen(req) as r:self.assertEqual(r.status,200)
            self.assertEqual(json.loads(dest.read_text())['clips'][0]['review_status'],'approved')
        finally:
            proc.terminate();proc.communicate(timeout=5)


if __name__=='__main__':unittest.main(verbosity=2)
