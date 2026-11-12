"""Loopback-only clip review server. Save/download decisions explicitly."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import re
from urllib.parse import urlparse
from media import read, source_path, validate_clips

HTML = '''<!doctype html><meta charset="utf-8"><title>Clip review</title>
<style>body{background:#12151c;color:#eee;font:16px system-ui;max-width:1100px;margin:30px auto}video{width:100%;max-height:65vh;background:black}button,input,select,textarea{padding:9px;margin:5px;background:#242a35;color:white;border:1px solid #59616c}textarea{width:80%;height:75px}#status{color:#a9d9b5}</style>
<h1>Clip review</h1><p>Watch the full context. Set local-file IN/OUT, label the performer/player, and save decisions.</p>
<select id="pick"></select><span id="status"></span><video id="video" controls></video>
<div>IN <input id="start" type="number" step="0.001"> OUT <input id="end" type="number" step="0.001">
<button id="markin">IN at playhead</button><button id="markout">OUT at playhead</button><button id="play">Play selection</button><label><input type="checkbox" id="stop">Stop at OUT</label></div>
<div>Decision <select id="decision"><option>pending</option><option>approved</option><option>rejected</option></select>
Performer/player <input id="performer"> Attribution basis <input id="basis"></div>
<textarea id="notes" placeholder="Outcome, full encounter, transcription doubts, or edit notes"></textarea>
<div><button id="save">Save local decisions</button><button id="download">Download decisions JSON</button></div>
<script>
const $=id=>document.getElementById(id);let data,index=0;
function stash(){const c=data.clips[index];c.start=Number($('start').value);c.end=Number($('end').value);c.review_status=$('decision').value;c.performer=$('performer').value;c.attribution_basis=$('basis').value;c.notes=$('notes').value;}
function show(){const c=data.clips[index];$('video').src='/media/'+index;$('video').currentTime=Math.max(0,c.start-3);$('start').value=c.start;$('end').value=c.end;$('decision').value=c.review_status||'pending';$('performer').value=c.performer||'';$('basis').value=c.attribution_basis||'';$('notes').value=c.notes||'';}
$('pick').onchange=()=>{stash();index=Number($('pick').value);show()};
$('markin').onclick=()=>{$('start').value=$('video').currentTime.toFixed(3)};
$('markout').onclick=()=>{$('end').value=$('video').currentTime.toFixed(3)};
$('play').onclick=()=>{$('stop').checked=true;$('video').currentTime=Number($('start').value);$('video').play()};
$('video').ontimeupdate=()=>{if($('stop').checked&&$('video').currentTime>=Number($('end').value))$('video').pause()};
$('save').onclick=async()=>{stash();const r=await fetch('/decisions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});$('status').textContent=await r.text()};
$('download').onclick=()=>{stash();const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));a.download='reviewed-clips.json';a.click();URL.revokeObjectURL(a.href)};
fetch('/catalog').then(r=>r.json()).then(d=>{data=d;data.clips.forEach((c,i)=>{const o=document.createElement('option');o.value=i;o.textContent=c.id;$('pick').append(o)});show()});
</script>'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest',type=Path);p.add_argument('--port',type=int,default=8796)
    p.add_argument('--decisions',type=Path,required=True)
    a=p.parse_args();data=read(a.manifest);rows=validate_clips(data,a.manifest)
    # Absolute paths keep a downloaded decisions file valid in a different folder.
    for row in rows:row['source_path']=str(source_path(row,a.manifest))
    source_map={str(i):Path(row['source_path']) for i,row in enumerate(rows)}
    decisions=a.decisions.resolve()
    if decisions==a.manifest.resolve() or decisions in source_map.values():raise ValueError('Decisions must be a separate file')
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def body(self,value,kind='application/json',status=200):
            b=value if isinstance(value,bytes) else value.encode();self.send_response(status)
            self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(b)))
            self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(b)
        def do_GET(self):
            path=urlparse(self.path).path
            if path=='/':return self.body(HTML,'text/html; charset=utf-8')
            if path=='/catalog':return self.body(json.dumps(data))
            if not path.startswith('/media/'):return self.send_error(404)
            src=source_map.get(path[7:])
            if not src:return self.send_error(404)
            size=src.stat().st_size;start,end=0,size-1;status=200
            if self.headers.get('Range'):
                m=re.fullmatch(r'bytes=(\d+)-(\d*)',self.headers['Range'])
                if not m:return self.send_error(416)
                start=int(m[1]);end=min(end,int(m[2])) if m[2] else end;status=206
            if start>end or start>=size:return self.send_error(416)
            self.send_response(status);self.send_header('Content-Type',mimetypes.guess_type(src)[0] or 'application/octet-stream')
            self.send_header('Content-Length',str(end-start+1));self.send_header('Accept-Ranges','bytes')
            if status==206:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
            self.end_headers()
            try:
                with src.open('rb') as f:
                    f.seek(start);remaining=end-start+1
                    while remaining:
                        chunk=f.read(min(1048576,remaining))
                        if not chunk:break
                        self.wfile.write(chunk);remaining-=len(chunk)
            except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass
        def do_POST(self):
            if self.path!='/decisions':return self.send_error(404)
            if self.headers.get('Origin')!=f'http://127.0.0.1:{a.port}':return self.send_error(403)
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=10_000_000:return self.send_error(413)
            try:
                new=json.loads(self.rfile.read(length));changed=validate_clips(new,a.manifest)
                if len(changed)!=len(rows):raise ValueError('Clip count changed')
                for old,row in zip(rows,changed):
                    if old['id']!=row['id'] or old['source_path']!=row['source_path']:raise ValueError('Source/id changed')
                    if row.get('review_status') not in ('pending','approved','rejected'):raise ValueError('Invalid decision')
                decisions.parent.mkdir(parents=True,exist_ok=True)
                temp=decisions.with_suffix('.tmp');temp.write_text(json.dumps(new,indent=2),encoding='utf-8');temp.replace(decisions)
                data.clear();data.update(new)
                self.body('Decisions saved.','text/plain')
            except (ValueError,KeyError,TypeError) as e:self.body(str(e),'text/plain',400)
    print(f'Review: http://127.0.0.1:{a.port} — Ctrl+C to stop',flush=True)
    ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()


if __name__=='__main__':main()
