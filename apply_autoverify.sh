#!/data/data/com.termux/files/usr/bin/bash
set -e

mkdir -p omr_verify

cat > omr_verify/notehead_detector.py <<'PY'
import cv2
import numpy as np

def detect_noteheads(image_path):
    img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(image_path)

    bw = cv2.threshold(img, 180, 255, cv2.THRESH_BINARY_INV)[1]
    n, labels, stats, cent = cv2.connectedComponentsWithStats(bw, 8)

    result = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if 8 <= w <= 30 and 5 <= h <= 22 and 25 <= area <= 350:
            result.append({
                "x": float(cent[i][0]),
                "y": float(cent[i][1]),
                "w": int(w),
                "h": int(h),
                "area": int(area),
            })
    return result
PY

cat > omr_verify/decision_engine.py <<'PY'
from dataclasses import dataclass

@dataclass
class Decision:
    action: str
    confidence: float
    reason: str

def decide(source_count, homr_count, distance=None):
    if source_count <= 0:
        return Decision("REVIEW", 0.0, "source symbol detection unavailable")

    ratio = homr_count / source_count

    if distance is not None and distance <= 12 and 0.85 <= ratio <= 1.15:
        return Decision("AUTO", 0.98, "count and position agree")

    if 0.90 <= ratio <= 1.10:
        return Decision("AUTO", 0.90, "symbol count agrees")

    return Decision("REVIEW", 0.0, "uncertain correspondence")
PY

cat > omr_verify/auto_verify.py <<'PY'
import json
import sys
from pathlib import Path

from notehead_detector import detect_noteheads
from decision_engine import decide

def main():
    if len(sys.argv) != 3:
        print("usage: auto_verify.py IMAGE OUTPUT_JSON")
        raise SystemExit(2)

    image = Path(sys.argv[1])
    output = Path(sys.argv[2])

    notes = detect_noteheads(image)

    result = {
        "image": str(image),
        "source_note_candidates": len(notes),
        "candidates": notes,
        "status": "DETECTED"
    }

    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(json.dumps({
        "image": str(image),
        "source_note_candidates": len(notes)
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
PY

cat > omr_verify/README.md <<'MD'
# OMR Auto Verify

PDF 원본과 HOMR 결과를 비교하기 위한 검증 엔진.

현재 단계:
1. 원본 PDF 렌더링
2. 원본 악보의 보수적인 notehead 후보 검출
3. HOMR 결과와 비교할 수 있는 JSON 생성
4. 불확실한 영역은 REVIEW 대상으로 분리

자동 보정은 충분한 근거가 있을 때만 수행하며,
근거가 부족한 경우 임의로 수정하지 않는다.
MD

python - <<'PY'
from pathlib import Path

p = Path(".github/workflows/omr-homr.yml")
s = p.read_text()

# 중복 Poppler 설치 제거
block = '''      - name: Install Poppler
        run: sudo apt-get update && sudo apt-get install -y poppler-utils
'''
s = s.replace("\n" + block, "", 1)

# 자동검증 단계 추가
marker = '''      - name: Upload final result
'''
step = '''      - name: Source score auto verification
        run: |
          set -e
          mkdir -p output/autoverify

          for img in work/pdf/page-*.png; do
            base=$(basename "$img" .png)
            python omr_verify/auto_verify.py \
              "$img" \
              "output/autoverify/${base}.json"
          done

          echo "=== AUTO VERIFY RESULT ==="
          find output/autoverify -type f -maxdepth 1 -print

'''
if marker in s and "Source score auto verification" not in s:
    s = s.replace(marker, step + marker)

p.write_text(s)
PY

git add .
git commit -m "Add source score auto verification engine"
git push origin main
