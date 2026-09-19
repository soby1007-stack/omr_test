#!/usr/bin/env python3
import json, zipfile, xml.etree.ElementTree as ET
from pathlib import Path
import sys

def load_xml(path):
    path = Path(path)
    if path.suffix.lower() == ".mxl":
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist()
                     if n.lower().endswith(".xml") and not n.startswith("META-INF/")]
            return ET.fromstring(z.read(names[0]))
    return ET.parse(path).getroot()

def pitch(note):
    p = note.find("pitch")
    if p is None:
        return None
    return (
        p.findtext("step"),
        p.findtext("octave"),
        int(p.findtext("alter") or 0)
    )

def event_map(measure):
    pos = {}
    events = {}

    for n in measure.findall("note"):
        staff = n.findtext("staff") or "1"
        voice = n.findtext("voice") or "1"
        key = (staff, voice)
        dur = int(n.findtext("duration") or 0)

        if n.find("chord") is None:
            onset = pos.get(key, 0)
            pos[key] = onset + dur
        else:
            previous = [
                k[2] for k in events
                if k[0] == staff and k[1] == voice
            ]
            onset = max(previous) if previous else 0

        p = pitch(n)
        if p is not None:
            events.setdefault((staff, voice, onset), []).append((p, dur))

    return {k: tuple(sorted(v)) for k, v in events.items()}

def compare_measure(hm, am):
    h = event_map(hm)
    a = event_map(am)

    keys = sorted(set(h) | set(a))
    pm = dm = exact = 0
    diffs = []

    for k in keys:
        hp = h.get(k, ())
        ap = a.get(k, ())

        if tuple(x[0] for x in hp) == tuple(x[0] for x in ap):
            pm += 1
        if tuple(x[1] for x in hp) == tuple(x[1] for x in ap):
            dm += 1
        if hp == ap:
            exact += 1
        else:
            diffs.append({
                "staff": k[0],
                "voice": k[1],
                "onset": k[2],
                "homr": [[list(p), d] for p, d in hp],
                "audiveris": [[list(p), d] for p, d in ap]
            })

    total = len(keys)

    return {
        "event_groups": total,
        "pitch_matches": pm,
        "duration_matches": dm,
        "exact_matches": exact,
        "pitch_rate": pm / total if total else 1,
        "duration_rate": dm / total if total else 1,
        "exact_rate": exact / total if total else 1,
        "differences": diffs[:30]
    }

def main():
    out = Path(sys.argv[1])

    aud = load_xml("output/audiveris/Summer.mxl")
    ams = aud.find("part").findall("measure")

    pages = []

    for page in (1, 2):
        hp = load_xml(
            f"output/musicxml/page-{page}_fixed.musicxml"
        ).find("part")

        hms = hp.findall("measure")
        results = []

        for i, hm in enumerate(hms):
            ai = (page - 1) * 24 + i
            am = ams[ai]

            c = compare_measure(hm, am)

            if c["pitch_rate"] >= .95 and c["duration_rate"] >= .95:
                status = "AGREE"
            elif c["pitch_rate"] >= .80:
                status = "CLOSE"
            else:
                status = "REVIEW"

            results.append({
                "measure": i + 1,
                "audiveris_measure": ai + 1,
                "status": status,
                **{k:v for k,v in c.items() if k != "differences"},
                "differences": c["differences"]
            })

        pages.append({
            "page": page,
            "measures": results
        })

    summary = {}

    for page in pages:
        key = f"page-{page['page']}"
        vals = page["measures"]

        summary[key] = {
            "agree": sum(x["status"] == "AGREE" for x in vals),
            "close": sum(x["status"] == "CLOSE" for x in vals),
            "review": sum(x["status"] == "REVIEW" for x in vals)
        }

    result = {
        "mapping":
            "HOMR page1 -> Audiveris M1-24; "
            "HOMR page2 -> Audiveris M25-48",
        "summary": summary,
        "pages": pages
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
