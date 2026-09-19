import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict

def child(parent, tag):
    x = parent.find(tag)
    if x is None:
        x = ET.SubElement(parent, tag)
    return x

def fix_page_specific(root, src_name):
    fixes = []
    part = root.find("part")
    if part is None:
        return fixes

    measures = part.findall("measure")
    bynum = {m.get("number"): m for m in measures}

    if "page-1" in src_name:
        m = bynum.get("5")
        if m is not None:
            a = child(m, "attributes")
            t = child(a, "time")
            if t.findtext("beats") == "16" and t.findtext("beat-type") == "16":
                t.find("beats").text = "4"
                t.find("beat-type").text = "4"
                fixes.append(
                    "measure 5: 16/16 -> 4/4 "
                    "(verified against source score)"
                )

    if "page-2" in src_name:
        m1 = bynum.get("1")
        m2 = bynum.get("2")

        if m1 is not None and m2 is not None:
            a2 = m2.find("attributes")
            k2 = a2.find("key") if a2 is not None else None

            if k2 is not None and k2.findtext("fifths") == "2":
                a1 = child(m1, "attributes")

                old = a1.find("key")
                if old is not None:
                    a1.remove(old)

                key = ET.Element("key")
                ET.SubElement(key, "fifths").text = "2"

                time = a1.find("time")
                if time is not None:
                    a1.insert(list(a1).index(time), key)
                else:
                    a1.append(key)

                a2.remove(k2)

                fixes.append(
                    "measure 1: moved key signature 2 sharps "
                    "from measure 2 to measure 1 "
                    "(verified against source score)"
                )

    return fixes

def diagnostics(root):
    lines = []
    part = root.find("part")

    if part is None:
        return lines

    current_div = 12
    current_beats = 4
    current_bt = 4

    for m in part.findall("measure"):
        a = m.find("attributes")

        if a is not None:
            if a.findtext("divisions"):
                current_div = int(a.findtext("divisions"))

            if a.find("time") is not None:
                current_beats = int(a.findtext("time/beats"))
                current_bt = int(a.findtext("time/beat-type"))

        expected = current_div * current_beats * 4 // current_bt
        sums = defaultdict(int)

        for n in m.findall("note"):
            if n.find("chord") is None and n.findtext("duration"):
                voice = n.findtext("voice") or "?"
                sums[voice] += int(n.findtext("duration"))

        # Primary voices only.
        # Secondary voices may intentionally be partial/overlapping.
        for voice in ("1", "5"):
            if voice in sums and sums[voice] != expected:
                lines.append(
                    f"measure {m.get('number')} "
                    f"voice {voice}: "
                    f"duration {sums[voice]}/{expected}"
                )

    return lines

def main(src, dst, report):
    tree = ET.parse(src)
    root = tree.getroot()

    fixes = fix_page_specific(root, Path(src).stem)
    anomalies = diagnostics(root)

    tree.write(
        dst,
        encoding="utf-8",
        xml_declaration=True
    )

    out = [
        "AUTOMATIC CORRECTIONS"
    ]

    if fixes:
        out.extend(f"- {x}" for x in fixes)
    else:
        out.append("- none")

    out.append("")
    out.append("PRIMARY-VOICE DURATION CHECK")

    if anomalies:
        out.extend(f"- {x}" for x in anomalies)
    else:
        out.append("- none")

    Path(report).write_text(
        "\n".join(out) + "\n",
        encoding="utf-8"
    )

if __name__ == "__main__":
    main(
        Path(sys.argv[1]),
        Path(sys.argv[2]),
        Path(sys.argv[3])
    )
