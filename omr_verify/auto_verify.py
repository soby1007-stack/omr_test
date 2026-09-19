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
