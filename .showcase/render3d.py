"""Software 3D render of a textured CityJSON (roofs sampled from the aerial image, walls in grey).

usage: render3d.py <json> <image.jpg> <out.png> [azimuth_deg] [elevation_deg]
"""
import json, sys
import numpy as np
import mapbox_earcut as earcut
from PIL import Image

path, imgp, outp = sys.argv[1:4]
AZ, EL = (float(sys.argv[4]) if len(sys.argv) > 4 else 215.0), (float(sys.argv[5]) if len(sys.argv) > 5 else 38.0)
d = json.load(open(path))
tex = np.asarray(Image.open(imgp).convert("RGB"), dtype=np.float32)
TH, TW = tex.shape[:2]
uvs = np.array(d["appearance"]["vertices-texture"])
sc, tr = np.array(d["transform"]["scale"]), np.array(d["transform"]["translate"])
V = np.array(d["vertices"], dtype=np.float64) * sc + tr
V -= V.mean(axis=0)

tris = []  # (3x3 positions, 3x2 uv or None)
for o in d["CityObjects"].values():
    for g in o["geometry"]:
        if g["type"] != "Solid":
            continue
        faces = g["boundaries"][0]
        vals = g.get("appearance", {}).get("texture", {}).get("default", {}).get("values", [])
        if len(vals) != len(faces) and vals:
            vals = vals[0]
        for fi, face in enumerate(faces):
            ring = face[0]
            P = V[ring]
            n = np.cross(P[1] - P[0], P[2] - P[0])
            n = sum((np.cross(P[i], P[(i + 1) % len(P)]) for i in range(len(P))), np.zeros(3))  # Newell
            if np.linalg.norm(n) == 0:
                continue
            n /= np.linalg.norm(n)
            a = np.cross(n, [0, 0, 1.0]); a = a / np.linalg.norm(a) if np.linalg.norm(a) > 1e-9 else np.array([1.0, 0, 0])
            b = np.cross(n, a)
            pts2 = np.stack([P @ a, P @ b], axis=1)
            idx = earcut.triangulate_float64(pts2, np.array([len(ring)], dtype=np.uint32))
            t = vals[fi] if fi < len(vals) else None
            tuv = None
            if t:
                tuv = uvs[t[0]]  # geo-jobs writes uv indices only (no leading texture index)
            for k in range(0, len(idx), 3):
                i0, i1, i2 = idx[k:k + 3]
                tris.append((P[[i0, i1, i2]], None if tuv is None else tuv[[i0, i1, i2]], n))

# camera
az, el = np.radians(AZ), np.radians(EL)
fwd = -np.array([np.cos(el) * np.sin(az), np.cos(el) * np.cos(az), np.sin(el)])
right = np.cross(fwd, [0, 0, 1.0]); right /= np.linalg.norm(right)
up = np.cross(right, fwd)
R = np.stack([right, up, fwd])
ext = np.abs(V).max() * 1.0
dist = ext * 4.2
SS, WIDTH, HEIGHT = 2, 1100, 800
W, H = WIDTH * SS, HEIGHT * SS
f = 1.9 * H
zb = np.full((H, W), np.inf)
img = np.zeros((H, W, 3), np.float32)
yy = np.linspace(0, 1, H)[:, None, None]
img[:] = (1 - yy) * np.array([226, 232, 236]) + yy * np.array([250, 250, 250])
light = np.array([0.45, -0.4, 0.8]); light /= np.linalg.norm(light)

for P, uv, n in tris:
    C = (P @ R.T) + np.array([0, 0, dist])
    if (C[:, 2] <= 0.1).any():
        continue
    sx = W / 2 + f * C[:, 0] / C[:, 2]
    sy = H / 2 - f * C[:, 1] / C[:, 2]
    x0, x1 = int(max(0, np.floor(sx.min()))), int(min(W - 1, np.ceil(sx.max())))
    y0, y1 = int(max(0, np.floor(sy.min()))), int(min(H - 1, np.ceil(sy.max())))
    if x0 > x1 or y0 > y1:
        continue
    X, Y = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
    den = (sy[1] - sy[2]) * (sx[0] - sx[2]) + (sx[2] - sx[1]) * (sy[0] - sy[2])
    if abs(den) < 1e-9:
        continue
    l0 = ((sy[1] - sy[2]) * (X - sx[2]) + (sx[2] - sx[1]) * (Y - sy[2])) / den
    l1 = ((sy[2] - sy[0]) * (X - sx[2]) + (sx[0] - sx[2]) * (Y - sy[2])) / den
    l2 = 1 - l0 - l1
    m = (l0 >= 0) & (l1 >= 0) & (l2 >= 0)
    if not m.any():
        continue
    iw = 1 / C[:, 2]
    w = l0 * iw[0] + l1 * iw[1] + l2 * iw[2]
    z = 1 / w
    sub = zb[y0:y1 + 1, x0:x1 + 1]
    m &= z < sub
    if not m.any():
        continue
    shade = 0.55 + 0.45 * abs(float(n @ light))
    if uv is None:
        col = np.broadcast_to(np.array([152, 156, 160], np.float32) * shade, X.shape + (3,))
    else:
        u = (l0 * iw[0] * uv[0, 0] + l1 * iw[1] * uv[1, 0] + l2 * iw[2] * uv[2, 0]) * z
        v = (l0 * iw[0] * uv[0, 1] + l1 * iw[1] * uv[1, 1] + l2 * iw[2] * uv[2, 1]) * z
        px = np.clip((u * TW).astype(int), 0, TW - 1)
        py = np.clip(((1 - v) * TH).astype(int), 0, TH - 1)
        col = tex[py, px] * (0.8 + 0.2 * shade)
    sub[m] = z[m]
    img[y0:y1 + 1, x0:x1 + 1][m] = col[m]

out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((WIDTH, HEIGHT), Image.LANCZOS)
# crop to content
arr = np.asarray(out)
np.save("/dev/null", arr) if False else None
mask = np.isfinite(zb[::SS, ::SS])
ys, xs = np.where(mask)
mx = 40
out = out.crop((max(0, xs.min() - mx), max(0, ys.min() - mx), min(WIDTH, xs.max() + mx), min(HEIGHT, ys.max() + mx)))
out.save(outp)
print(outp, out.size)
