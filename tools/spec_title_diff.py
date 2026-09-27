"""Title prompt (6036 t1) and difficulty labels (6049 t6 easy/normal/hard x2, t7 asura x2)."""
import json
from pathlib import Path
import numpy as np
from label_boxes import boxes, load
from image_labels import SANS, SERIF

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / "mapping/images"

d, t, im = load(6036, 1)
bb = im.getchannel("A").point(lambda v: 255 if v > 12 else 0).getbbox()
box = [bb[0], bb[1], bb[2] - 1, bb[3] - 1]
spec = {"entry": 6036, "textures": [{"tex": 1, "labels": [
    {"box": box, "ko": "시작 버튼을 누르십시오", "font": SANS, "shear": 0.14, "extend_w": t["w"] - box[0] - 4}]}]}
(out / "06036.json").write_text(json.dumps(spec, ensure_ascii=False, indent=0), encoding="utf-8")

tex = []
for ti, kos in ((6, ["쉬움", "쉬움", "보통", "보통", "어려움", "어려움"]), (7, ["수라", "수라"])):
    d, t, im = load(6049, ti)
    bx = boxes(np.asarray(im.getchannel("A")), gap=2.0)
    assert len(bx) == len(kos), (ti, bx)
    tex.append({"tex": ti, "labels": [{"box": b, "ko": k, "shear": 0.0, "extend_w": t["w"] - b[0] - 4} for b, k in zip(bx, kos)]})
(out / "06049.json").write_text(json.dumps({"entry": 6049, "textures": tex}, ensure_ascii=False, indent=0), encoding="utf-8")
print("ok")
