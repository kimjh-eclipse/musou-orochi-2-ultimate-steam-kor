"""Merge ko_<batch>_*.jsonl ({n, ko}) with queue_<batch>.jsonl into pc_ko_<batch>.jsonl ({jp, ko}).

Checks per item: ESC control sequence list (⟨E⟩C#, ⟨E⟩R, ⟨E⟩P?) identical and in order, printf tokens
(%s %d %2d %02d %w %2w %03w ...) identical multiset, leading 2-digit notice code kept, every character encodable.
"""
import collections, json, re, sys
from pathlib import Path
from ko_encode import can_encode

ROOT = Path(__file__).resolve().parents[1]
TM = ROOT / "translation_memory"
batch = sys.argv[1]
ESC = re.compile(r"⟨E⟩(?:C\d|R|P.|A.|O.)")
FMT = re.compile(r"%\d*[sdw]|%0\d+[dw]")
queue = {json.loads(l)["n"]: json.loads(l) for l in (TM / f"queue_{batch}.jsonl").open(encoding="utf-8")}
done, errors = {}, []
for p in sorted(TM.glob(f"ko_{batch}_*.jsonl")):
    for ln, l in enumerate(p.open(encoding="utf-8"), 1):
        if not l.strip():
            continue
        r = json.loads(l)
        q = queue.get(r["n"])
        if q is None:
            errors.append((p.name, ln, "unknown n"))
            continue
        jp, ko = q["jp"], r["ko"]
        if ESC.findall(jp) != ESC.findall(ko):
            errors.append((r["n"], "esc", ESC.findall(jp), ESC.findall(ko)))
        if collections.Counter(FMT.findall(jp)) != collections.Counter(FMT.findall(ko)):
            errors.append((r["n"], "fmt", FMT.findall(jp), FMT.findall(ko)))
        m = re.match(r"^[0-9][0-9]", jp)
        if m and not ko.startswith(m.group()):
            errors.append((r["n"], "code", m.group(), ko[:4]))
        real = ko.replace("⟨E⟩", "\x1b")
        if not can_encode(real):
            bad = [c for c in real if not can_encode(c)]
            errors.append((r["n"], "glyph", bad))
        done[r["n"]] = real
missing = sorted(set(queue) - set(done))
print(f"{batch}: translated {len(done)}/{len(queue)}, missing {len(missing)} {missing[:20]}, errors {len(errors)}")
for e in errors[:40]:
    print("  ", e)
if not errors:
    with (TM / f"pc_ko_{batch}.jsonl").open("w", encoding="utf-8") as f:
        for n in sorted(done):
            f.write(json.dumps({"jp": queue[n]["jp"].replace("⟨E⟩", "\x1b"), "ko": done[n]}, ensure_ascii=False) + "\n")
    print("wrote", TM / f"pc_ko_{batch}.jsonl")
