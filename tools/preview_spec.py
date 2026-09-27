"""preview_spec.py out.png e:t [e:t ...] : apply mapping/images specs to single textures and stack original|new."""
import json, sys
from pathlib import Path
from PIL import Image
from pc_idx import Archive
from g1t_pc import parse, decode
from image_labels import apply_labels

ROOT = Path(__file__).resolve().parents[1]
chs = Archive("CHS")
tiles = []
for it in sys.argv[2:]:
    e, ti = map(int, it.split(":"))
    ts = next(x for x in json.loads((ROOT / f"mapping/images/{e:05d}.json").read_text(encoding="utf-8"))["textures"]
              if x["tex"] == ti)
    d = chs.read(e)
    im = decode(d, parse(d)["tex"][ti])
    if "copy" in ts:
        se, sti = ts.get("src", [e, ti])
        sd = Archive(ts["copy"]).read(se)
        new = decode(sd, parse(sd)["tex"][sti])
    else:
        new, _ = apply_labels(im, ts["labels"])
    bb = im.getchannel("A").getbbox()
    pair = Image.new("RGBA", ((bb[2] - bb[0]) * 2 + 16, bb[3] - bb[1]), (40, 44, 60, 255))
    pair.alpha_composite(im.crop(bb), (0, 0))
    pair.alpha_composite(new.crop(bb), (bb[2] - bb[0] + 16, 0))
    s = min(1.0, 1400 / pair.width)
    tiles.append(pair.resize((int(pair.width * s), int(pair.height * s))))
out = Image.new("RGBA", (1400, sum(t.height + 8 for t in tiles)), (20, 20, 20, 255))
y = 0
for t in tiles:
    out.alpha_composite(t, (0, y))
    y += t.height + 8
out.save(ROOT / "extract/peek" / sys.argv[1])
