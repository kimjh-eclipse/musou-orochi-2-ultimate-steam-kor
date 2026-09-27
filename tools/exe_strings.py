"""Survey NUL-terminated text strings in WO3U.exe: GBK (CHS) and CP932 (JPN) runs with CJK content.

Writes extract/exe_strings.json: [{off, enc, len, slot, text}] where slot = bytes up to the next non-NUL
(the room available for in-place replacement). Prints clusters (runs of strings closer than 64 bytes).
"""
import json, re
from pathlib import Path

EXE = Path(r"C:\Program Files (x86)\Steam\steamapps\common\WARRIORS OROCHI 3 Ultimate\WO3U.exe")
ROOT = Path(__file__).resolve().parents[1]
d = EXE.read_bytes()


def cjk(t):
    return sum(1 for c in t if "\u4e00" <= c <= "\u9fff" or "\u3040" <= c <= "\u30ff")


out = []
for m in re.finditer(rb"[^\x00]{4,}", d):
    raw = m.group()
    if not any(b >= 0x80 for b in raw):
        continue
    for enc in ("gbk", "cp932"):
        try:
            t = raw.decode(enc)
        except UnicodeDecodeError:
            continue
        if cjk(t) >= 2 and all(c.isprintable() or c in "\n\x1b\t" for c in t):
            end = m.end()
            nxt = end
            while nxt < len(d) and d[nxt] == 0:
                nxt += 1
            out.append({"off": m.start(), "enc": enc, "len": len(raw), "slot": nxt - m.start(), "text": t})
            break
(ROOT / "extract/exe_strings.json").write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
# clusters
cl, cur = [], [out[0]] if out else []
for s in out[1:]:
    if s["off"] - (cur[-1]["off"] + cur[-1]["slot"]) < 64 and s["enc"] == cur[-1]["enc"]:
        cur.append(s)
    else:
        cl.append(cur)
        cur = [s]
if cur:
    cl.append(cur)
for c in cl:
    if len(c) >= 5:
        print(f"{c[0]['enc']:5} {c[0]['off']:#x}-{c[-1]['off']:#x}  {len(c):4} strings  e.g. {c[0]['text'][:24]!r} / {c[len(c)//2]['text'][:24]!r}")
print("total", len(out), "gbk", sum(s["enc"] == "gbk" for s in out), "cp932", sum(s["enc"] == "cp932" for s in out))
