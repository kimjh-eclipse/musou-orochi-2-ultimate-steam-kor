"""Korean charset for the CHS slot: which Hangul/extra glyphs go into which GBK hanzi cells.

Donors = CHS code-table entries that are hanzi (GB2312 B0A1-F7FE and GBK extension), i.e. every cell whose
Chinese glyph disappears. Kept = symbols (A1-A9 rows incl. kana/full-width forms), user-defined AAxx, ASCII row.
Chosen glyphs, in priority order until the donors run out:
  1. Hangul used by the translation   2. KS X 1001 (2,350)   3. compatibility jamo ㄱ-ㅣ
  4. symbols missing from the table (・ ＊ ♪)   5. remaining syllables, common finals first
Chosen characters retain priority order; GB2312 donors are allocated before GBK extensions.
The used Hangul plus KS X 1001 must fit entirely in GB2312 donor slots.
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
    # Priority order meets the safest codes first. GB2312 hanzi (both bytes >= A1) are what the Chinese text
    # actually uses. GBK extension codes (trail 40-A0, trail < 80 looks like ASCII) are suspected in
    # subtitle/help corruption; the runtime cause is not yet proven. Used + KS X 1001 fit in GB2312.
    def safety(c):
        lead, trail = c >> 8, c & 0xFF
        if 0xB0 <= lead <= 0xF7 and trail >= 0xA1:
            return 0
        return 1 if trail >= 0x80 else 2
    safe_donors = sorted(donors, key=lambda c: (safety(c), c))
    n_gb = sum(1 for c in donors if safety(c) == 0)
    assert len(set(used_hangul) | set(ksx1001())) <= n_gb, "used Hangul + KS X 1001 exceed GB2312 donors"
    assign = {ch: f"{code:04x}" for ch, code in zip(chosen, safe_donors)}
    return {"version": 1, "donor_count": len(donors), "chosen": len(chosen),
            "syllables": sum(1 for c in chosen if 0xAC00 <= ord(c) <= 0xD7A3), "chars": assign}


if __name__ == "__main__":
    audit = json.loads((ROOT / "mapping/charset_audit.json").read_text(encoding="utf-8"))
    used = set(audit["hangul"])
    # every Hangul in the current Korean text (PS3 matches + new translations), not only the first audit
    for l in (ROOT / "mapping/pc_match.jsonl").open(encoding="utf-8"):
        used.update(c for c in (json.loads(l).get("ko") or "") if "가" <= c <= "힣")
    for p in (ROOT / "translation_memory").glob("pc_ko_*.jsonl"):
        for l in p.open(encoding="utf-8"):
            if l.strip():
                used.update(c for c in json.loads(l)["ko"] if "가" <= c <= "힣")
    res = build(sorted(used))
    (ROOT / "mapping/ko_charset.json").write_text(json.dumps(res, ensure_ascii=False, indent=0), encoding="utf-8")
    print({k: v for k, v in res.items() if k != "chars"})
    missing_used = [c for c in audit["hangul"] if c not in res["chars"]]
    print("used Hangul not assigned:", missing_used)
    print("sample", list(res["chars"].items())[:5], list(res["chars"].items())[-5:])
