"""Issue #17 (2026-10-11): fit live mission messages into 21 cells (see msg22_queue.py for the width model).
User decision: shorten in bulk, e.g. "%s, 오다군 본진 방어를 위해 진군 개시!" -> "%s, 오다군 본진 방어로 진군!".

1. Phrase rules, applied in order to over-limit messages only, stopping once a message fits.
2. Hand-shortened rows, tidied (tidy(): "," between names -> "·", space before the verb; such a row may take
   21.5 cells, still inside the measured ~22) (translation_memory/msg22_parts/answer*.jsonl, keyed by [entry, path]) for the rest.
Checks: same 2-digit prefix, same ESC colour-code sequence, same %s count, no line break, <= 21 cells, encodable.
writes translation_memory/pc_ko_R_msg22.jsonl (applied after pc_ko_A..Q)
"""
import glob, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.stdout.reconfigure(encoding="utf-8")
from ko_encode import can_encode
from msg22_queue import ESC, LIMIT, cells, current, messages

RULES = [
    (r"진군을 개시!", "진군!"),
    (r"진군 개시!", "진군!"),
    (r"진군 시작!", "진군!"),
    (r"이동 개시!", "이동!"),
    (r"이동 시작!", "이동!"),
    (r"의 패주에 주의하라!", " 패주 주의!"),
    (r"인 듯하다!", "인 듯!"),
    (r"한 듯하다!", "한 듯!"),
    (r"는 듯하다!", "는 듯!"),
    (r"된 듯하다!", "된 듯!"),
    (r"의 패주에 주의하며 ", " 패주 주의, "),
]
RULES = [(re.compile(a), b) for a, b in RULES]


def by_rules(ko):
    for pat, rep in RULES:
        if cells(ko[2:]) <= LIMIT:
            break
        ko = pat.sub(rep, ko)
    return ko


def tidy(ko):
    """Hand rows packed names together to save half cells; restore readable spacing (costs at most 0.5 cell each)."""
    ko = re.sub(r",(?=C)", "·", ko)              # list of highlighted names: 이름·이름
    ko = re.sub(r",(?=[가-힣])", ", ", ko)
    ko = re.sub(r"R(?=C)", "R ", ko)
    ko = re.sub(r"R(?=(격파|출현|신뢰|공격|격노|교전))", "R ", ko)
    return ko


def check(old, new, limit=LIMIT):
    why = []
    if new[:2] != old[:2]:
        why.append("prefix")
    if ESC.findall(new) != ESC.findall(old):
        why.append("colour codes")
    if new.count("%s") != old.count("%s"):
        why.append("%s count")
    if "\\n" in new or "\n" in new:
        why.append("line break")
    if cells(new[2:]) > limit:
        why.append(f"{cells(new[2:])} cells")
    if not can_encode(ESC.sub("", new)):
        why.append("not encodable")
    return why


def main():
    hand, exempt, manual = {}, set(), set()
    for p in sorted(glob.glob(str(ROOT / "translation_memory/msg22_parts/answer*.jsonl"))):
        for l in open(p, encoding="utf-8"):
            if l.strip():
                a = json.loads(l)
                hand[json.dumps(a["key"])] = a["ko"]
                if "manual" in Path(p).name:
                    manual.add(json.dumps(a["key"]))
                if a.get("exempt"):
                    exempt.add(json.dumps(a["key"]))
    out, left, bad = {}, [], []
    for e, path, jp, ko in messages(current()):
        if not re.match(r"\d\d", ko) or cells(ko[2:]) <= LIMIT:
            continue
        k = json.dumps([e, path])
        if k in hand:
            new = tidy(hand[k])
            if k in exempt:   # msg22_manual.py: names alone exceed the bar; key words first, codes may reorder
                why = [w for w in check(ko, new, 99) if w != "colour codes"]
                if sorted(ESC.findall(new)) != sorted(ESC.findall(ko)):
                    why.append("colour code set")
            else:
                why = check(ko, new, LIMIT + (0.5 if new != hand[k] or k in manual else 0))
        else:
            new = by_rules(ko)
            why = check(ko, new)
        if why:
            (bad if k in hand else left).append({"key": [e, path], "jp": jp, "ko": new, "orig_ko": ko,
                                                  "cells": cells(new[2:]), "why": why})
            continue
        out[jp] = new
    q = ROOT / "translation_memory/msg22_left.jsonl"
    q.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in left), encoding="utf-8")
    for b in bad:
        print("BAD", b["key"], b["why"], ESC.sub("^", b["ko"]))
    p = ROOT / "translation_memory/pc_ko_R_msg22.jsonl"
    p.write_text("".join(json.dumps({"jp": k, "ko": v}, ensure_ascii=False) + "\n" for k, v in out.items()),
                 encoding="utf-8")
    print(f"{len(out)} fitted -> {p.name}; {len(left)} still over -> {q.name}; {len(bad)} bad hand rows")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
