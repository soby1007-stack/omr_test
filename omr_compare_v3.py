#!/usr/bin/env python3
import json
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
import sys


def load_root(path):
    path = Path(path)

    if path.suffix.lower() == ".mxl":
        with zipfile.ZipFile(path) as z:
            names = [
                n for n in z.namelist()
                if n.lower().endswith(".xml")
                and not n.startswith("META-INF/")
            ]

            # score-partwise XML 우선
            for name in names:
                root = ET.fromstring(z.read(name))
                if root.tag.endswith("score-partwise"):
                    return root

            raise RuntimeError("score-partwise XML을 찾지 못했습니다.")

    return ET.parse(path).getroot()


def get_pitch(note):
    p = note.find("pitch")
    if p is None:
        return None

    return (
        p.findtext("step"),
        int(p.findtext("octave")),
        int(p.findtext("alter") or 0)
    )


def get_divisions(measure, current):
    value = measure.find("attributes/divisions")
    if value is not None and value.text:
        current = Fraction(value.text)
    return current


def measure_events(measure, initial_divisions):
    """
    XML 내부 duration/onset을 quarterLength로 정규화.
    voice 번호는 비교에서 제거한다.
    staff는 유지한다.
    """
    divisions = get_divisions(measure, initial_divisions)

    positions = defaultdict(Fraction)
    result = []

    for note in measure.findall("note"):
        staff = note.findtext("staff") or "1"
        voice = note.findtext("voice") or "1"

        raw_duration = Fraction(note.findtext("duration") or "0")
        duration = raw_duration / divisions

        key = (staff, voice)

        if note.find("chord") is not None:
            onset = positions[key] - duration
        else:
            onset = positions[key]

        p = get_pitch(note)

        if p is not None:
            result.append(
                (
                    staff,
                    onset,
                    p,
                    duration
                )
            )

        if note.find("grace") is None and note.find("chord") is None:
            positions[key] += duration

    return Counter(result), divisions


def collect_measures(root):
    part = root.find("part")
    measures = part.findall("measure")

    current_divisions = Fraction(1)
    output = []

    for measure in measures:
        events, current_divisions = measure_events(
            measure,
            current_divisions
        )
        output.append(events)

    return output


def compare(homr, aud):
    matched = homr & aud
    homr_only = homr - aud
    aud_only = aud - homr

    h_count = sum(homr.values())
    a_count = sum(aud.values())
    m_count = sum(matched.values())

    total = max(h_count, a_count, 1)

    pitch_h = Counter(
        (staff, onset, p)
        for staff, onset, p, dur in homr.elements()
    )

    pitch_a = Counter(
        (staff, onset, p)
        for staff, onset, p, dur in aud.elements()
    )

    pitch_match = sum(
        (pitch_h & pitch_a).values()
    )

    pitch_total = max(
        sum(pitch_h.values()),
        sum(pitch_a.values()),
        1
    )

    return {
        "homr_notes": h_count,
        "audiveris_notes": a_count,
        "exact_note_matches": m_count,
        "exact_rate": m_count / total,
        "pitch_matches": pitch_match,
        "pitch_total": pitch_total,
        "pitch_rate": pitch_match / pitch_total,
        "homr_only": [
            [staff, str(onset), list(pitch), str(duration)]
            for staff, onset, pitch, duration
            in homr_only.elements()
        ],
        "audiveris_only": [
            [staff, str(onset), list(pitch), str(duration)]
            for staff, onset, pitch, duration
            in aud_only.elements()
        ]
    }


def main(out_file):
    homr_pages = []

    for page in (1, 2):
        root = load_root(
            f"output/musicxml/page-{page}_fixed.musicxml"
        )
        homr_pages.append(collect_measures(root))

    aud_root = load_root(
        "output/audiveris/Summer.mxl"
    )

    aud_measures = collect_measures(aud_root)

    pages = []

    for page in (1, 2):
        rows = []

        for i, homr_measure in enumerate(
            homr_pages[page - 1]
        ):
            aud_index = (page - 1) * 24 + i

            if aud_index >= len(aud_measures):
                rows.append({
                    "measure": i + 1,
                    "status": "REVIEW",
                    "reason": "Audiveris measure missing"
                })
                continue

            aud_measure = aud_measures[aud_index]

            c = compare(
                homr_measure,
                aud_measure
            )

            # pitch와 rhythm이 모두 정확히 같은 경우
            if c["exact_rate"] >= 0.95:
                status = "AGREE"

            # pitch는 거의 같은데 duration 차이가 있는 경우
            elif c["pitch_rate"] >= 0.95:
                status = "RHYTHM_REVIEW"

            # 상당 부분 일치
            elif c["pitch_rate"] >= 0.80:
                status = "CLOSE"

            else:
                status = "REVIEW"

            rows.append({
                "measure": i + 1,
                "audiveris_measure": aud_index + 1,
                "status": status,
                **c
            })

        pages.append({
            "page": page,
            "measures": rows
        })

    all_rows = [
        row
        for page in pages
        for row in page["measures"]
    ]

    summary = {
        "total_measures": len(all_rows),
        "agree": sum(
            r["status"] == "AGREE"
            for r in all_rows
        ),
        "rhythm_review": sum(
            r["status"] == "RHYTHM_REVIEW"
            for r in all_rows
        ),
        "close": sum(
            r["status"] == "CLOSE"
            for r in all_rows
        ),
        "review": sum(
            r["status"] == "REVIEW"
            for r in all_rows
        ),
        "mean_exact_rate": (
            sum(
                r.get("exact_rate", 0)
                for r in all_rows
            ) / len(all_rows)
            if all_rows else 0
        ),
        "mean_pitch_rate": (
            sum(
                r.get("pitch_rate", 0)
                for r in all_rows
            ) / len(all_rows)
            if all_rows else 0
        )
    }

    result = {
        "method": "voice-agnostic comparison with MusicXML divisions normalized to quarterLength",
        "summary": summary,
        "pages": pages
    }

    Path(out_file).parent.mkdir(
        parents=True,
        exist_ok=True
    )

    Path(out_file).write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(json.dumps(
        summary,
        ensure_ascii=False,
        indent=2
    ))


if __name__ == "__main__":
    main(sys.argv[1])
