import os, numpy as np
from PIL import Image, ImageDraw, ImageFont
DL = r"C:\Users\bubakazouba\chat-assistant\state\downloads"

face = Image.open(os.path.join(DL, "face_sticker.webp")).convert("RGBA")
face = face.crop(face.getbbox())
FW, FH = face.size

font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 74)

def detect_cockpit(body):
    rgb = body.convert("RGB").copy()
    W, H = rgb.size
    for seed in [(0,0),(W-1,0),(0,H-1),(W-1,H-1),(W//2,1),(1,H//2),(W-2,H//2)]:
        ImageDraw.floodfill(rgb, seed, (255,0,255), thresh=32)
    arr = np.array(rgb)
    white = (arr[:,:,0]>232)&(arr[:,:,1]>232)&(arr[:,:,2]>232)
    ys, xs = np.where(white)
    if len(xs) < 80:
        return None
    # largest enclosed white blob via coarse histogram peak (robust to tiny specks)
    cx, cy = int(np.median(xs)), int(np.median(ys))
    # radius from the interquartile spread
    rr = int((np.percentile(xs,90)-np.percentile(xs,10) + np.percentile(ys,90)-np.percentile(ys,10))/4)
    return cx, cy, max(rr, 60)

# "2" badge spots per vehicle (on the coloured body, away from wheels/cockpit) — 1024 coords
NUM_POS = {"truck": (300, 560), "train": (470, 560), "plane": (690, 470)}

for name in ("truck", "train", "plane"):
    body = Image.open(os.path.join(DL, f"body_{name}.png")).convert("RGBA")
    ck = detect_cockpit(body)
    print(name, "cockpit:", ck)
    if ck:
        cx, cy, rr = ck
        diam = int(rr*2*1.12)
        f = face.resize((diam, int(FH*diam/FW)), Image.LANCZOS)
        body.alpha_composite(f, (cx - f.size[0]//2, cy - int(f.size[1]*0.52)))
    # "2" badge
    d = ImageDraw.Draw(body)
    nx, ny = NUM_POS[name]; br = 52
    d.ellipse((nx-br, ny-br, nx+br, ny+br), fill=(255,255,255,255), outline=(0,0,0,255), width=7)
    bb = d.textbbox((0,0), "2", font=font)
    d.text((nx-(bb[2]-bb[0])/2-bb[0], ny-(bb[3]-bb[1])/2-bb[1]), "2", fill=(0,0,0,255), font=font)
    body.save(os.path.join(DL, f"topper_{name}.png"))
    print("saved", name)
