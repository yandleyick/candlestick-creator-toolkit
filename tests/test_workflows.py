"""Catalog consistency and scanner grouping checks."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FF = os.environ.get("FFMPEG", "ffmpeg")
FP = os.environ.get("FFPROBE", "ffprobe")
HAS_FF = bool(shutil.which(FF) and shutil.which(FP))


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="creator-toolkit-")
        self.d = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_python_syntax_and_catalog(self):
        for p in ROOT.rglob('*.py'):
            if '.venv' not in p.parts:ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
        tools=json.loads((ROOT/'catalog/tools.json').read_text())['tools']
        self.assertEqual(len(tools),len({t['id'] for t in tools}))
        self.assertTrue(all(t['url'].startswith('https://') for t in tools))

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
