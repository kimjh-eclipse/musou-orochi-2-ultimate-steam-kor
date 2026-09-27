"""Scan WO3U.exe for Chinese/Japanese text in every plausible encoding: GBK/CP932 (NUL-terminated),
UTF-8 and UTF-16LE. Reports counts per encoding and region, and writes extract/exe_scan_all.json."""
import json, re, collections
from pathlib import Path

EXE = Path(r"C:\Program Files (x86)\Steam\steamapps\common\WARRIORS OROCHI 3 Ultimate\WO3U.exe")
ROOT = Path(__file__).resolve().parents[1]
d = EXE.read_bytes()
HAN = lambda c: "\u4e00" <= c <= "\u9fff"
KANA = lambda c: "\u3040" <= c <= "\u30ff"
COMMON_ZH = set("的了是在不我有他这中大来上国个到说们为子和你地出道也时年得就那要下以生会自着去之过家学对可她里后小么心多天而能好都然没日于起还发成事只作当想看文无开手十用主行方又如前所本见经头面公同三已老从动两长知民样现分将外但身些与高意进把法此实回二理美点月明其种声全工己话儿者向情部正名定女问力机给等几很业最间新什打便位因重被走电四第门相次东政海口使教西再平真听世气信北少关并内加化由却代军产入先山五太水万市眼体别处总才场师书比住员九笑性通目华报立马命张活难神数件安表原车白应路期叫死常提感金何更反合放做系计或司利受光王果亲界及今京务制解各任至清物台象记边共风战干接它许八特觉望直服毛林题建南度统色字请交爱让认算论百吃义科怎元社术结六功指思非流每青管夫连远资队跟带花快条院变联言权往展该领传近留红治决周保达办运武半候七必城父强步完革深区即求品士转量空甚众技轻程告江语英基派满式李息写呢识极令黄德收脸钱党倒未持取设始版双历越史商千片容研像找友孩站广改议形委早房音火际则首单据导影失拿网香似斯专石若兵弟谁校读志飞观争究包组造落视济喜离虽坏兴医")
out = []


def add(enc, off, text):
    zh = sum(1 for c in text if c in COMMON_ZH)
    ja = sum(1 for c in text if KANA(c))
    han = sum(1 for c in text if HAN(c))
    if han + ja >= 2 and (zh >= 1 or ja >= 1):
        out.append({"enc": enc, "off": off, "lang": "JPN" if ja else "CHS", "text": text})


for m in re.finditer(rb"[^\x00]{4,}", d):
    raw = m.group()
    if not any(b >= 0x80 for b in raw):
        continue
    for enc in ("utf-8", "cp932", "gbk"):
        try:
            t = raw.decode(enc)
        except UnicodeDecodeError:
            continue
        if all(c.isprintable() or c in "\n\x1b\t\r" for c in t):
            if enc == "cp932" and not any(KANA(c) for c in t):
                continue  # kanji-only cp932 is ambiguous with gbk; let gbk decide
            add(enc, m.start(), t)
            break
# UTF-16LE: runs of 2-byte units, at even and odd alignment
for align in (0, 1):
    for m in re.finditer(rb"(?:[^\x00][\x00-\xff]|\x00[^\x00]){3,}", d[align:]):
        raw = m.group()
        if len(raw) % 2:
            raw = raw[:-1]
        try:
            t = raw.decode("utf-16le")
        except UnicodeDecodeError:
            continue
        if any(HAN(c) or KANA(c) for c in t) and all(c.isprintable() or c in "\n\r\t" for c in t):
            add("utf-16le", m.start() + align, t)
(ROOT / "extract/exe_scan_all.json").write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
c = collections.Counter((o["enc"], o["lang"]) for o in out)
print(c)
for key in c:
    xs = [o for o in out if (o["enc"], o["lang"]) == key]
    print(key, [f"{o['off']:#x}:{o['text'][:18]!r}" for o in xs[:6]])
