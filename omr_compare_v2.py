#!/usr/bin/env python3
import json, zipfile, xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
import sys

def load_root(path):
    p = Path(path)
    if p.suffix.lower() == ".mxl":
        with zipfile.ZipFile(p) as z:
            name = next(
                n for n in z.namelist()
                if n.lower().endswith(".xml") and not n.startswith("META-INF/")
            )
            return ET.fromstring(z.read(name))
    return ET.parse(p).getroot()

def pitch(n):
    p = n.find("pitch")
    if p is None:
        return None
    return (
        p.findtext("step"),
        int(p.findtext("octave")),
        int(p.findtext("alter") or 0)
    )

def events(measure):
    pos = defaultdict(int)
    out = []

    for n in measure.findall("note"):
        staff = n.findtext("staff") or "1"
        voice = n.findtext("voice") or "1"
        dur = int(n.findtext("duration") or 0)

        onset = (
            pos[(staff, voice)]
            if n.find("chord") is None
            else pos[(staff, voice)] - dur
        )

        p = pitch(n)

        if p is not None:
            out.append((staff, onset, p, dur))

        if n.find("chord") is None:
            pos[(staff, voice)] += dur

    return Counter(out)

def main(out):
    homr_pages = []

    for page in (1, 2):
        root = load_root(
            f"output/musicxml/page-{page}_fixed.musicxml"
        )
        homr_pages.append(
            root.find("part").findall("measure")
        )

    aud = load_root(
        "output/audiveris/Summer.mxl"
    ).find("part").findall("measure")

    pages = []

    for page in (1, 2):
        rows = []

        for i, hm in enumerate(homr_pages[page - 1]):
            am = aud[(page - 1) * 24 + i]

            h = events(hm)
            a = events(am)

            matched = sum((h & a).values())
            total = max(sum(h.values()), sum(a.values()), 1)
            rate = matched / total

            if rate >= 0.95:
                status = "AGREE"
            elif rate >= 0.80:
                status = "CLOSE"
            else:
                status = "REVIEW"

            rows.append({
                "measure": i + 1,
                "status": status,
                "voice_agnostic_rate": rate,
                "matched": matched,
                "total": total,
                "homr_events": sum(h.values()),
                "audiveris_events": sum(a.values()),
                "homr_only": [list(x) for x in (h - a).elements()],
                "audiveris_only": [list(x) for x in (a - h).elements()]
            })

        pages.append({
            "page": page,
            "measures": rows
        })

    summary = {}

    for p in pages:
        rows = p["measures"]
        summary[f"page-{p['page']}"] = {
            "agree": sum(x["status"] == "AGREE" for x in rows),
            "close": sum(x["status"] == "CLOSE" for x in rows),
            "review": sum(x["status"] == "REVIEW" for x in rows),
            "mean_rate":
                sum(x["voice_agnostic_rate"] for x in rows) / len(rows)
        }

    result = {
        "method":
            "voice-agnostic staff/onset/pitch/duration comparison",
        "summary": summary,
        "pages": pages
    }

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main(sys.argv[1])
