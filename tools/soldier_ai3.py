"""Optional gameplay test: raise the AI level of combat troops from 0 to 3 (clone-officer level).

Unit data: LINKFILE_000.BIN @0x44CDA, 2206 slots x 40 bytes; u16 at slot+32 = AI level (layout from PythWare's
WO3 Steel Unit Editor, values per DC gallery post 66415: troops 0 / clone officers 3 / playable 5 / Lu Bu 7).
Slots are selected by their real name (u16 name id at slot+0 -> name table 33 [5,id], Japanese, via
mapping/pc_match.jsonl). The English list in Kybernes-Tools wo3_names.txt does NOT line up with the slots (v1 of this
tool used it and hit shops, civilians, siege weapons; 2026-10-02). Combat troops -> 3; Orochi-side troops (Orochi
soldier / Tamamo soldier names, and combat troops using the demon models 221/226) and the leader types
什長/副将/拠点兵長/守備兵長 -> 5. Siege weapons, civilians,
shops, animals, messengers, supply/engineer units, support casters/ninjas, reserve and per-stage officer slots stay 0.

usage: soldier_ai3.py status|plan|apply|restore [game dir] [--all=N  (test: every target slot -> N)]
apply  : refuses unless every target slot is 0 and the block matches the saved original; writes the original block
         to <game>/WO3U_soldier_ai.orig (once) before patching.
restore: writes the saved original block back.
"""
import hashlib, json, struct, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\WARRIORS OROCHI 3 Ultimate")
MATCH = Path(__file__).resolve().parents[1] / "mapping/pc_match.jsonl"
OFF, COUNT, SIZE, FIELD = 0x44CDA, 2206, 40, 32
# byte 34 = unit class (troop 0, officer 1, siege 15-19, captain 20, civilian 22), byte 35 = behaviour type (officers 3/4,
# troops per weapon class). PythWare's Super Aggressive AI (Nexus warriorsorochi3/1) sets every slot to class 1 / type 4
# / AI 65535; the AI level alone only makes troops close in faster (user test 2026-10-02), so targets also get 1 / 4.
CLASS, BEHAVIOUR = 34, 35
OFFICER_AI = True
NEW, OROCHI = 1, 3  # v6 (2026-10-02): v5 3/5 with officer AI was too eager to close in
# ranged troops keep their own class/behaviour (archers class 2, throwers class 7, guns/archers/casters type 1/20/80/88)
RANGED_CLASS, RANGED_TYPE = {2, 7}, {1, 20, 80, 88}
# v8 (2026-10-07, GitHub issue #9): officer AI broke cavalry (behaviour 2: they stood still), raised ranged troops (bomb
# throwers) attacked almost endlessly, and shield troops (behaviour 96) are kept as a breather - all three untouched.
KEEP_TYPE = {2, 96}
OFFICER_LEVEL = 0  # 0 = keep officers as they are (2026-10-02: user declined 7, it would also apply to allies). Set 7 to raise named officers
OROCHI_NAMES = {"遠呂智兵", "玉藻前兵"}
LEADER_NAMES = {"什長", "副将", "拠点兵長", "守備兵長"}  # 2026-10-02 user: leaders also 5
OROCHI_MODELS = {221, 226}
COMBAT_JP = {
    "卒伯", "兵卒", "什長", "副将", "守備兵長", "拠点兵長", "衛兵", "弓兵", "投石兵", "騎兵", "親衛隊", "火弓兵", "民兵",
    "遠呂智兵", "玉藻前兵", "女性兵士", "ディンガル兵", "フランス兵", "戦国兵", "野武士", "鉄砲兵", "忍者", "女忍者",
    "突忍", "旋忍", "爆忍", "忍者隊長", "雑賀鉄砲兵", "雑賀衆", "盾兵", "強盾兵", "剛盾兵", "堅兵", "強堅兵", "剛堅兵",
    "不動兵", "強不動兵", "剛不動兵", "護兵", "強護兵", "剛護兵", "耐兵", "強耐兵", "剛耐兵", "斧兵", "強斧兵", "剛斧兵",
    "山賊", "土賊", "義賊", "盗賊", "強賊", "力士", "強力士", "剛力士", "氷剣兵", "強氷剣兵", "剛氷剣兵", "炎槍兵",
    "強炎槍兵", "剛炎槍兵", "邪剣兵", "強邪剣兵", "剛邪剣兵", "火忍", "火上忍", "炸忍", "炸上忍", "火矢兵", "炎矢兵",
    "銃兵", "強銃兵", "剛銃兵", "強投岩兵", "火術士", "大火術士", "雷術士", "大雷術士", "呪術士", "大呪術士", "氷術士",
    "大氷術士", "風術士", "大風術士", "仙術士", "大仙術士", "邪術士", "大邪術士", "気功士", "大気功士",
    "兵士１", "兵士２", "兵士３", "兵士４", "兵士５", "兵士６", "兵士７", "兵士８",
}

def read_block(game):
    with open(game / "LINKFILE_000.BIN", "rb") as h:
        h.seek(OFF)
        b = h.read(COUNT * SIZE)
    assert len(b) == COUNT * SIZE
    return b


VANILLA_SHA = "a6b62541dbe6cef5"  # first 16 hex of sha256 of the unmodified Steam DE block (2026-10-02)


