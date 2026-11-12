"""HUD-grounded alias disambiguation; known similar names are not interchangeable."""
import re
from difflib import SequenceMatcher
KNOWN=('YANDLEYICK','CANDLESTICK','FNRGFE','JMCLENDON','TORTAXIDXAMP','WEILAND')
def norm(value):return re.sub('[^A-Z0-9]','',value.upper())
def sim(a,b):return SequenceMatcher(None,norm(a),norm(b)).ratio()
def name_score(text,names,active=None):
    allowed=[active] if active else names
    target=max((sim(text,n) for n in allowed),default=0.)
    other=max((sim(text,n) for n in KNOWN if n not in allowed),default=0.)
    return 0. if other>=.65 and other>target+.05 else target
def hud_identity(words,names):
    matches=[]
    for w in words:
        if not (600<=w['y']<730 and 120<=w['x']<=450 and w['height']>=10):continue
        best=max(names,key=lambda n:sim(w['text'],n))
        score=name_score(w['text'],names)
        if score>=.68:matches.append((score,best))
    return max(matches)[1] if matches else None
