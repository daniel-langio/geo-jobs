"""Draw the roof faces of each textured CityJSON on its aerial image.

usage: render.py <out_dir> <in_dir> <png_dir> <label> <ref_out_dir>
The crop is computed from <ref_out_dir> (the final output) so before/after images are comparable.
"""
import json, sys, pathlib
from PIL import Image, ImageDraw

out, inp, png, label, ref = (pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]),
                             pathlib.Path(sys.argv[3]), sys.argv[4], pathlib.Path(sys.argv[5]))
png.mkdir(parents=True, exist_ok=True)
IMG = {"roof7_roofer": "roof7"}


def faces(path, W, H):
    d = json.load(open(path))
    uv = d["appearance"]["vertices-texture"]
    for o in d["CityObjects"].values():
        for g in o["geometry"]:
            for surf in g.get("appearance", {}).get("texture", {}).get("default", {}).get("values", []):
                for ring in surf or []:
                    yield [(uv[i][0] * W, (1 - uv[i][1]) * H) for i in ring[1:]]  # CityJSON: v axis points up


for f in sorted(out.glob("*.json")):
    name = f.stem
    im = Image.open(inp / f"{IMG.get(name, name)}.jpg").convert("RGBA")
    W, H = im.size
    ov = Image.new("RGBA", im.size)
    dr = ImageDraw.Draw(ov)
    inside = total = 0
    for pts in faces(f, W, H):
        total += len(pts)
        inside += sum(1 for x, y in pts if 0 <= x <= W and 0 <= y <= H)
        if len(pts) > 2 and all(abs(x) < 4 * W and abs(y) < 4 * H for x, y in pts):
            dr.polygon(pts, fill=(254, 83, 27, 90), outline=(254, 83, 27, 255), width=4)
    im = Image.alpha_composite(im, ov).convert("RGB")
    ref_f = ref / f.name
    pts_all = [p for ring in faces(ref_f, W, H) for p in ring] if ref_f.exists() else []
    if pts_all:
        xs, ys = zip(*pts_all)
        m = 260
        im = im.crop((max(0, int(min(xs) - m)), max(0, int(min(ys) - m)),
                      min(W, int(max(xs) + m)), min(H, int(max(ys) + m))))
    im.thumbnail((900, 900))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 330, 30), fill=(255, 255, 255))
    d.text((8, 9), f"{inside}/{total} sommets dans l'image", fill=(21, 42, 27))
    im.save(png / f"{label}__{name}.png")
    print(f"{label} {name}: {inside}/{total} sommets de texture dans l'image")
