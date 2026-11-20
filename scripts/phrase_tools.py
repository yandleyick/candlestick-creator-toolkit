"""Timed excerpt helpers adapted from the freestyle review workflow."""
import re

def sublines(segments, start, end):
    lines = []
    for s in segments:
        if s["end"] <= start or s["start"] >= end:
            continue
        words = [w for w in s.get("words",[]) if start <= (w["start"]+w["end"])/2 < end]
        if words:
            line = ""
            line_start = None
            last = None
            for w in words:
                if line and (w["end"] - line_start > 5.5 or w["start"] - last > 0.8):
                    lines.append({"s":round(max(start,line_start)-start,3),"e":round(min(end,last)-start,3),"t":line.strip()})
                    line=""; line_start=None
                if line_start is None:
                    line_start=w["start"]
                line+=w["word"] if not line or w["word"].startswith(" ") else " "+w["word"]
                last=w["end"]
            if line:
                lines.append({"s":round(max(start,line_start)-start,3),"e":round(min(end,last)-start,3),"t":line.strip()})
        elif not s.get("words") and s.get("text","").strip():
            lines.append({"s":round(max(start,s["start"])-start,3),"e":round(min(end,s["end"])-start,3),"t":s["text"].strip()})
    return lines

def split_passage(segments, start, end):
    words = [w for s in segments for w in s.get("words",[]) if start <= (w["start"]+w["end"])/2 <= end]
    if not words:
        return []
    phrase_end = {round(s["end"],2) for s in segments}
    cuts=[]; i=0
    while i<len(words):
        a=max(start,words[i]["start"]-0.07)
        choices=[]
        for j in range(i,len(words)):
            b=min(end,words[j]["end"]+0.07)
            if b-a>30: break
            if b-a>=20 and j-i>=8:
                gap = min(1.4,max(0,(words[j+1]["start"] if j+1<len(words) else end+.4)-words[j]["end"]))
                boundary = (1.5 if re.search(r"[.!?][\"']?$",words[j]["word"]) else 0)+(.9 if round(words[j]["end"],2) in phrase_end else 0)+gap*1.5
                if j==len(words)-1: boundary+=2
                choices.append((boundary-.085*abs(b-a-25.5),j,b))
        if not choices:
            if end-a < 20: break
            i+=1
            continue
        _,j,b=max(choices);cuts.append((round(a,3),round(b,3)));i=j+1
    return cuts
