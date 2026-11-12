"""Check catalog URL reachability; a reachable site is not a safety endorsement."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import urllib.error
import urllib.request

def check(item):
    url=item['url']
    try:
        request=urllib.request.Request(url,headers={'User-Agent':'CreatorToolkit-LinkCheck/1.0'},method='HEAD')
        with urllib.request.urlopen(request,timeout=15) as r:
            return {'id':item['id'],'url':url,'status':r.status,'result':'reachable'}
    except urllib.error.HTTPError as e:
        return {'id':item['id'],'url':url,'status':e.code,'result':'manual check needed; HEAD may be blocked'}
    except Exception as e:
        return {'id':item['id'],'url':url,'status':None,'result':type(e).__name__}

def main():
    p=argparse.ArgumentParser();p.add_argument('--catalog',type=Path,default=Path(__file__).resolve().parents[1]/'catalog/tools.json');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('Output already exists')
    data=json.loads(a.catalog.read_text(encoding='utf-8'))
    with ThreadPoolExecutor(max_workers=8) as pool:rows=list(pool.map(check,data['tools']))
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps({'method':'HEAD requests; errors are not definitive evidence that a site is down','results':rows},indent=2),encoding='utf-8')
    print(json.dumps({'checked':len(rows),'reachable':sum(r['result']=='reachable' for r in rows),'manual_check':sum(r['result']!='reachable' for r in rows)}))

if __name__=='__main__':main()
