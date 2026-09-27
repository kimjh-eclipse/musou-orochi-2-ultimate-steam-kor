"""Turn garbled on-screen Hangul (Chinese text rendered with Korean glyphs) back into the original GBK text,
then find the catalog strings containing it."""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
cs = json.loads((ROOT / "mapping/ko_charset.json").read_text(encoding="utf-8"))["chars"]
for s in sys.argv[1:]:
    raw = b"".join(bytes.fromhex(cs[c]) if c in cs else c.encode("gbk", "replace") for c in s)
    zh = raw.decode("gbk", "replace")
    print(s, "->", zh)
    key = zh.rstrip("。")[:6]
    for l in (ROOT / "extract/pc_catalog.jsonl").open(encoding="utf-8"):
        r = json.loads(l)
        if r["CHS"] and key.encode("gbk", "ignore") in bytes.fromhex(r["CHS"]):
            print("   ", r["entry"], r["path"], bytes.fromhex(r["JPN"]).decode("cp932", "replace")[:60].replace("\n", "/"))
