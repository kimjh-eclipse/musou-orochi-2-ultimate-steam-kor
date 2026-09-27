"""Apply mapping/images/*.json label specs to CHS G1T entries -> {entry: new bytes}; optional previews."""
import json, sys
from pathlib import Path
from PIL import Image
from pc_idx import Archive
from g1t_pc import parse, decode, replace
from image_labels import apply_labels

ROOT = Path(__file__).resolve().parents[1]


def build_all(preview=False):
    chs = Archive("CHS")
    out, report = {}, []
    for p in sorted((ROOT / "mapping/images").glob("*.json")):
        spec = json.loads(p.read_text(encoding="utf-8"))
        e = spec["entry"]
        d = chs.read(e)
        g = parse(d)
        for ts in spec["textures"]:
            t = g["tex"][ts["tex"]]
            im = decode(d, t)
            if "boot_notice" in ts:
                from boot_notice import render_notice
                new, rep = render_notice(im, ts["boot_notice"])
            elif "copy" in ts:
                # the source slot already shows language-neutral art (e.g. JPN "Clear!" where CHS drew 通关!)
                se, sti = ts.get("src", [e, ts["tex"]])
                sd = Archive(ts["copy"]).read(se)
                st = parse(sd)["tex"][sti]
                assert (st["w"], st["h"]) == (t["w"], t["h"]), (e, ts["tex"])
                new, rep = decode(sd, st), [{"text": "copy " + ts["copy"], "condense": None}]
            elif "overpaint" in ts:
                from image_overpaint import overpaint
                jd = Archive("JPN").read(e)
                jim = decode(jd, parse(jd)["tex"][ts["tex"]])
                o = ts["overpaint"]
                new, rep = overpaint(im, jim, o["region"], o["ko"])
                rep = [rep]
            elif "logo_over" in ts:
                from image_logo import place_logo_over
                o = ts["logo_over"]
                new, rep = place_logo_over(im, o["src"], o["rect"], o["erase"], grow=o.get("grow", 1.0))
                rep = [rep]
            elif "logo" in ts:
                from image_logo import place_logo
                new, rep = place_logo(im, ts["logo"]["src"], ts["logo"]["rect"])
                rep = [rep]
            else:
                new, rep = apply_labels(im, ts["labels"])
            d = replace(d, t, new)
            back = decode(d, t)
            report.append({"entry": e, "tex": ts["tex"], "labels": rep})
            if preview:
                pv = ROOT / "extract/preview"
                pv.mkdir(parents=True, exist_ok=True)
                bb = im.getchannel("A").getbbox()
                pair = Image.new("RGBA", (bb[2] - bb[0] + 20) * 2 and ((bb[2] - bb[0]) * 2 + 20, bb[3] - bb[1]), (40, 44, 60, 255))
                pair.alpha_composite(im.crop(bb), (0, 0))
                pair.alpha_composite(back.crop((bb[0], bb[1], min(t["w"], bb[2] + (bb[2] - bb[0]) // 2), bb[3])), ((bb[2] - bb[0]) + 20, 0))
                s = min(1.0, 1600 / pair.width)
                pair.resize((int(pair.width * s), int(pair.height * s))).save(pv / f"{e:05d}_t{ts['tex']}.png")
        out[e] = d
    return out, report


if __name__ == "__main__":
    out, rep = build_all(preview=True)
    for r in rep:
        print(r["entry"], r["tex"], [(x.get("text", "logo"), x.get("condense")) for x in r["labels"]])
