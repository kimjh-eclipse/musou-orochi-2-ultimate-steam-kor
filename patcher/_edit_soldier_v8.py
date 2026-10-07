r"""One-off edit (2026-10-07, issue #9): soldier option v8 + recognise the soldier data written by older patchers.

- table block gains SoldierOldShas / SoldierOldDiffs from patcher/soldier_ai_table_<version>.txt (previous releases)
- an old applied block is first reverted with its own diff (-> vanilla), then the current choice is applied
- slot counts in comments/messages follow the current table
_edit_soldier_option.py keeps refreshing the current table; run this after it.
"""
import glob, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CS = HERE / "WO3USteamPatch.cs"
s = CS.read_text(encoding="utf-8-sig")
shutil.copy2(CS, HERE.parent / "backup" / "WO3USteamPatch.cs.before_soldier_v8")


def rep(old, new, count=1):
    global s
    if s.count(old) != count:
        sys.exit(f"expected {count} x {old[:70]!r}, found {s.count(old)}")
    s = s.replace(old, new)


olds = []
for p in sorted(glob.glob(str(HERE / "soldier_ai_table_v*.txt"))):
    van, tgt, cnt, diff = Path(p).read_text(encoding="ascii").split()
    assert len(diff) == int(cnt) * 9
    olds.append((Path(p).stem.replace("soldier_ai_table_", ""), van, tgt, diff))
END = "    // </soldier-ai-table>\n"
old_block = "    // <soldier-ai-old>\n"
for ver, van, tgt, diff in olds:
    old_block += f"    // {ver}\n"
old_block += "    private static readonly string[] SoldierOldShas = { " + ", ".join(f'"{t}"' for _, _, t, _ in olds) + " };\n"
old_block += "    private static readonly string[] SoldierOldDiffs =\n    {\n"
for ver, van, tgt, diff in olds:
    old_block += "        " + " +\n        ".join(f'"{diff[i:i + 108]}"' for i in range(0, len(diff), 108)) + ",\n"
old_block += "    };\n    // </soldier-ai-old>\n"
if "    // <soldier-ai-old>\n" in s:
    a, b = s.index("    // <soldier-ai-old>\n"), s.index("    // </soldier-ai-old>\n") + len("    // </soldier-ai-old>\n")
    s = s[:a] + old_block + s[b:]
