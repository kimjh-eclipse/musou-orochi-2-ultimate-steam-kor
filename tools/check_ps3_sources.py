"""Confirm PS3 jp_iso = original and hdd0 = v20260910b final, by the hashes recorded in the PS3 handoff."""
import hashlib, json
from pathlib import Path

JP = Path(r"C:\Emul\Switch\패치유틸.xdeltaUI\work_wo3u\jp_iso\PS3_GAME\USRDIR")
HDD = Path(r"C:\Emul\PS3\rpcs3-v0.0.27-14986-db7f84f9_win64\dev_hdd0\disc\BLJM61084\PS3_GAME\USRDIR")
EXPECT = {
    "EBOOT.BIN": ("E59780C5DC9C9F27B1CECEF4C3D71AACC9E7C55B86323C7F25BEF54BFFFABF66", "BCC84BDA4C20C984021CB5432190120209CDE960053858A2E2377BF931EC0612"),
    "LINKDATA.IDX": ("11872DF3C8E1026FBFBD9A4A508D2E20B3926DCD45F011C5F609168629A8558B", "D7DDDEC52C1771808CD804CC60D19CBBFC2BD20600FCDF14DA38362A744DD85A"),
    "LINKDATA.BIN": ("E8A491D3FA5B06154B98A56745DA598423555E32DF17DE73D24A4F2E0A6EDAA9", "CEE8EA70120B012301A65C21280401D7E776A6D1BCCFA39AA92BCBC75ACC2FFB"),
}


def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        while b := f.read(1 << 24):
            h.update(b)
    return h.hexdigest().upper()


out = {}
for name, (orig, final) in EXPECT.items():
    for label, root, want in (("jp_iso", JP, orig), ("hdd0", HDD, final)):
        got = sha(root / name)
        out[f"{label}/{name}"] = {"sha256": got, "expected": want, "ok": got == want}
        print(label, name, "OK" if got == want else f"MISMATCH {got}", flush=True)
Path(__file__).resolve().parents[1].joinpath("inventory", "ps3_sources_check.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
