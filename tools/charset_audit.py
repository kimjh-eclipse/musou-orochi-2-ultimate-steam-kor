"""What characters must the Korean CHS font provide, and does the CHS code table cover the non-Hangul ones?"""
import collections, json, struct, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = Path(r"C:\Program Files (x86)\Steam\steamapps\common\WARRIORS OROCHI 3 Ultimate\WO3U.exe")
codes = struct.unpack_from("<9888H", EXE.read_bytes(), 0xB936EE)[1:-1]
table_chars = {}
for c in codes:
    try:
        table_chars[struct.pack(">H", c).decode("gbk")] = c
    except UnicodeDecodeError:
        pass
print("CHS table codes", len(codes), "decodable", len(table_chars))

rows = [json.loads(l) for l in (ROOT / "mapping/pc_match.jsonl").open(encoding="utf-8")]
is_hangul = lambda ch: 0xAC00 <= ord(ch) <= 0xD7A3 or 0x3131 <= ord(ch) <= 0x318E
is_kana = lambda ch: 0x3040 <= ord(ch) <= 0x30FF
is_han = lambda ch: 0x4E00 <= ord(ch) <= 0x9FFF

jp_left = collections.Counter()
un_kinds = collections.Counter()
for r in rows:
    if r["level"] == "untranslated_ps3":
        s = r["jp"]
        k = "kana/kanji" if any(is_kana(c) or is_han(c) for c in s) else ("other-nonascii" if any(ord(c) > 127 for c in s) else "ascii")
        un_kinds[k] += 1
        if k == "kana/kanji":
            jp_left[r["entry"]] += 1
print("untranslated_ps3 composition", dict(un_kinds))
print("  top entries with Japanese left", jp_left.most_common(15))

ko_chars = collections.Counter()
for r in rows:
    if r["ko"] and r["level"] not in ("untranslated_ps3",):
        ko_chars.update(r["ko"])
hangul = {c for c in ko_chars if is_hangul(c)}
other = {c: n for c, n in ko_chars.items() if not is_hangul(c) and ord(c) > 0x7F}
print("distinct Hangul in Korean", len(hangul))
missing = {c: n for c, n in other.items() if c not in table_chars}
kanji_in_ko = {c: n for c, n in other.items() if is_han(c)}
kana_in_ko = {c: n for c, n in other.items() if is_kana(c)}
print("non-ASCII non-Hangul chars in Korean", len(other), "not in CHS table:", len(missing))
print("  missing:", sorted(missing.items(), key=lambda x: -x[1])[:60])
print("  kanji left in Korean:", len(kanji_in_ko), sorted(kanji_in_ko.items(), key=lambda x: -x[1])[:40])
print("  kana left in Korean:", len(kana_in_ko), sorted(kana_in_ko.items(), key=lambda x: -x[1])[:40])
# table composition by GBK lead byte region
reg = collections.Counter()
for c in codes:
    lead = c >> 8
    reg["A1-A9 symbols" if 0xA1 <= lead <= 0xA9 else "B0-F7 GB2312 hanzi" if 0xB0 <= lead <= 0xF7 else "GBK ext"] += 1
print("table regions", dict(reg))
json.dump({"hangul": sorted(hangul), "other": other, "missing": missing}, open(ROOT / "mapping/charset_audit.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
