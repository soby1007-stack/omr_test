import sys
from pathlib import Path
import verovio
src=Path(sys.argv[1]); out=Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
tk=verovio.toolkit(False)
tk.setOptions({"scale":40,"adjustPageHeight":True,"header":"none","footer":"none"})
if not tk.loadFile(str(src)): raise RuntimeError(f"Verovio load failed: {src}")
for i in range(1,tk.getPageCount()+1):
    (out/f"page-{i}.svg").write_text(tk.renderToSVG(i),encoding="utf-8")