else:
    rep(END, END + old_block)

    rep("""    // LINKFILE_000.BIN (공통 데이터) 0x44CDA 의 유닛 표(2206 슬롯 x 40 바이트). 전투 병사 364 슬롯의 AI 단계(+32)를
    // 1(일반)/3(오로치·대장)으로 올리고, 근접 병사 289 슬롯은 분류(+34)=1·행동(+35)=4(무장 AI)로 바꾼다.
    // 원거리 병사·병기·백성·동물·장수는 그대로.""", """    // LINKFILE_000.BIN (공통 데이터) 0x44CDA 의 유닛 표(2206 슬롯 x 40 바이트). 근접 병사 263 슬롯의 AI 단계(+32)를
    // 1(일반)/3(오로치·대장)으로 올리고 분류(+34)=1·행동(+35)=4(무장 AI)로 바꾼다. 기마병(행동 2)·방패병(행동 96)·
    // 원거리 병사·병기·백성·동물·장수는 그대로(이슈 #9: 기마병이 멈추고 원거리 병사가 과하게 공격).
    // 이전 버전 패처가 쓴 표(SoldierOld*)도 알아보고 먼저 원본으로 되돌린 뒤 지금 선택을 적용한다.""")
    rep("""        Applied,
        Other
    }""", """        Applied,
        OldApplied,
        Other
    }""")
    rep("""        if (hash == SoldierTargetSha)
            return SoldierState.Applied;
        return SoldierState.Other;""", """        if (hash == SoldierTargetSha)
            return SoldierState.Applied;
        if (Array.IndexOf(SoldierOldShas, hash) >= 0)
            return SoldierState.OldApplied;
        return SoldierState.Other;""")
    rep("""        if (state == SoldierState.Applied)
            Console.WriteLine("[*] 선택 기능 '병사 공격성 강화'가 적용되어 있습니다.");""",
        """        if (state == SoldierState.Applied)
            Console.WriteLine("[*] 선택 기능 '병사 공격성 강화'가 적용되어 있습니다.");
        else if (state == SoldierState.OldApplied)
            Console.WriteLine("[*] 이전 버전의 '병사 공격성 강화'가 적용되어 있습니다. 패치 적용 때 새 설정으로 바꾸거나(체크) 되돌립니다(해제).");""")
    rep("""                soldierCheck.Checked = !String.IsNullOrWhiteSpace(folder) && SoldierStateOf(ResolveGameDir(folder)) == SoldierState.Applied;""",
        """                SoldierState current = String.IsNullOrWhiteSpace(folder) ? SoldierState.Missing : SoldierStateOf(ResolveGameDir(folder));
                soldierCheck.Checked = current == SoldierState.Applied || current == SoldierState.OldApplied;""")
    # SetSoldier: old -> vanilla first, diff application factored out
    rep("""        if (on == (state == SoldierState.Applied))
        {""", """        if (state == SoldierState.OldApplied)
        {
            int old = Array.IndexOf(SoldierOldShas, BlockHash(ReadSoldierBlock(dir)));
            WriteSoldierBlock(dir, ApplySoldierDiff(ReadSoldierBlock(dir), SoldierOldDiffs[old], false));
            if (SoldierStateOf(dir) != SoldierState.Vanilla)
                throw new InvalidDataException("이전 버전 '병사 공격성 강화'를 되돌린 뒤 검증에 실패했습니다. Steam '게임 파일 무결성 검사'로 원본을 받으세요.");
            WriteOk("이전 버전의 '병사 공격성 강화'를 원래대로 되돌렸습니다.");
            state = SoldierState.Vanilla;
            if (!on)
                return;
        }
        if (on == (state == SoldierState.Applied))
        {""")
    rep("""        byte[] block = ReadSoldierBlock(dir);
        for (int i = 0; i < SoldierDiff.Length; i += 9)
        {
            int at = Convert.ToInt32(SoldierDiff.Substring(i, 5), 16);
            byte vanilla = Convert.ToByte(SoldierDiff.Substring(i + 5, 2), 16);
            byte changed = Convert.ToByte(SoldierDiff.Substring(i + 7, 2), 16);
            if (block[at] != (on ? vanilla : changed))
                throw new InvalidDataException("병사 데이터 표가 예상과 다릅니다 (위치 " + at + ").");
            block[at] = on ? changed : vanilla;
        }
        using (FileStream stream = new FileStream(Path.Combine(dir, SoldierFile), FileMode.Open, FileAccess.ReadWrite, FileShare.None))
        {
            stream.Position = SoldierOffset;
            stream.Write(block, 0, block.Length);
            stream.Flush(true);
        }
        SoldierState now""", """        WriteSoldierBlock(dir, ApplySoldierDiff(ReadSoldierBlock(dir), SoldierDiff, on));
        SoldierState now""")
    rep("""        WriteOk(on ? "'병사 공격성 강화' 적용 및 검증 완료 (" + SoldierFile + ", 전투 병사 364 슬롯)\"""",
        """        WriteOk(on ? "'병사 공격성 강화' 적용 및 검증 완료 (" + SoldierFile + ", 근접 병사 263 슬롯)\"""")
    rep("""    private static void SetSoldier(string dir, bool on, bool quietIfVanilla)""", """    private static string BlockHash(byte[] block)
    {
        using (SHA256 sha = SHA256.Create())
            return ToHex(sha.ComputeHash(block));
    }

    // diff = "위치(5)·원래 값(2)·새 값(2)" 16진 반복. on = 원래 값 → 새 값, off = 새 값 → 원래 값.
    private static byte[] ApplySoldierDiff(byte[] block, string diff, bool on)
    {
        for (int i = 0; i < diff.Length; i += 9)
        {
            int at = Convert.ToInt32(diff.Substring(i, 5), 16);
            byte vanilla = Convert.ToByte(diff.Substring(i + 5, 2), 16);
            byte changed = Convert.ToByte(diff.Substring(i + 7, 2), 16);
            if (block[at] != (on ? vanilla : changed))
                throw new InvalidDataException("병사 데이터 표가 예상과 다릅니다 (위치 " + at + ").");
            block[at] = on ? changed : vanilla;
        }
        return block;
    }

    private static void WriteSoldierBlock(string dir, byte[] block)
    {
        using (FileStream stream = new FileStream(Path.Combine(dir, SoldierFile), FileMode.Open, FileAccess.ReadWrite, FileShare.None))
        {
            stream.Position = SoldierOffset;
            stream.Write(block, 0, block.Length);
            stream.Flush(true);
        }
    }

    private static void SetSoldier(string dir, bool on, bool quietIfVanilla)""")

CS.write_text(s, encoding="utf-8-sig")
print("ok, old tables:", [o[0] for o in olds])
