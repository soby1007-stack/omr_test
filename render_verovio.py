#!/usr/bin/env python3
import sys
from pathlib import Path
import verovio

if len(sys.argv) != 3:
    print("usage: render_verovio.py INPUT.musicxml OUTPUT_DIR")
    raise SystemExit(2)

src = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
out.mkdir(parents=True, exist_ok=True)

# Verovio Python wheel의 실제 resource 디렉터리 탐색
pkg = Path(verovio.__file__).resolve().parent

candidates = [
    pkg / "data",
    pkg / "share" / "verovio",
    pkg.parent / "share" / "verovio",
]

resource = next((p for p in candidates if p.is_dir()), None)

if resource is None:
    print("ERROR: Verovio resource directory not found")
    print("Package:", pkg)
    for p in candidates:
        print("Checked:", p)
    raise SystemExit(1)

print("Verovio:", verovio.__version__ if hasattr(verovio, "__version__") else "unknown")
print("Resource:", resource)

tk = verovio.toolkit(False)

if not tk.setResourcePath(str(resource)):
    raise RuntimeError(f"Verovio resource load failed: {resource}")

tk.setOptions({
    "scale": 40,
    "adjustPageHeight": True,
    "header": "none",
    "footer": "none",
})

if not tk.loadFile(str(src)):
    raise RuntimeError(f"Verovio could not load {src}")

pages = tk.getPageCount()
print(f"Verovio pages={pages}")

for page in range(1, pages + 1):
    dst = out / f"page-{page}.svg"
    svg = tk.renderToSVG(page)
    dst.write_text(svg, encoding="utf-8")
    print(dst)
