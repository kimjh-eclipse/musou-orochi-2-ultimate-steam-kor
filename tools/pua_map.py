"""Pair JPN CP932 user-defined codes (F040-F9FC) with CHS GBK user-defined codes, record by record."""
import collections, json, re, struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = Path(r"C:\Program Files (x86)\Steam\steamapps\common\WARRIORS OROCHI 3 Ultimate\WO3U.exe")
chs_codes = set(struct.unpack_from("<9888H", EXE.read_bytes(), 0xB936EE)[1:-1])


def cp932_tokens(b):
    out, i = [], 0
    while i < len(b):
        c = b[i]
        if 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xFC:
            out.append(b[i:i + 2]); i += 2
        else:
            out.append(b[i:i + 1]); i += 1
    return out


def gbk_tokens(b):
    out, i = [], 0
    while i < len(b):
        if b[i] >= 0x81:
            out.append(b[i:i + 2]); i += 2
        else:
            out.append(b[i:i + 1]); i += 1
    return out


is_jp_pua = lambda t: len(t) == 2 and 0xF0 <= t[0] <= 0xF9
is_gbk_ud = lambda t: len(t) == 2 and (0xAA <= t[0] <= 0xAF and t[1] >= 0xA1 or 0xF8 <= t[0] <= 0xFE and t[1] >= 0xA1 or 0xA1 <= t[0] <= 0xA7 and t[1] < 0xA1)

pairs = collections.defaultdict(collections.Counter)
for l in (ROOT / "extract/pc_catalog.jsonl").open(encoding="utf-8"):
    r = json.loads(l)
    if not r["CHS"]:
        continue
    j = [t for t in cp932_tokens(bytes.fromhex(r["JPN"])) if is_jp_pua(t)]
    if not j:
        continue
    c = [t for t in gbk_tokens(bytes.fromhex(r["CHS"])) if is_gbk_ud(t)]
    if len(j) == len(c):
        for a, b in zip(j, c):
            pairs[a.hex()][b.hex()] += 1

table = {}
for a, cnt in sorted(pairs.items()):
    b, n = cnt.most_common(1)[0]
    table[a] = b
    print(a, "->", b, f"{n}/{sum(cnt.values())}", "in CHS table" if int(b, 16) in chs_codes else "NOT IN TABLE", dict(cnt) if len(cnt) > 1 else "")
(ROOT / "mapping/pua_cp932_to_gbk.json").write_text(json.dumps(table, indent=1), encoding="utf-8")
ud_in_table = sorted(c for c in chs_codes if is_gbk_ud(struct.pack(">H", c)))
print("GBK user-defined codes present in CHS table:", len(ud_in_table), [hex(c) for c in ud_in_table[:40]])
