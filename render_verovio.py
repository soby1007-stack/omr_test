#!/usr/bin/env python3
import sys
from pathlib import Path
import verovio

if len(sys.argv) < 3:
    print("usage: render_verovio.py INPUT.musicxml OUTPUT_DIR")
    raise SystemExit(2)

src = Path(sys.argv[1])
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)

tk = verovio.toolkit(False)
# Python wheels normally resolve their resource directory automatically.
# Keep an explicit fallback for unusual environments.
try:
    tk.setResourcePath(str(Path(verovio.__file__).resolve().parent / "data"))
except Exception:
    pass

# Python toolkit options are dictionaries/stringified JSON internally.
tk.setOptions({
    "scale": 40,
    "adjustPageHeight": True,
    "header": "none",
    "footer": "none",
})

if not tk.loadFile(str(src)):
    raise RuntimeError(f"Verovio could not load {src}")

pages = tk.getPageCount()
print(f"Verovio {tk.getVersion()} pages={pages}")

for page in range(1, pages + 1):
    dst = out / f"page-{page}.svg"
    svg = tk.renderToSVG(page)
    dst.write_text(svg, encoding="utf-8")
    print(dst)
