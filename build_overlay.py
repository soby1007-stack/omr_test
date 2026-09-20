import sys, json, base64, re
from pathlib import Path

layout = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
work = Path(sys.argv[2])
out = Path(sys.argv[3])
cmp_path = Path(sys.argv[4]) if len(sys.argv) > 4 else None

def b64(p):
    return base64.b64encode(Path(p).read_bytes()).decode()

pages = []
for i, p in enumerate(layout["pages"], 1):
    svgs = []
    d = work / f"svg-source-{i}"
    for f in sorted(d.glob("page-*.svg"), key=lambda x: int(re.search(r"page-(\d+)", x.name).group(1))):
        svgs.append(f.read_text(encoding="utf-8"))
    pages.append({
        "image": "data:image/png;base64," + b64(work / "300" / f"page-{i}.png"),
        "svgs": svgs,
        "measures": p["measures"],
        "w": p["width"],
        "h": p["height"],
    })

cmp = {}
if cmp_path and cmp_path.exists():
    raw = json.loads(cmp_path.read_text(encoding="utf-8"))
    for page in raw.get("pages", []):
        pn = page.get("page")
        for m in page.get("measures", []):
            mn = m.get("measure")
            if pn is None or mn is None:
                continue
            cmp[f"{pn}-{mn}"] = {
                "status": m.get("status"),
                "diagnosis": m.get("diagnosis"),
                "exact": m.get("exact_rate"),
                "pitch": m.get("pitch_rate"),
                "pitch_content": m.get("pitch_content_rate"),
                "homr_notes": m.get("homr_notes"),
                "audiveris_notes": m.get("audiveris_notes"),
                "strict_matches": m.get("strict_matches"),
                "strict_precision": m.get("strict_precision"),
                "strict_recall": m.get("strict_recall"),
                "strict_f1": m.get("strict_f1"),
                "strict_onset_tolerance": m.get("strict_onset_tolerance"),
                "strict_duration_tolerance": m.get("strict_duration_tolerance"),
                "homr_only": m.get("homr_only", []),
                "audiveris_only": m.get("audiveris_only", []),
                "homr_content_only": m.get("homr_content_only", []),
                "audiveris_content_only": m.get("audiveris_content_only", []),
                "content_difference_count": m.get("content_difference_count", 0),
            }

DATA = json.dumps(pages, ensure_ascii=False, separators=(",", ":"))
CMP = json.dumps(cmp, ensure_ascii=False, separators=(",", ":"))
HTML = (Path(__file__).resolve().parent / "viewer_template.html").read_text(encoding="utf-8")
HTML = HTML.replace("/*__DATA__*/", "const DATA=" + DATA + ";")
HTML = HTML.replace("/*__CMP__*/", "const CMP=" + CMP + ";")
out.write_text(HTML, encoding="utf-8")
