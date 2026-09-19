import json
import sys
from pathlib import Path

def main():
    root=Path(sys.argv[1])
    out=Path(sys.argv[2])

    rows=[]

    for p in sorted(root.glob("page-*.json")):
        d=json.loads(p.read_text(encoding="utf-8"))
        rows.append({
            "page":p.stem,
            "source_count":d.get("source_count",0),
            "status":d.get("status")
        })

    out.write_text(
        json.dumps({
            "version":2,
            "pages":rows
        },ensure_ascii=False,indent=2),
        encoding="utf-8"
    )

if __name__=="__main__":
    main()
