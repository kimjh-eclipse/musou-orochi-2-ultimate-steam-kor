r"""One-off edit (2026-10-07): second unit option '장수 공격성 한 단계 올리기' (named officers AI 3->4, 5->6), separate
checkbox / --officer-ai, sharing the LINKFILE_000.BIN unit table with the soldier option.

Both options change disjoint bytes, so the block can no longer be judged by one whole-block hash. State per option =
all its bytes vanilla / all changed / mixed; the block is ours when reverting every applied option (incl. the old
v20261002b soldier table) gives the vanilla hash. Re-running refreshes the officer table only.
"""
import shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CS = HERE / "WO3USteamPatch.cs"
s = CS.read_text(encoding="utf-8-sig")
van, tgt, cnt, diff = (HERE / "officer_ai_table.txt").read_text(encoding="ascii").split()
assert len(diff) == int(cnt) * 9
B, E = "    // <officer-ai-table>\n", "    // </officer-ai-table>\n"
table = (B + f"    // {cnt} bytes: every named officer (class 1, AI 3 or 5) one AI level up\n"
         f'    private const string OfficerDiff =\n' +
         "".join(f'        "{diff[i:i + 108]}"{" +" if i + 108 < len(diff) else ";"}\n' for i in range(0, len(diff), 108)) + E)


def rep(old, new, count=1):
    global s
    if s.count(old) != count:
        sys.exit(f"expected {count} x {old[:70]!r}, found {s.count(old)}")
    s = s.replace(old, new)


if B in s:
    s = s[:s.index(B)] + table + s[s.index(E) + len(E):]
    CS.write_text(s, encoding="utf-8-sig")
    print("officer table refreshed")
    sys.exit(0)

shutil.copy2(CS, HERE.parent / "backup" / "WO3USteamPatch.cs.before_officer_option")
rep("    // </soldier-ai-old>\n", "    // </soldier-ai-old>\n" + table)

# --- options / work item / CLI
rep("        public bool? Soldier;   // null = leave the soldier setting as it is\n",
    "        public bool? Soldier;   // null = leave the soldier setting as it is\n        public bool? Officer;   // null = leave the officer setting as it is\n")
rep("        public bool Soldier;\n    }\n\n    private sealed class UiResult",
    "        public bool Soldier;\n        public bool Officer;\n    }\n\n    private sealed class UiResult")
rep("""            else if (arg.Equals("--no-soldier-ai", StringComparison.OrdinalIgnoreCase))
                options.Soldier = false;
""", """            else if (arg.Equals("--no-soldier-ai", StringComparison.OrdinalIgnoreCase))
                options.Soldier = false;
            else if (arg.Equals("--officer-ai", StringComparison.OrdinalIgnoreCase))
                options.Officer = true;
            else if (arg.Equals("--no-officer-ai", StringComparison.OrdinalIgnoreCase))
                options.Officer = false;
""")
rep("[--soldier-ai | --no-soldier-ai]", "[--soldier-ai | --no-soldier-ai] [--officer-ai | --no-officer-ai]")
rep("""        if (options.VerifyOnly)
        {
            PrintCommon003State(dir, loadedPack);
            PrintSoldierState(dir);
        }
        else if (result == 0 && options.Restore)
        {
            SetCommon003(dir, loadedPack, false);
            SetSoldier(dir, false, true);
        }
        else if (result == 0)
        {
            SetCommon003(dir, loadedPack, true);
            if (options.Soldier.HasValue)
                SetSoldier(dir, options.Soldier.Value, false);
        }""", """        if (options.VerifyOnly)
        {
            PrintCommon003State(dir, loadedPack);
            PrintSoldierState(dir);
        }
        else if (result == 0 && options.Restore)
        {
            SetCommon003(dir, loadedPack, false);
            SetSoldier(dir, false, true);
            SetOfficer(dir, false, true);
        }
        else if (result == 0)
        {
            SetCommon003(dir, loadedPack, true);
            if (options.Soldier.HasValue)
                SetSoldier(dir, options.Soldier.Value, false);
            if (options.Officer.HasValue)
                SetOfficer(dir, options.Officer.Value, false);
        }""")

