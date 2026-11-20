"""Export reviewed cuts for an editor without altering or importing a timeline."""
import argparse
import csv
from pathlib import Path
from media import read, write, validate_clips, source_path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest',type=Path);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();data=read(a.manifest);clips=validate_clips(data,a.manifest,approved=True)
    if a.out.exists():raise ValueError('Choose a new output folder')
    a.out.mkdir(parents=True)
    rows=[]
    for c in clips:
        rows.append(dict(id=c['id'],source_id=c.get('source_id',''),source_path=str(source_path(c,a.manifest)),
            source_url=c.get('source_url',''),in_seconds=c['start'],out_seconds=c['end'],
            duration_seconds=round(c['end']-c['start'],6),notes=c.get('notes','')))
    with (a.out/'cuts.csv').open('x',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    write(a.out/'cuts.json',{'timestamp_basis':'local source file seconds','clips':rows,'editor_import_tested':False})
    print(f'Wrote {len(rows)} reviewed cuts to {a.out}')


if __name__=='__main__':main()
