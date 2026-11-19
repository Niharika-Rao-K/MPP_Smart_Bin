import csv
import glob
import io
import itertools
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from app.services.image_hash import compute, variant_phashes, hamming


def to_bytes(img, fmt="PNG", **kw):
    buf = io.BytesIO()
    img.convert("RGB").save(buf, fmt, **kw)
    return buf.getvalue()


def jpeg(img, q, scale=1.0):
    img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))))
    return Image.open(io.BytesIO(to_bytes(img, "JPEG", quality=q)))


ATTACKS = {
    "resize_50":  lambda i: i.resize((max(1, i.width // 2), max(1, i.height // 2))),
    "jpeg_q30":   lambda i: jpeg(i, 30),
    "crop_10":    lambda i: i.crop((i.width * .1, i.height * .1, i.width * .9, i.height * .9)),
    "brightness": lambda i: ImageEnhance.Brightness(i).enhance(1.3),
    "blur":       lambda i: i.filter(ImageFilter.GaussianBlur(2)),
    "mirror":     ImageOps.mirror,
    "rotate_90":  lambda i: i.rotate(90, expand=True),
    "screenshot": lambda i: jpeg(i, 60, 0.7),
}

files = sorted(f for f in glob.glob("eval_images/*.*")
               if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")))
if len(files) < 2:
    sys.exit("Put at least 2 images in eval_images/")

group = lambda f: Path(f).stem.rsplit("_", 1)[0]
phash = {f: compute(Path(f).read_bytes())["phash"] for f in files}
min_dist = lambda data, ref: min(hamming(v, ref) for v in variant_phashes(data))

# 1) copies of the same photo (should be caught)
attack_dist = {n: [] for n in ATTACKS}
for f in files:
    img = Image.open(f).convert("RGB")
    for name, fn in ATTACKS.items():
        attack_dist[name].append(min_dist(to_bytes(fn(img)), phash[f]))

# 2) different photos (should NOT be caught)
same_item, diff_item = [], []
for a, b in itertools.permutations(files, 2):
    d = min_dist(Path(a).read_bytes(), phash[b])
    (same_item if group(a) == group(b) else diff_item).append(d)

print(f"{len(files)} photos | same-item pairs: {len(same_item)} | different-item pairs: {len(diff_item)}")
if same_item:
    print(f"Same-item distances: min={min(same_item)}, median={statistics.median(same_item)}")
print(f"Different-item distances: min={min(diff_item)}, median={statistics.median(diff_item)}\n")

pct = lambda lst, t: 100 * sum(d <= t for d in lst) / len(lst) if lst else 0.0
header = ["threshold"] + list(ATTACKS) + ["same_item_blocked%", "diff_item_blocked%"]
print(" | ".join(header))
rows = []
for t in range(2, 17, 2):
    row = [t] + [round(pct(attack_dist[n], t), 1) for n in ATTACKS] \
          + [round(pct(same_item, t), 1), round(pct(diff_item, t), 1)]
    rows.append(row)
    print(" | ".join(str(x) for x in row))

with open("phash_results.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(header)
    w.writerows(rows)
print("\nSaved phash_results.csv")