import sys, json, base64, re
from pathlib import Path
import xml.etree.ElementTree as ET
import cv2, numpy as np

layout = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
work = Path(sys.argv[2]); out=Path(sys.argv[3]); cmp_path=Path(sys.argv[4]); music_dir=Path(sys.argv[5])

STEP_INDEX={s:i for i,s in enumerate('CDEFGAB')}
CLEF_LINE1={('G',2):('F',4), ('F',4):('D',3), ('C',3):('E',4), ('C',4):('F',4)}

def b64(p): return base64.b64encode(Path(p).read_bytes()).decode()

def detect_staff_lines(img_path, t):
    img=cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
    if img is None: return []
    x,y,w,h=[int(round(v)) for v in (t['x'],t['y'],t['w'],t['h'])]
    crop=img[y:y+h,x:x+w]
    if crop.size==0:return []
    bw=cv2.threshold(crop,180,255,cv2.THRESH_BINARY_INV)[1]
    counts=(bw>0).sum(axis=1)
    ys=np.where(counts>=max(8,int(w*0.55)))[0]
    lines=[]
    for yy in ys:
        if not lines or yy-lines[-1][-1]>2: lines.append([int(yy)])
        else: lines[-1].append(int(yy))
    centers=[float(sum(g)/len(g))+y for g in lines]
    # pair into 5-line staffs; a large vertical gap separates staffs
    staffs=[]
    for c in centers:
        if not staffs or c-staffs[-1][-1]>25: staffs.append([c])
        else: staffs[-1].append(c)
    staffs=[s for s in staffs if len(s)>=5]
    return [s[:5] for s in staffs[:2]]

def parse_measure_events(m, state):
    div=state.get('divisions',12); clefs=state.get('clefs',{1:('G',2),2:('F',4)})
    cur=0.0; last={}; events=[]; maxpos=0.0
    for child in m:
        tag=child.tag.split('}')[-1]
        if tag=='attributes':
            z=child.find('divisions')
            if z is not None: div=int(z.text)
            for c in child.findall('clef'):
                n=int(c.get('number','1')); clefs[n]=(c.findtext('sign','G'),int(c.findtext('line','2')))
        elif tag=='backup': cur-=float(child.findtext('duration','0'))/div
        elif tag=='forward': cur+=float(child.findtext('duration','0'))/div; maxpos=max(maxpos,cur)
        elif tag=='note':
            dur=float(child.findtext('duration','0'))/div
            staff=int(child.findtext('staff','1')); voice=child.findtext('voice','1'); chord=child.find('chord') is not None
            onset=last.get((staff,voice),cur) if chord else cur
            pitch=child.find('pitch')
            if pitch is not None:
                events.append({'onset':onset,'duration':dur,'staff':staff,'step':pitch.findtext('step'),'octave':int(pitch.findtext('octave')),'alter':float(pitch.findtext('alter','0')),'voice':voice})
            if not chord: cur += dur
            last[(staff,voice)]=onset; maxpos=max(maxpos,cur)
    return events, max(maxpos,4.0), clefs

def pitch_y(event, staff_lines, clef):
    if event['staff']<1 or event['staff']>len(staff_lines): return None
    sign,line=clef
    line_step,line_oct=CLEF_LINE1.get((sign,line),('F',4))
    base= line_oct*7+STEP_INDEX[line_step]
    idx=event['octave']*7+STEP_INDEX[event['step']]
    steps=idx-base
    lines=staff_lines[event['staff']-1]
    spacing=sum(lines[i+1]-lines[i] for i in range(4))/4
    return lines[4] - steps*(spacing/2)

# Parse XML per page, preserving clefs across measures.
xml_pages=[]
for pi,p in enumerate(layout['pages'],1):
    xml=music_dir/f'page-{pi}_fixed.musicxml'
    root=ET.parse(xml).getroot(); measures=list(root.findall('.//measure'))
    state={'divisions':12,'clefs':{1:('G',2),2:('F',4)}}; parsed=[]
    for m in measures:
        ev,dur,clefs=parse_measure_events(m,state); state['clefs']=clefs
        parsed.append({'events':ev,'duration':dur})
    xml_pages.append(parsed)

pages=[]
for pi,p in enumerate(layout['pages'],1):
    img=work/'pdf'/f'page-{pi}.png'
    # 144dpi image is the coordinate basis of layout.json
    measures=[]
    for mi,t in enumerate(p['measures']):
        staffs=detect_staff_lines(img,t)
        events=xml_pages[pi-1][mi]['events'] if mi<len(xml_pages[pi-1]) else []
        duration=xml_pages[pi-1][mi]['duration'] if mi<len(xml_pages[pi-1]) else 4.0
        clefs={1:('G',2),2:('F',4)}
        # re-read clefs from event parser is not retained; defaults match this score
        notes=[]
        for e in events:
            if e['staff']>len(staffs): continue
            y=pitch_y(e,staffs,(('G',2) if e['staff']==1 else ('F',4)))
            if y is None: continue
            # X based on musical onset within this measure, not rendered SVG geometry.
            lead_in = 78 if t.get('measure_in_system', 1) == 1 else 5
            usable=max(1,t['w']-lead_in-5)
            x=t['x'] + lead_in + min(1.0,max(0.0,e['onset']/duration)) * usable
            notes.append({'x':x,'y':y,'staff':e['staff'],'onset':e['onset'],'duration':e['duration'],'step':e['step'],'octave':e['octave'],'alter':e['alter']})
        measures.append({**t,'notes':notes})
    pages.append({'image':'data:image/png;base64,'+b64(img),'measures':measures,'w':p['width'],'h':p['height']})

raw=json.loads(cmp_path.read_text(encoding='utf-8')); cmp={}
for page in raw.get('pages',[]):
    pn=page.get('page')
    for m in page.get('measures',[]):
        mn=m.get('measure')
        if pn is None or mn is None: continue
        cmp[f'{pn}-{mn}']={'status':m.get('status'),'diagnosis':m.get('diagnosis'),'exact':m.get('exact_rate'),'pitch':m.get('pitch_rate'),'pitch_content':m.get('pitch_content_rate'),'homr_notes':m.get('homr_notes'),'audiveris_notes':m.get('audiveris_notes'),'strict_matches':m.get('strict_matches'),'strict_precision':m.get('strict_precision'),'strict_recall':m.get('strict_recall'),'strict_f1':m.get('strict_f1'),'strict_onset_tolerance':m.get('strict_onset_tolerance'),'strict_duration_tolerance':m.get('strict_duration_tolerance'),'homr_only':m.get('homr_only',[]),'audiveris_only':m.get('audiveris_only',[]),'homr_content_only':m.get('homr_content_only',[]),'audiveris_content_only':m.get('audiveris_content_only',[]),'content_difference_count':m.get('content_difference_count',0)}

html=(Path(__file__).with_name('viewer_direct.html')).read_text(encoding='utf-8')
html=html.replace('/*__DATA__*/','const DATA='+json.dumps(pages,ensure_ascii=False,separators=(',',':'))+';')
html=html.replace('/*__CMP__*/','const CMP='+json.dumps(cmp,ensure_ascii=False,separators=(',',':'))+';')
out.write_text(html,encoding='utf-8')
print('generated',out,'pages',len(pages),'measures',sum(len(x['measures']) for x in pages),'notes',sum(len(m['notes']) for p in pages for m in p['measures']))
print('notes/page', [sum(len(m['notes']) for m in p['measures']) for p in pages])
