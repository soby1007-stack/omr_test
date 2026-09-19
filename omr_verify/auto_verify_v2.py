import json
import sys
from pathlib import Path

from source_symbols import detect_noteheads
from match_engine import match, confidence

def main():
    if len(sys.argv) != 3:
        print("usage: auto_verify_v2.py IMAGE OUTPUT_JSON")
        raise SystemExit(2)

    image=Path(sys.argv[1])
    out=Path(sys.argv[2])

    source=detect_noteheads(image)

    # HOMR 좌표는 현재 자동검증 단계에서 별도 입력으로 연결한다.
    # 여기서는 원본 notehead 후보를 안정적으로 생성한다.
    result={
        "version":2,
        "image":str(image),
        "source_noteheads":source,
        "source_count":len(source),
        "status":"READY_FOR_HOMR_MATCH"
    }

    out.write_text(
        json.dumps(result,ensure_ascii=False,indent=2),
        encoding="utf-8"
    )

    print(f"{image}: {len(source)} source notehead candidates")

if __name__=="__main__":
    main()
