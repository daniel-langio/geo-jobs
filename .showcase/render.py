"""Draw the roof faces of each textured CityJSON on its aerial image: render.py <out_dir> <in_dir> <png_dir> <label>."""
import json, sys, pathlib
from PIL import Image, ImageDraw

out, inp, png, label = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3]), sys.argv[4]
png.mkdir(parents=True, exist_ok=True)
IMG = {"roof7_roofer": "roof7"}
for f in sorted(out.glob("*.json")):
    name = f.stem
    d = json.load(open(f))
    uv = d["appearance"]["vertices-texture"]
    im = Image.open(inp / f"{IMG.get(name, name)}.jpg").convert("RGB")
    W, H = im.size
    ov = Image.new("RGBA", im.size)
    dr = ImageDraw.Draw(ov)
    pts_all, inside, total = [], 0, 0
    for o in d["CityObjects"].values():
        for g in o["geometry"]:
            vals = g.get("appearance", {}).get("texture", {}).get("default", {}).get("values", [])
            for surf in vals:
                if not surf:
                    continue
                for ring in surf:
                    pts = [(uv[i][0] * W, uv[i][1] * H) for i in ring[1:]]
                    total += len(pts)
                    inside += sum(1 for x, y in pts if 0 <= x <= W and 0 <= y <= H)
                    if len(pts) > 2:
                        dr.polygon(pts, fill=(254, 83, 27, 90), outline=(254, 83, 27, 255), width=4)
                        pts_all += pts
    im = Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")
    if pts_all:
        xs, ys = zip(*pts_all)
        m = 260
        box = (max(0, int(min(xs) - m)), max(0, int(min(ys) - m)), min(W, int(max(xs) + m)), min(H, int(max(ys) + m)))
        im = im.crop(box)
    im.thumbnail((900, 900))
    im.save(png / f"{label}__{name}.png")
    print(f"{label} {name}: {inside}/{total} sommets de texture dans l'image")
