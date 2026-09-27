"""Build a Korean CHS-slot package: font (entry 38) + text entries -> build/<version>/LINKIDX_CHS.BIN, LINKFILE_CHS.BIN."""
import json, sys, time
from pathlib import Path
from pc_idx import Archive
from build_font import build as build_font
from build_text import build_all
from build_images import build_all as build_images
from pack_lang import write_part, sha256

ROOT = Path(__file__).resolve().parents[1]
FONT_ENTRY = 38


def main(version):
    t = time.time()
    out_dir = ROOT / "build" / version
    charset = json.loads((ROOT / "mapping/ko_charset.json").read_text(encoding="utf-8"))["chars"]
    font, font_rep = build_font(Archive("CHS").read(FONT_ENTRY), charset)
    texts, stats, problems, queue = build_all()
    images, image_rep = build_images()
    overlap = set(images) & (set(texts) | {FONT_ENTRY})
    assert not overlap, f"image specs overlap text/font entries: {overlap}"
    repl = dict(texts)
    repl.update(images)
    repl[FONT_ENTRY] = font
    pack = write_part("CHS", repl, out_dir)
    rep = {"version": version, "built": time.strftime("%Y-%m-%d %H:%M:%S"), "font": font_rep, "text_stats": stats,
           "text_problems": problems, "images": image_rep, "untranslated_queue": len(queue), "entries_replaced": len(repl),
           "files": {n: {"size": (out_dir / n).stat().st_size, "sha256": sha256(out_dir / n)}
                     for n in ("LINKIDX_CHS.BIN", "LINKFILE_CHS.BIN")}}
    (out_dir / "build_report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    with (out_dir / "untranslated_queue.jsonl").open("w", encoding="utf-8") as f:
        for q in queue:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in rep.items() if k not in ("text_problems",)}, ensure_ascii=False, indent=1))
    print(f"{time.time()-t:.0f}s")


if __name__ == "__main__":
    main(sys.argv[1])
