import sys, json, itertools
from pathlib import Path
import fitz, cv2, numpy as np

def cluster(vals, gap=12):
    out=[]
    for v in vals:
        if not out or v-out[-1][-1] > gap:
            out.append([v])
        else:
            out[-1].append(v)
    return [sum(g)/len(g) for g in out]

def segments_above(row, threshold):
    ys=np.where(row>threshold)[0]
    out=[]
    if len(ys):
        a=b=int(ys[0])
        for y in ys[1:]:
            y=int(y)
            if y>b+1:
                out.append((a+b)/2)
                a=y
            b=y
        out.append((a+b)/2)
    return out

def detect_page(page, page_index):
    pix=page.get_pixmap(matrix=fitz.Matrix(2,2), alpha=False)
    img=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3)
    gray=cv2.cvtColor(img,cv2.COLOR_RGB2GRAY)
    bw=cv2.threshold(gray,180,255,cv2.THRESH_BINARY_INV)[1]

    # The score's staff lines span ~88% of the page width.  Use a ratio
    # instead of an absolute pixel threshold so the detector is stable.
    h=(bw>0).sum(axis=1)
    line_centers=segments_above(h, pix.width*0.80)
    if len(line_centers)!=60:
        raise RuntimeError(f"page {page_index}: expected 60 staff lines, got {len(line_centers)}")

    staves=[line_centers[i:i+5] for i in range(0,60,5)]
    measures=[]
    for si in range(6):
        upper=staves[2*si]
        lower=staves[2*si+1]
        top=upper[0]-24
        bottom=lower[-1]+24
        y1=max(0,int(upper[0]-3))
        y2=min(pix.height,int(lower[-1]+3))
        v=(bw[y1:y2]>0).sum(axis=0)
        xs=segments_above(v, (y2-y1)*0.72)
        groups=cluster([x for x in xs if x>=60], gap=12)
        if len(groups)>5:
            interior=groups[1:-1]
            choices=[]
            for c in itertools.combinations(interior,3):
                points=[groups[0],*c,groups[-1]]
                gaps=[points[j+1]-points[j] for j in range(4)]
                # Prefer four similarly sized measures; this rejects repeat
                # double-lines that create an extra candidate near the start.
                score=min(gaps)/(max(gaps)+1e-9) - 0.0005*(max(gaps)-min(gaps))
                choices.append((score,points))
            groups=max(choices,key=lambda x:x[0])[1]
        if len(groups)!=5:
            raise RuntimeError(f"page {page_index} system {si+1}: expected 5 bar boundaries, got {groups}")
        for mi in range(4):
            x0,x1=groups[mi],groups[mi+1]
            measures.append({
                "number": si*4+mi+1,
                "x": x0,
                "y": top,
                "w": x1-x0,
                "h": bottom-top,
                "system": si+1,
                "measure_in_system": mi+1,
            })
    return {"width":pix.width,"height":pix.height,"measures":measures}

pdf=fitz.open(sys.argv[1])
pages=[detect_page(p,i+1) for i,p in enumerate(pdf)]
for i,p in enumerate(pages,1):
    if len(p["measures"])!=24:
        raise RuntimeError(f"page {i}: expected 24 measures, got {len(p['measures'])}")
Path(sys.argv[2]).write_text(json.dumps({"pages":pages},ensure_ascii=False,indent=2),encoding="utf-8")
print(f"Detected {len(pages)} page(s), 24 measures per page")
