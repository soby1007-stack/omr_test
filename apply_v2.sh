#!/data/data/com.termux/files/usr/bin/bash
set -e

mkdir -p omr_verify

cat > omr_verify/source_symbols.py <<'PY'
import cv2
import numpy as np

def _components(img):
    n, labels, stats, cent = cv2.connectedComponentsWithStats(img, 8)
    out = []
    for i in range(1, n):
        x,y,w,h,a = stats[i]
        if 3 <= w <= 35 and 3 <= h <= 25 and 12 <= a <= 500:
            out.append((float(cent[i][0]), float(cent[i][1]), w,h,a))
    return out

def detect_noteheads(image_path):
    img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(image_path)

    # 오선 제거
    bw = cv2.threshold(img, 180, 255, cv2.THRESH_BINARY_INV)[1]

    horizontal = cv2.morphologyEx(
        bw, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (35,1))
    )
    clean = cv2.subtract(bw, horizontal)

    raw = _components(clean)

    result = []
    for x,y,w,h,a in raw:
        # notehead에 가까운 타원형/소형 연결성분
        ratio = w / max(h,1)
        if 0.45 <= ratio <= 2.2 and 10 <= a <= 300:
            result.append({
                "x": round(x,2),
                "y": round(y,2),
                "w": int(w),
                "h": int(h),
                "area": int(a)
            })

    return result
PY

cat > omr_verify/match_engine.py <<'PY'
import math

def dist(a,b):
    return math.hypot(a["x"]-b["x"], a["y"]-b["y"])

def match(source, homr, radius=45):
    pairs=[]
    used=set()

    for h in homr:
        best=None
        bestd=radius

        for i,s in enumerate(source):
            if i in used:
                continue
            d=dist(s,h)
            if d < bestd:
                bestd=d
                best=i

        if best is not None:
            used.add(best)
            pairs.append({
                "source_index":best,
                "homr":h,
                "source":source[best],
                "distance":round(bestd,2)
            })

    return pairs

def confidence(pairs, source_count, homr_count):
    if not source_count or not homr_count:
        return 0.0

    coverage=len(pairs)/max(source_count,homr_count)

    if not pairs:
        return 0.0

    avg=sum(x["distance"] for x in pairs)/len(pairs)

    pos=max(0.0,1.0-avg/45.0)

    return round(0.55*coverage + 0.45*pos,3)
PY

cat > omr_verify/auto_verify_v2.py <<'PY'
import json
import sys
from pathlib import Path

from source_symbols import detect_noteheads
from match_engine import match, confidence

def main():
    if len(sys.argv) != 3:
        print("usage: auto_verify_v2.py IMAGE OUTPUT_JSON")
        raise SystemExit(2)

    image=Path(sys.argv[1])
    out=Path(sys.argv[2])

    source=detect_noteheads(image)

    # HOMR 좌표는 현재 자동검증 단계에서 별도 입력으로 연결한다.
    # 여기서는 원본 notehead 후보를 안정적으로 생성한다.
    result={
        "version":2,
        "image":str(image),
        "source_noteheads":source,
        "source_count":len(source),
        "status":"READY_FOR_HOMR_MATCH"
    }

    out.write_text(
        json.dumps(result,ensure_ascii=False,indent=2),
        encoding="utf-8"
    )

    print(f"{image}: {len(source)} source notehead candidates")

if __name__=="__main__":
    main()
PY

cat > omr_verify/build_report.py <<'PY'
import json
import sys
from pathlib import Path

def main():
    root=Path(sys.argv[1])
    out=Path(sys.argv[2])

    rows=[]

    for p in sorted(root.glob("page-*.json")):
        d=json.loads(p.read_text(encoding="utf-8"))
        rows.append({
            "page":p.stem,
            "source_count":d.get("source_count",0),
            "status":d.get("status")
        })

    out.write_text(
        json.dumps({
            "version":2,
            "pages":rows
        },ensure_ascii=False,indent=2),
        encoding="utf-8"
    )

if __name__=="__main__":
    main()
PY

python - <<'PY'
from pathlib import Path

p=Path(".github/workflows/omr-homr.yml")
s=p.read_text()

if "Source notehead verification v2" not in s:
    marker="      - name: Upload final result"
    step="""      - name: Source notehead verification v2
        run: |
          set -e
          mkdir -p output/autoverify-v2

          for img in work/pdf/page-*.png; do
            base=$(basename "$img" .png)
            python omr_verify/auto_verify_v2.py \\
              "$img" \\
              "output/autoverify-v2/${base}.json"
          done

          python omr_verify/build_report.py \\
            output/autoverify-v2 \\
            output/autoverify-v2/report.json

          cat output/autoverify-v2/report.json

"""
    s=s.replace(marker,step+marker)

p.write_text(s)
PY

git add .
git commit -m "Add OMR source notehead verification v2"
git push origin main