def name_table():
    t = {}
    for line in MATCH.open(encoding="utf-8"):
        if '"entry": 33' not in line:
            continue
        r = json.loads(line)
        if r["entry"] == 33 and r["path"][0] == 5:
            t[r["path"][1]] = (r["jp"] or "").replace("\n", "")
    return t


def targets(block):
    """[(slot, jp name, new value)] for combat-troop slots that are 0 in the given (original) block."""
    names = name_table()
    out = []
    for i in range(COUNT):
        nid, model = struct.unpack_from("<HxxxxH", block, i * SIZE)
        n = names.get(nid, "")
        beh = block[i * SIZE + BEHAVIOUR]
        if beh in KEEP_TYPE or block[i * SIZE + CLASS] in RANGED_CLASS or beh in RANGED_TYPE:
            continue  # v8: cavalry / shield / ranged troops are left exactly as they are
        if n in COMBAT_JP and struct.unpack_from("<H", block, i * SIZE + FIELD)[0] == 0:
            orochi = n in OROCHI_NAMES or n in LEADER_NAMES or model in OROCHI_MODELS
            out.append((i, n, OROCHI if orochi else NEW))
    return out


def officer_slots(block):
    """Named officers: class 1 with AI level 3 (generic named) or 5 (playable/bosses)."""
    return [i for i in range(COUNT) if block[i * SIZE + CLASS] == 1
            and struct.unpack_from("<H", block, i * SIZE + FIELD)[0] in (3, 5)]


def build(block, t, offs):
    buf = bytearray(block)
    for i, _, v in t:
        struct.pack_into("<H", buf, i * SIZE + FIELD, v)
        ranged = block[i * SIZE + CLASS] in RANGED_CLASS or block[i * SIZE + BEHAVIOUR] in RANGED_TYPE
        if OFFICER_AI and not ranged:  # as PythWare's Super Aggressive AI: unit class 1 (officer) + behaviour type 4
            buf[i * SIZE + CLASS] = 1
            buf[i * SIZE + BEHAVIOUR] = 4
    for i in offs:
        struct.pack_into("<H", buf, i * SIZE + FIELD, OFFICER_LEVEL)
    return buf


def write_block(game, data):
    with open(game / "LINKFILE_000.BIN", "r+b") as h:
        h.seek(OFF)
        h.write(data)
    assert read_block(game) == data


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--all=")]
    force = [int(a[6:]) for a in sys.argv[1:] if a.startswith("--all=")]  # test: every target -> this value
    cmd = args[0] if args else "status"
    game = Path(args[1]) if len(args) > 1 else GAME
    orig = game / "WO3U_soldier_ai.orig"
    block = read_block(game)
    base = orig.read_bytes() if orig.exists() else block
    t = targets(base)
    if force:
        t = [(i, n, force[0]) for i, n, _ in t]
    cur = sum(1 for i, _, v in t if struct.unpack_from("<H", block, i * SIZE + FIELD)[0] == v)
    sha = hashlib.sha256(block).hexdigest()[:16]
    state = "vanilla" if sha == VANILLA_SHA else ("applied" if cur == len(t) and orig.exists() else "other")
    n5 = sum(1 for *_, v in t if v == OROCHI)
    print(f"block {sha} ({state})  targets {len(t)} (->{NEW}: {len(t) - n5}, ->{OROCHI}: {n5})  set: {cur}"
          f"  backup {'yes' if orig.exists() else 'no'}")
    offs = officer_slots(base) if OFFICER_LEVEL else []
    print(f"named officers {len(offs)} -> {OFFICER_LEVEL}  set: "
          f"{sum(1 for i in offs if struct.unpack_from('<H', block, i * SIZE + FIELD)[0] == OFFICER_LEVEL)}")
    if cmd == "plan":
        for i, n, v in t:
            print(f"  {i:4d} {n} -> {v}")
    elif cmd == "apply":
        if state != "vanilla":
            sys.exit("block is not the vanilla block - run restore (or Steam verify) first")
        if hashlib.sha256(base).hexdigest()[:16] != VANILLA_SHA:
            sys.exit("saved backup is not the vanilla block")
        if not orig.exists():
            orig.write_bytes(block)
            print("saved original block ->", orig.name)
        buf = build(block, t, offs)
        write_block(game, bytes(buf))
        diff = [k for k in range(len(buf)) if buf[k] != block[k]]
        assert all((k % SIZE) in (FIELD, CLASS, BEHAVIOUR) for k in diff)
        print(f"applied: {len(t)} troop + {len(offs)} officer slots, {len(diff)} bytes changed (AI level / class / behaviour only), readback ok")
    elif cmd == "table":  # C# data for the patcher option: "OOOOOooNN" per changed byte (block offset, vanilla, new)
        buf = build(base, t, offs)
        diff = [k for k in range(len(buf)) if buf[k] != base[k]]
        hexs = "".join(f"{k:05X}{base[k]:02X}{buf[k]:02X}" for k in diff)
        out = Path(__file__).resolve().parents[1] / "patcher/soldier_ai_table.txt"
        lines = [hashlib.sha256(base).hexdigest().upper(), hashlib.sha256(bytes(buf)).hexdigest().upper(), str(len(diff)), hexs]
        out.write_text("\n".join(lines) + "\n", encoding="ascii")
        print("table ->", out.name, len(diff), "bytes")
    elif cmd == "restore":
        if not orig.exists():
            sys.exit("no saved original block")
        write_block(game, base)
        print("restored original block, readback ok")


if __name__ == "__main__":
    main()
