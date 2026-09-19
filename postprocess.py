import sys
import xml.etree.ElementTree as ET
from pathlib import Path

def fix_and_check(src, dst, report):
    tree = ET.parse(src)
    root = tree.getroot()
    lines = []

    parts = root.findall(".//part")
    for part in parts:
        measures = part.findall("measure")

        for i, m in enumerate(measures):
            # isolated 16/16 -> 4/4
            ts = m.find("attributes/time")
            if ts is not None:
                beats = ts.findtext("beats")
                beat_type = ts.findtext("beat-type")

                if beats == "16" and beat_type == "16":
                    prev_ts = measures[i-1].find("attributes/time") if i > 0 else None
                    next_ts = measures[i+1].find("attributes/time") if i+1 < len(measures) else None

                    prev = (
                        prev_ts.findtext("beats"),
                        prev_ts.findtext("beat-type")
                    ) if prev_ts is not None else None

                    nxt = (
                        next_ts.findtext("beats"),
                        next_ts.findtext("beat-type")
                    ) if next_ts is not None else None

                    if prev == ("4", "4") and nxt == ("4", "4"):
                        ts.find("beats").text = "4"
                        ts.find("beat-type").text = "4"
                        lines.append(
                            f"{part.get('id')} measure {m.get('number')}: "
                            "16/16 -> 4/4"
                        )

            # measure duration check
            divisions = m.findtext("attributes/divisions")
            if divisions:
                try:
                    divisions = int(divisions)
                    beats = m.findtext("attributes/time/beats")
                    beat_type = m.findtext("attributes/time/beat-type")

                    if beats and beat_type:
                        expected = divisions * int(beats) * 4 // int(beat_type)

                        total = 0
                        for note in m.findall("note"):
                            d = note.findtext("duration")
                            if d:
                                total += int(d)

                        if total != expected:
                            lines.append(
                                f"{part.get('id')} measure {m.get('number')}: "
                                f"duration {total}/{expected} "
                                f"(expected/actual)"
                            )
                except Exception:
                    pass

    tree.write(dst, encoding="utf-8", xml_declaration=True)

    if not lines:
        lines.append("No automatic corrections or duration anomalies detected.")

    Path(report).write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    report = Path(sys.argv[3])
    fix_and_check(src, dst, report)