# --- GUI: second checkbox under the first, everything below moves down 24 px
rep("        private readonly CheckBox soldierCheck;\n", "        private readonly CheckBox soldierCheck;\n        private readonly CheckBox officerCheck;\n")
rep("            ClientSize = new Size(900, 884);", "            ClientSize = new Size(900, 908);")
rep("""            soldierCheck.Location = new Point(24, 442);
            Controls.Add(soldierCheck);
""", """            soldierCheck.Location = new Point(24, 442);
            Controls.Add(soldierCheck);

            officerCheck = new CheckBox();
            officerCheck.Text = OfficerCheckText;
            officerCheck.Checked = false;
            officerCheck.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
            officerCheck.ForeColor = Color.FromArgb(120, 30, 30);
            officerCheck.AutoSize = true;
            officerCheck.Location = new Point(24, 466);
            Controls.Add(officerCheck);
""")
for a, b in [("logLabel.Location = new Point(22, 479);", "logLabel.Location = new Point(22, 503);"),
             ("logBox.SetBounds(22, 501, 856, 280);", "logBox.SetBounds(22, 525, 856, 280);"),
             ('AddButton("상태 검사", 22, 797,', 'AddButton("상태 검사", 22, 821,'),
             ('AddButton("한국어 패치 적용", 172, 797,', 'AddButton("한국어 패치 적용", 172, 821,'),
             ('AddButton("원본 복구", 412, 797,', 'AddButton("원본 복구", 412, 821,'),
             ('AddButton("닫기", 758, 797,', 'AddButton("닫기", 758, 821,'),
             ("progressBar.SetBounds(22, 851, 650, 16);", "progressBar.SetBounds(22, 875, 650, 16);"),
             ("statusLabel.SetBounds(685, 846, 193, 25);", "statusLabel.SetBounds(685, 870, 193, 25);")]:
    rep(a, b)
rep("""        private void RefreshSoldierCheck()
        {""", """        private const string OfficerCheckText = "선택: 장수 공격성 한 단계 올리기 — 일반 장수 3→4, 무쌍 장수 5→6 (아군 장수에도 적용)";

        private void RefreshSoldierCheck()
        {
            try
            {
                string folder = folderPathBox.Text.Trim().Trim('"');
                bool officerOn = !String.IsNullOrWhiteSpace(folder) && OfficerOn(ResolveGameDir(folder));
                officerCheck.Text = OfficerCheckText + (officerOn ? "  [현재 적용됨 — 유지하려면 체크]" : "");
            }
            catch
            {
                officerCheck.Text = OfficerCheckText;
            }""")
rep("""                        "\\r\\n\\r\\n'병사 공격성 강화'는 적용하지 않습니다 (적용되어 있었다면 원래대로 되돌립니다).") +""",
    """                        "\\r\\n\\r\\n'병사 공격성 강화'는 적용하지 않습니다 (적용되어 있었다면 원래대로 되돌립니다).") +
                    (officerCheck.Checked ? "\\r\\n선택 기능 '장수 공격성 한 단계 올리기'도 적용합니다." :
                        "\\r\\n'장수 공격성 한 단계 올리기'는 적용하지 않습니다 (적용되어 있었다면 원래대로 되돌립니다).") +""")
rep("Foreign = foreign, Soldier = soldierCheck.Checked });", "Foreign = foreign, Soldier = soldierCheck.Checked, Officer = officerCheck.Checked });")
rep("""                options.Soldier = work.Operation == UiOperation.Patch ? (bool?)work.Soldier : null;
""", """                options.Soldier = work.Operation == UiOperation.Patch ? (bool?)work.Soldier : null;
                options.Officer = work.Operation == UiOperation.Patch ? (bool?)work.Officer : null;
""")
rep("warningCheck, soldierCheck, verifyButton,", "warningCheck, soldierCheck, officerCheck, verifyButton,")

