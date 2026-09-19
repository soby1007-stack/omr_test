import sys, json, base64, re
from pathlib import Path

layout=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
work=Path(sys.argv[2]); out=Path(sys.argv[3])
def b64(p): return base64.b64encode(Path(p).read_bytes()).decode()

pages=[]
for i,p in enumerate(layout["pages"],1):
    svgs=[]
    d=work/f"svg-source-{i}"
    for f in sorted(d.glob("page-*.svg"),key=lambda x:int(re.search(r"page-(\d+)",x.name).group(1))):
        svgs.append(f.read_text(encoding="utf-8"))
    pages.append({"image":"data:image/png;base64,"+b64(work/pdf/f"pdf-page-{i}.png"),
                  "svgs":svgs,"measures":p["measures"],"w":p["width"],"h":p["height"]})

DATA=json.dumps(pages,ensure_ascii=False,separators=(",",":"))
HTML=(Path(__file__).resolve().parent/"viewer_template.html").read_text(encoding="utf-8")
HTML=HTML.replace("/*__DATA__*/", "const DATA="+DATA+";")
out.write_text(HTML,encoding="utf-8")
