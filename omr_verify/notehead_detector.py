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
