"""Korean charset for the CHS slot: which Hangul/extra glyphs go into which GBK hanzi cells.

Donors = CHS code-table entries that are hanzi (GB2312 B0A1-F7FE and GBK extension), i.e. every cell whose
Chinese glyph disappears. Kept = symbols (A1-A9 rows incl. kana/full-width forms), user-defined AAxx, ASCII row.
Chosen glyphs, in priority order until the donors run out:
  1. Hangul used by the translation   2. KS X 1001 (2,350)   3. compatibility jamo ㄱ-ㅣ
  4. symbols missing from the table (・ ＊ ♪)   5. remaining syllables, common finals first
All chosen characters are sorted by code point and given to donors in ascending code order.
Output mapping/ko_charset.json: {"version", "donor_count", "chars": {char: "gbk hex"}}.
"""
import json, struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = Path(r"C:\Program Files (x86)\Steam\steamapps\common\WARRIORS OROCHI 3 Ultimate\WO3U.exe")
TABLE_OFF, TABLE_N = 0xB936EE, 9888
EXTRA_SYMBOLS = "・＊♪"


def table_codes():
    return struct.unpack_from(f"<{TABLE_N}H", EXE.read_bytes(), TABLE_OFF)[1:-1]


def is_hanzi_code(c):
    lead, trail = c >> 8, c & 0xFF
    if 0xB0 <= lead <= 0xF7 and trail >= 0xA1:
        return True  # GB2312 hanzi
    if 0x81 <= lead <= 0xA0 or (0xAA <= lead <= 0xFE and trail < 0xA1):
        return True  # GBK/3, GBK/4 extension hanzi
    return False


def ksx1001():
    out = []
    for lead in range(0xB0, 0xC9):
        for trail in range(0xA1, 0xFF):
            try:
                out.append(bytes([lead, trail]).decode("euc-kr"))
            except UnicodeDecodeError:
                pass
    return out


JONG_ORDER = [0, 4, 8, 21, 16, 1, 17, 19, 20, 7, 22, 23, 25, 26, 27, 24, 2, 9, 5, 18, 3, 6, 10, 11, 12, 13, 14, 15]


def extra_rank(ch):
    o = ord(ch) - 0xAC00
    cho, jung, jong = o // 588, (o % 588) // 28, o % 28
    return (JONG_ORDER.index(jong), cho, jung)


def build(used_hangul):
    codes = table_codes()
    donors = [c for c in codes if is_hanzi_code(c)]
    chosen = []
    seen = set()
    def add(chars):
        for ch in chars:
            if ch not in seen and len(chosen) < len(donors):
                seen.add(ch); chosen.append(ch)
    add(sorted(used_hangul))
    add(ksx1001())
    add([chr(c) for c in range(0x3131, 0x3164)])
    add(EXTRA_SYMBOLS)
    rest = sorted((chr(c) for c in range(0xAC00, 0xD7A4) if chr(c) not in seen), key=extra_rank)
    add(rest)
    ordered = sorted(chosen)
    assign = {ch: f"{code:04x}" for ch, code in zip(ordered, sorted(donors))}
    return {"version": 1, "donor_count": len(donors), "chosen": len(chosen),
            "syllables": sum(1 for c in chosen if 0xAC00 <= ord(c) <= 0xD7A3), "chars": assign}


if __name__ == "__main__":
    audit = json.loads((ROOT / "mapping/charset_audit.json").read_text(encoding="utf-8"))
    res = build(audit["hangul"])
    (ROOT / "mapping/ko_charset.json").write_text(json.dumps(res, ensure_ascii=False, indent=0), encoding="utf-8")
    print({k: v for k, v in res.items() if k != "chars"})
    missing_used = [c for c in audit["hangul"] if c not in res["chars"]]
    print("used Hangul not assigned:", missing_used)
    print("sample", list(res["chars"].items())[:5], list(res["chars"].items())[-5:])
