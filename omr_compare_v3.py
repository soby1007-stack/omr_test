#!/usr/bin/env python3
import json
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from fractions import Fraction
from pathlib import Path
import sys


def load_root(path):
    path = Path(path)
    if path.suffix.lower() == ".mxl":
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".xml") and not n.startswith("META-INF/")]
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
    return (p.findtext("step"), int(p.findtext("octave")), int(p.findtext("alter") or 0))


def get_divisions(measure, current):
    value = measure.find("attributes/divisions")
    if value is not None and value.text:
        current = Fraction(value.text)
    return current


def measure_events(measure, initial_divisions):
    """MusicXML cursor/backup/forward timing을 따라 event를 추출한다."""
    divisions = get_divisions(measure, initial_divisions)
    cursor = Fraction(0)
    last_onset_by_voice = {}
    result = []

    for item in measure:
        if item.tag == "note":
            staff = item.findtext("staff") or "1"
            voice = item.findtext("voice") or "1"
            key = (staff, voice)
            raw_duration = Fraction(item.findtext("duration") or "0")
            duration = raw_duration / divisions
            is_chord = item.find("chord") is not None

            onset = last_onset_by_voice.get(key, cursor) if is_chord else cursor
            pitch = get_pitch(item)
            if pitch is not None:
                result.append((staff, onset, pitch, duration))

            if item.find("grace") is None and not is_chord:
                cursor += duration
                last_onset_by_voice[key] = onset

        elif item.tag in ("backup", "forward"):
            raw_duration = Fraction(item.findtext("duration") or "0")
            delta = raw_duration / divisions
            cursor += delta if item.tag == "forward" else -delta

    return Counter(result), divisions


def collect_measures(root):
    part = root.find("part")
    measures = part.findall("measure")
    current_divisions = Fraction(1)
    output = []
    for measure in measures:
        events, current_divisions = measure_events(measure, current_divisions)
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

    pitch_h = Counter((staff, onset, p) for staff, onset, p, dur in homr.elements())
    pitch_a = Counter((staff, onset, p) for staff, onset, p, dur in aud.elements())
    onset_pitch_match = sum((pitch_h & pitch_a).values())
    onset_pitch_total = max(sum(pitch_h.values()), sum(pitch_a.values()), 1)

    # 시간 위치(onset)를 무시하고 staff + pitch의 음 개수만 비교한다.
    # 같은 음을 다른 시점에 배치한 경우도 여기서는 일치로 본다.
    pitch_content_h = Counter((staff, p) for staff, onset, p, dur in homr.elements())
    pitch_content_a = Counter((staff, p) for staff, onset, p, dur in aud.elements())
    pitch_content_match = sum((pitch_content_h & pitch_content_a).values())
    pitch_content_total = max(sum(pitch_content_h.values()), sum(pitch_content_a.values()), 1)

    # onset을 무시한 pitch 내용 차이를 명시적으로 기록한다.
    # 이 정보는 "HOMR이 틀렸다"가 아니라 "두 OMR 엔진이 다르다"는
    # 사실을 진단하기 위한 것이다. 어느 쪽이 원본과 맞는지는 PDF 확인이 필요하다.
    content_homr_only = pitch_content_h - pitch_content_a
    content_aud_only = pitch_content_a - pitch_content_h

    def content_diff(counter):
        return [
            {
                "staff": staff,
                "pitch": list(pitch),
                "count": count
            }
            for (staff, pitch), count in sorted(
                counter.items(),
                key=lambda x: (str(x[0][0]), str(x[0][1]))
            )
        ]

    return {
        "homr_notes": h_count,
        "audiveris_notes": a_count,
        "exact_note_matches": m_count,
        "exact_rate": m_count / total,
        "pitch_matches": onset_pitch_match,
        "pitch_total": onset_pitch_total,
        "pitch_rate": onset_pitch_match / onset_pitch_total,
        "pitch_content_matches": pitch_content_match,
        "pitch_content_total": pitch_content_total,
        "pitch_content_rate": pitch_content_match / pitch_content_total,
        "homr_only": [[staff, str(onset), list(pitch), str(duration)] for staff, onset, pitch, duration in homr_only.elements()],
        "audiveris_only": [[staff, str(onset), list(pitch), str(duration)] for staff, onset, pitch, duration in aud_only.elements()],
        "homr_content_only": content_diff(content_homr_only),
        "audiveris_content_only": content_diff(content_aud_only),
        "content_difference_count": sum(content_homr_only.values()) + sum(content_aud_only.values())
    }


def main(out_file):
    homr_pages = []
    for page in (1, 2):
        root = load_root(f"output/musicxml/page-{page}_fixed.musicxml")
        homr_pages.append(collect_measures(root))

    aud_root = load_root("output/audiveris/Summer.mxl")
    aud_measures = collect_measures(aud_root)
    pages = []

    for page in (1, 2):
        rows = []
        for i, homr_measure in enumerate(homr_pages[page - 1]):
            aud_index = (page - 1) * 24 + i
            if aud_index >= len(aud_measures):
                rows.append({
                    "measure": i + 1,
                    "status": "REVIEW",
                    "diagnosis": "AUDIVERIS_MEASURE_MISSING",
                    "reason": "Audiveris measure missing"
                })
                continue
            c = compare(homr_measure, aud_measures[aud_index])
            if c["exact_rate"] >= 0.95:
                status = "AGREE"
                diagnosis = "MATCH"
            elif c["pitch_content_rate"] >= 0.95:
                status = "RHYTHM_REVIEW"
                diagnosis = "TIMING_DIFFERENCE"
            elif c["pitch_content_rate"] >= 0.80:
                status = "CLOSE"
                diagnosis = "PARTIAL_ENGINE_DISAGREEMENT"
            else:
                status = "REVIEW"
                diagnosis = "ENGINE_DISAGREEMENT"

            rows.append({
                "measure": i + 1,
                "audiveris_measure": aud_index + 1,
                "status": status,
                "diagnosis": diagnosis,
                **c
            })
        pages.append({"page": page, "measures": rows})

    all_rows = [r for page in pages for r in page["measures"]]
    summary = {
        "total_measures": len(all_rows),
        "agree": sum(r["status"] == "AGREE" for r in all_rows),
        "rhythm_review": sum(r["status"] == "RHYTHM_REVIEW" for r in all_rows),
        "close": sum(r["status"] == "CLOSE" for r in all_rows),
        "review": sum(r["status"] == "REVIEW" for r in all_rows),
        "mean_exact_rate": sum(r.get("exact_rate", 0) for r in all_rows) / len(all_rows) if all_rows else 0,
        "mean_pitch_rate": sum(r.get("pitch_rate", 0) for r in all_rows) / len(all_rows) if all_rows else 0,
        "mean_pitch_content_rate": sum(r.get("pitch_content_rate", 0) for r in all_rows) / len(all_rows) if all_rows else 0,
    }
    result = {
        "method": "voice-agnostic comparison with MusicXML cursor/backup/forward timing; onset-aware and onset-independent pitch-content metrics; explicit engine-disagreement diagnostics",
        "summary": summary,
        "pages": pages
    }
    Path(out_file).parent.mkdir(parents=True, exist_ok=True)
    Path(out_file).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main(sys.argv[1])
