"""Calibrated white-letter name fallback; outputs candidates, not verdicts."""
from pathlib import Path
import sys
import cv2
from scan_killfeed import normalize,white_glyph_mask

ROOT=Path(__file__).resolve().parent
THRESHOLD=.62

def load_templates(names):
    result={}
    for alias in names:
        alias=normalize(alias)
        p=ROOT/('name_glyph.png' if alias=='YANDLEYICK' else f'name_glyph_{alias}.png')
        gray_path=ROOT/f'name_gray_{alias}.png'
        gray=gray_path.is_file()
        if gray:p=gray_path
        if p.is_file():
            template=cv2.imread(str(p),0)
            # TM_CCOEFF_NORMED returns 1 everywhere for constant templates.
            # Fail closed before a bad calibration can create fake deaths.
            if template is None or float(template.std()) < (5 if gray else 20):
                raise ValueError(f'Invalid constant/near-constant name template: {p}')
            result[alias]={'image':template,'mode':'gray' if gray else 'white'}
    return result

def find_names(feed,templates,threshold=THRESHOLD):
    white=white_glyph_mask(feed)
    result=[]
    gray=None
    for alias,item in templates.items():
        if isinstance(item,dict):template=item['image'];mode=item['mode']
        else:template=item;mode='white'
        if mode=='gray':
            if gray is None:gray=cv2.cvtColor(feed,cv2.COLOR_BGR2GRAY)
            target=gray
        else:target=white
        h,w=template.shape
        scores=cv2.matchTemplate(target[25:465],template,cv2.TM_CCOEFF_NORMED)
        for _ in range(8):
            _,score,_,(x,y)=cv2.minMaxLoc(scores)
            if score<threshold:break
            result.append({'text':alias,'x':x,'y':y+25,'width':w,'height':h,'name_method':'gray_glyph_fallback' if mode=='gray' else 'glyph_fallback','glyph_score':round(float(score),4)})
            scores[max(0,y-h):min(scores.shape[0],y+h+1),max(0,x-w):min(scores.shape[1],x+w+1)]=-1
    return result

def not_covered(word,observations):
    cy=word['y']+word['height']/2
    return not any(abs(cy-o['row_y'])<15 and abs(word['x']-o['name_box']['x'])<60 for o in observations)
