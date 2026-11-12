"""Build review candidates with NO maximum kill spacing.

Only a recognized own-name victim event splits a provisional life. Hero/HUD
absence is retained as uncertainty, never silently used to discard 2+1 kills.
Nothing here adjudicates a final blow or certifies that a death was not missed.
"""
import argparse
import json
from pathlib import Path


def build(scan):
    events=json.loads((scan/'events.json').read_text(encoding='utf-8'))
    if (scan/'identity_rebuilt_events.json').exists():
        rebuilt=json.loads((scan/'identity_rebuilt_events.json').read_text())
        replaced=set(rebuilt['replaced_original_ids'])
        events=[e for e in events if e['id'] not in replaced]+rebuilt['events']
    boundaries=json.loads((scan/'boundaries.json').read_text(encoding='utf-8'))
    manual=json.loads((scan/'manual_findings.json').read_text()) if (scan/'manual_findings.json').exists() else {}
    excluded={eid for finding in manual.get('excluded_candidates',[]) for eid in finding.get('event_ids',[])}
    excluded.update(manual.get('excluded_event_ids',[]))
    identity=json.loads((scan/'identity_audit.json').read_text()) if (scan/'identity_audit.json').exists() else {}
    excluded.update(int(eid[1:]) for eid in identity.get('excluded_event_ids',[]) if eid.startswith('o'))
    lookup={e['id']:e for e in events}
    for i,b in enumerate(manual.get('reviewed_boundaries',[])):
        t=b.get('source_seconds')
        if t is None and b.get('before_event_id') in lookup:t=lookup[b['before_event_id']]['first_seen']-.000001
        if t is not None:events.append(dict(id=f'boundary{i}',role='reviewed_boundary',first_seen=t,last_seen=t,reason=b.get('reason')))
    lives=[]
    life={'life_id':0,'after_death_event':None,'events':[],'ending_death_event':None}
    for event in sorted(events,key=lambda e:(e['first_seen'],str(e['id']))):
        if event['id'] in excluded:continue
        if event['role'] in ('victim','reviewed_boundary'):
            boundary_key='death_event' if event['role']=='victim' else 'phase_boundary'
            life['ending_'+boundary_key]=event['id']
            life['end_seconds']=event['first_seen']
            lives.append(life)
            life={'life_id':len(lives),'after_'+boundary_key:event['id'],'events':[],'ending_death_event':None}
        else:
            life['events'].append(event)
    lives.append(life)
    candidates=[]
    for life in lives:
        events_in_life=life.pop('events')
        strong=[e for e in events_in_life if e['role']=='killer' and e['tracer_feed_score']>=0.63 and e['self_tracer_nearby']]
        possible=[e for e in events_in_life if e['role']=='killer' and e['tracer_feed_score']>=0.50]
        life['strong_candidate_event_ids']=[e['id'] for e in strong]
        life['possible_candidate_event_ids']=[e['id'] for e in possible]
        life['other_own_name_event_ids']=[e['id'] for e in events_in_life if e not in possible]
        life['strong_candidate_count']=len(strong)
        life['possible_candidate_count']=len(possible)
        if possible:
            first=min(e['first_seen'] for e in possible)
            last=max(e['first_seen'] for e in possible)
            life['first_candidate_seconds']=first
            life['last_candidate_seconds']=last
            life['soft_boundaries']=[b for b in boundaries if first<=b['source_seconds']<=last and b['reason']!='own_name_on_victim_side']
            life['possible_merged_rekills']=[e['id'] for e in possible if e['last_seen']-e['first_seen']>8.5]
            life['status']='needs_visual_review'
            life['review_requirements']=['Confirm each big killer name and first Tracer portrait.', 'Exclude assists, deployables, replay/POTG, and other POVs.', 'Check the full span for own death, round transition, hero change, and OCR gaps.', 'Inspect possible repeated same-victim kills after resurrection; the nine-second dedup window can merge them.']
        if len(possible)>=3 or life.get('possible_merged_rekills'):
            candidates.append(life.copy())
    result={'method':'Provisional lives bounded only by recognized own victim events, no maximum time between kills. Soft HUD/hero boundaries do not split lives.', 'lives':lives,'candidate_lives':candidates}
    (scan/'life_candidates.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return {'scan':str(scan),'provisional_lives':len(lives),'candidate_lives':len(candidates),'strong_3plus_lives':sum(l['strong_candidate_count']>=3 for l in candidates)}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('scan',type=Path);a=p.parse_args()
    print(json.dumps(build(a.scan)),flush=True)
