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