# --- state model: per option, block judged by reverting every applied option
a, b = s.index("    private enum SoldierState\n"), s.index("    private static bool EqualBytes(")
s = s[:a] + r'''    private enum SoldierState
    {
        Missing,
        Vanilla,
        Applied,
        OldApplied,
        Other
    }

    private static byte[] ReadSoldierBlock(string dir)
    {
        string path = Path.Combine(dir, SoldierFile);
        if (!File.Exists(path) || new FileInfo(path).Length < SoldierOffset + SoldierBlockSize)
            return null;
        byte[] block = new byte[SoldierBlockSize];
        using (FileStream stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read))
        {
            stream.Position = SoldierOffset;
            ReadFully(stream, block, 0, block.Length);
        }
        return block;
    }

    private static string BlockHash(byte[] block)
    {
        using (SHA256 sha = SHA256.Create())
            return ToHex(sha.ComputeHash(block));
    }

    // diff = "위치(5)·원래 값(2)·새 값(2)" 16진 반복. 0 = 모두 원래 값, 1 = 모두 새 값, 2 = 섞임
    private static int DiffState(byte[] block, string diff)
    {
        bool allOld = true, allNew = true;
        for (int i = 0; i < diff.Length; i += 9)
        {
            int at = Convert.ToInt32(diff.Substring(i, 5), 16);
            allOld &= block[at] == Convert.ToByte(diff.Substring(i + 5, 2), 16);
            allNew &= block[at] == Convert.ToByte(diff.Substring(i + 7, 2), 16);
        }
        return allNew ? 1 : allOld ? 0 : 2;
    }

    // on = 원래 값 → 새 값, off = 새 값 → 원래 값.
    private static byte[] ApplySoldierDiff(byte[] block, string diff, bool on)
    {
        for (int i = 0; i < diff.Length; i += 9)
        {
            int at = Convert.ToInt32(diff.Substring(i, 5), 16);
            byte vanilla = Convert.ToByte(diff.Substring(i + 5, 2), 16);
            byte changed = Convert.ToByte(diff.Substring(i + 7, 2), 16);
            if (block[at] != (on ? vanilla : changed))
                throw new InvalidDataException("유닛 데이터 표가 예상과 다릅니다 (위치 " + at + ").");
            block[at] = on ? changed : vanilla;
        }
        return block;
    }

    // 적용된 우리 변경(이전 판 병사 표 포함)을 모두 걷어낸 표가 원본이면 true. oldIndex = 적용된 이전 판 병사 표 번호(-1 없음)
    private static bool UnitBlockIsOurs(byte[] block, out int oldIndex)
    {
        byte[] copy = (byte[])block.Clone();
        oldIndex = -1;
        for (int k = 0; k < SoldierOldDiffs.Length; k++)
            if (DiffState(copy, SoldierOldDiffs[k]) == 1)
            {
                ApplySoldierDiff(copy, SoldierOldDiffs[k], false);
                oldIndex = k;
                break;
            }
        foreach (string diff in new[] { SoldierDiff, OfficerDiff })
            if (DiffState(copy, diff) == 1)
                ApplySoldierDiff(copy, diff, false);
        return BlockHash(copy) == SoldierVanillaSha;
    }

    private static SoldierState SoldierStateOf(string dir)
    {
        byte[] block = ReadSoldierBlock(dir);
        if (block == null)
            return SoldierState.Missing;
        int old;
        if (!UnitBlockIsOurs(block, out old))
            return SoldierState.Other;
        if (old >= 0)
            return SoldierState.OldApplied;
        return DiffState(block, SoldierDiff) == 1 ? SoldierState.Applied : SoldierState.Vanilla;
    }

    private static bool OfficerOn(string dir)
    {
        byte[] block = ReadSoldierBlock(dir);
        int old;
        return block != null && UnitBlockIsOurs(block, out old) && DiffState(block, OfficerDiff) == 1;
    }

    private static void PrintSoldierState(string dir)
    {
        SoldierState state = SoldierStateOf(dir);
        if (state == SoldierState.Applied)
            Console.WriteLine("[*] 선택 기능 '병사 공격성 강화'가 적용되어 있습니다.");
        else if (state == SoldierState.OldApplied)
            Console.WriteLine("[*] 이전 버전의 '병사 공격성 강화'가 적용되어 있습니다. 패치 적용 때 새 설정으로 바꾸거나(체크) 되돌립니다(해제).");
        else if (state == SoldierState.Vanilla)
            Console.WriteLine("[*] 선택 기능 '병사 공격성 강화'는 적용되어 있지 않습니다(원본).");
        else if (state == SoldierState.Other)
            Console.WriteLine("[*] " + SoldierFile + " 의 유닛 데이터가 다른 프로그램으로 수정되어 있어 병사·장수 공격성 옵션을 쓸 수 없습니다.");
        if (state != SoldierState.Other && state != SoldierState.Missing)
            Console.WriteLine(OfficerOn(dir) ? "[*] 선택 기능 '장수 공격성 한 단계 올리기'가 적용되어 있습니다."
                                             : "[*] 선택 기능 '장수 공격성 한 단계 올리기'는 적용되어 있지 않습니다(원본).");
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

    private static void SetSoldier(string dir, bool on, bool quietIfVanilla)
    {
        SetUnitOption(dir, SoldierDiff, on, quietIfVanilla, "병사 공격성 강화", "근접 병사 263 슬롯");
    }

    private static void SetOfficer(string dir, bool on, bool quietIfVanilla)
    {
        SetUnitOption(dir, OfficerDiff, on, quietIfVanilla, "장수 공격성 한 단계 올리기", "이름 있는 장수 1,560 슬롯");
    }

    // on = 적용, off = 원래대로. 표에 우리 변경 말고 다른 변경이 있으면(다른 유닛 모드 등) 건드리지 않는다.
    private static void SetUnitOption(string dir, string diff, bool on, bool quietIfVanilla, string label, string scope)
    {
        byte[] block = ReadSoldierBlock(dir);
        if (block == null)
            return;
        int old;
        if (!UnitBlockIsOurs(block, out old))
        {
            if (on)
            {
                SetConsoleColor(ConsoleColor.Yellow);
                Console.WriteLine("[!] " + SoldierFile + " 의 유닛 데이터가 원본이 아니라(다른 유닛 모드 등) '" + label + "'을(를) 건너뜁니다.");
                Console.WriteLine("    Steam '게임 파일 무결성 검사'로 원본을 받은 뒤 다시 적용할 수 있습니다.");
                ResetConsoleColor();
            }
            return;
        }
        if (old >= 0 && diff == SoldierDiff)
        {
            ApplySoldierDiff(block, SoldierOldDiffs[old], false);
            WriteSoldierBlock(dir, block);
            WriteOk("이전 버전의 '병사 공격성 강화'를 원래대로 되돌렸습니다.");
        }
        int state = DiffState(block, diff);
        if (on == (state == 1))
        {
            if (on)
                WriteOk("'" + label + "'은(는) 이미 적용되어 있습니다.");
            else if (!quietIfVanilla)
                WriteOk("'" + label + "'은(는) 적용되어 있지 않습니다(원본 유지).");
            return;
        }
        WriteSoldierBlock(dir, ApplySoldierDiff(block, diff, on));
        byte[] now = ReadSoldierBlock(dir);
        int after;
        if (!UnitBlockIsOurs(now, out after) || DiffState(now, diff) != (on ? 1 : 0))
            throw new InvalidDataException("'" + label + "' " + (on ? "적용" : "해제") + " 후 검증에 실패했습니다. Steam '게임 파일 무결성 검사'로 원본을 받으세요.");
        WriteOk(on ? "'" + label + "' 적용 및 검증 완료 (" + SoldierFile + ", " + scope + ")"
                   : "'" + label + "'을(를) 원래대로 되돌리고 검증했습니다 (" + SoldierFile + ")");
    }

''' + s[b:]
CS.write_text(s, encoding="utf-8-sig")
print("ok")
