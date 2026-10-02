r"""One-off edit: add the optional 'soldier aggression' setting to WO3USteamPatch.cs (GUI checkbox + CLI flags).

Data comes from patcher/soldier_ai_table.txt (tools/soldier_ai3.py table); re-running only refreshes the table block.
"""
import shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CS = HERE / "WO3USteamPatch.cs"
TABLE = HERE / "soldier_ai_table.txt"
s = CS.read_text(encoding="utf-8-sig")
vanilla, target, count, diff = TABLE.read_text(encoding="ascii").split()
assert len(diff) == int(count) * 9

BEGIN, END = "    // <soldier-ai-table>\n", "    // </soldier-ai-table>\n"
table = (BEGIN +
         f'    private const string SoldierVanillaSha = "{vanilla}";\n'
         f'    private const string SoldierTargetSha = "{target}";\n'
         f'    private const string SoldierDiff =\n' +
         "".join(f'        "{diff[i:i + 108]}"{" +" if i + 108 < len(diff) else ";"}\n' for i in range(0, len(diff), 108)) +
         END)


def rep(old, new, count=1):
    global s
    if s.count(old) != count:
        sys.exit(f"expected {count} x {old[:70]!r}, found {s.count(old)}")
    s = s.replace(old, new)


if BEGIN in s:  # refresh data only
    a, b = s.index(BEGIN), s.index(END) + len(END)
    s = s[:a] + table + s[b:]
else:
    shutil.copy2(CS, HERE.parent / "backup" / "WO3USteamPatch.cs.before_soldier_option")

    # --- options
    rep("        public ForeignDll Foreign;\n    }\n\n    // what to do",
        "        public ForeignDll Foreign;\n        public bool? Soldier;   // null = leave the soldier setting as it is\n    }\n\n    // what to do")
    rep("        public ForeignDll Foreign;\n    }\n\n    private sealed class UiResult",
        "        public ForeignDll Foreign;\n        public bool Soldier;\n    }\n\n    private sealed class UiResult")

    # --- GUI: checkbox below the warnings, everything under it moves down 34 px
    rep("        private readonly CheckBox warningCheck;\n",
        "        private readonly CheckBox warningCheck;\n        private readonly CheckBox soldierCheck;\n")
    rep("            ClientSize = new Size(900, 850);", "            ClientSize = new Size(900, 884);")
    rep("""            warningGroup.Controls.Add(warningCheck);
""", """            warningGroup.Controls.Add(warningCheck);

            soldierCheck = new CheckBox();
            soldierCheck.Text = "선택: 병사 공격성 강화 — 일반 병사가 무장처럼 적극적으로 공격합니다 (난이도 상승, 게임 언어와 무관, 해제 후 적용하면 원래대로)";
            soldierCheck.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
            soldierCheck.ForeColor = Color.FromArgb(120, 30, 30);
            soldierCheck.AutoSize = true;
            soldierCheck.Location = new Point(24, 442);
            Controls.Add(soldierCheck);
""")
    rep("            logLabel.Location = new Point(22, 445);", "            logLabel.Location = new Point(22, 479);")
    rep("            logBox.SetBounds(22, 467, 856, 280);", "            logBox.SetBounds(22, 501, 856, 280);")
    rep('            verifyButton = AddButton("상태 검사", 22, 763,', '            verifyButton = AddButton("상태 검사", 22, 797,')
    rep('            patchButton = AddButton("한국어 패치 적용", 172, 763,', '            patchButton = AddButton("한국어 패치 적용", 172, 797,')
    rep('            restoreButton = AddButton("원본 복구", 412, 763,', '            restoreButton = AddButton("원본 복구", 412, 797,')
    rep('            closeButton = AddButton("닫기", 758, 763,', '            closeButton = AddButton("닫기", 758, 797,')
    rep("            progressBar.SetBounds(22, 817, 650, 16);", "            progressBar.SetBounds(22, 851, 650, 16);")
    rep("            statusLabel.SetBounds(685, 812, 193, 25);", "            statusLabel.SetBounds(685, 846, 193, 25);")
    # checkbox follows the folder's current state
    rep("""        private void UpdateDefaultBackup()
        {
            if (backupCustomized)
                return;
            string folder = folderPathBox.Text.Trim().Trim('"');""", """        private void UpdateDefaultBackup()
        {
            RefreshSoldierCheck();
            if (backupCustomized)
                return;
            string folder = folderPathBox.Text.Trim().Trim('"');""")
    rep("""        private void FormDragEnter(object sender, DragEventArgs e)""", """        private void RefreshSoldierCheck()
        {
            try
            {
                string folder = folderPathBox.Text.Trim().Trim('"');
                soldierCheck.Checked = !String.IsNullOrWhiteSpace(folder) && SoldierStateOf(ResolveGameDir(folder)) == SoldierState.Applied;
            }
            catch
            {
                soldierCheck.Checked = false;
            }
        }

        private void FormDragEnter(object sender, DragEventArgs e)""")
    rep("            worker.RunWorkerAsync(new UiWorkItem { Operation = operation, TargetPath = targetPath, BackupPath = backupPath, Foreign = foreign });",
        "            worker.RunWorkerAsync(new UiWorkItem { Operation = operation, TargetPath = targetPath, BackupPath = backupPath, Foreign = foreign, Soldier = soldierCheck.Checked });")
    rep("                options.Foreign = work.Foreign;\n",
        "                options.Foreign = work.Foreign;\n                options.Soldier = work.Operation == UiOperation.Patch ? (bool?)work.Soldier : null;\n")
    rep("                warningCheck, verifyButton, patchButton, restoreButton, closeButton\n",
        "                warningCheck, soldierCheck, verifyButton, patchButton, restoreButton, closeButton\n")
    rep("""            SetBusy(false, "대기 중");
""", """            SetBusy(false, "대기 중");
            RefreshSoldierCheck();
""")

    # --- CLI
    rep("""            else if (arg.Equals("--skip-dll", StringComparison.OrdinalIgnoreCase))
                options.Foreign = ForeignDll.Skip;
""", """            else if (arg.Equals("--skip-dll", StringComparison.OrdinalIgnoreCase))
                options.Foreign = ForeignDll.Skip;
            else if (arg.Equals("--soldier-ai", StringComparison.OrdinalIgnoreCase))
                options.Soldier = true;
            else if (arg.Equals("--no-soldier-ai", StringComparison.OrdinalIgnoreCase))
                options.Soldier = false;
""")
    rep("[--chain-dll | --overwrite-dll | --skip-dll] [--no-pause]",
        "[--chain-dll | --overwrite-dll | --skip-dll] [--soldier-ai | --no-soldier-ai] [--no-pause]")

    # --- Run wrapper: Korean patch first, then the soldier setting
    rep("""    private static int Run(Options options)
    {
        WriteHeader();""", """    private static int Run(Options options)
    {
        int result = RunKorean(options);
        string dir = options.FolderPath;
        if (options.VerifyOnly)
            PrintSoldierState(dir);
        else if (result == 0 && options.Restore)
            SetSoldier(dir, false, true);
        else if (result == 0 && options.Soldier.HasValue)
            SetSoldier(dir, options.Soldier.Value, false);
        return result;
    }

    private static int RunKorean(Options options)
    {
        WriteHeader();""")

    # --- implementation
    rep("""    private static bool EqualBytes(byte[] left, byte[] right)""", r"""    // ------------------------------------------------------------------ 선택: 병사 공격성 강화
    // LINKFILE_000.BIN (공통 데이터) 0x44CDA 의 유닛 표(2206 슬롯 x 40 바이트). 전투 병사 364 슬롯의 AI 단계(+32)를
    // 1(일반)/3(오로치·대장)으로 올리고, 근접 병사 289 슬롯은 분류(+34)=1·행동(+35)=4(무장 AI)로 바꾼다.
    // 원거리 병사·병기·백성·동물·장수는 그대로. 아래 표는 바뀌는 바이트마다 "표 안 위치(5)·원래 값(2)·새 값(2)" 16진.
    // 원래 값이 표에 들어 있으므로 따로 백업하지 않고, 표 전체 SHA-256 으로 원본/적용 상태를 판별한다.
    private const string SoldierFile = "LINKFILE_000.BIN";
    private const long SoldierOffset = 0x44CDA;
    private const int SoldierBlockSize = 2206 * 40;
""" + "@@TABLE@@" + r"""
    private enum SoldierState
    {
        Missing,
        Vanilla,
        Applied,
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

    private static SoldierState SoldierStateOf(string dir)
    {
        byte[] block = ReadSoldierBlock(dir);
        if (block == null)
            return SoldierState.Missing;
        string hash;
        using (SHA256 sha = SHA256.Create())
            hash = ToHex(sha.ComputeHash(block));
        if (hash == SoldierVanillaSha)
            return SoldierState.Vanilla;
        if (hash == SoldierTargetSha)
            return SoldierState.Applied;
        return SoldierState.Other;
    }

    private static void PrintSoldierState(string dir)
    {
        SoldierState state = SoldierStateOf(dir);
        if (state == SoldierState.Applied)
            Console.WriteLine("[*] 선택 기능 '병사 공격성 강화'가 적용되어 있습니다.");
        else if (state == SoldierState.Vanilla)
            Console.WriteLine("[*] 선택 기능 '병사 공격성 강화'는 적용되어 있지 않습니다(원본).");
        else if (state == SoldierState.Other)
            Console.WriteLine("[*] " + SoldierFile + " 의 유닛 데이터가 다른 프로그램으로 수정되어 있어 '병사 공격성 강화'를 쓸 수 없습니다.");
    }

    // on = 적용, off = 원래대로. 원본도 적용 상태도 아니면(다른 유닛 모드 등) 건드리지 않는다.
    private static void SetSoldier(string dir, bool on, bool quietIfVanilla)
    {
        SoldierState state = SoldierStateOf(dir);
        if (state == SoldierState.Missing)
            return;
        if (state == SoldierState.Other)
        {
            if (on)
            {
                SetConsoleColor(ConsoleColor.Yellow);
                Console.WriteLine("[!] " + SoldierFile + " 의 유닛 데이터가 원본이 아니라(다른 유닛 모드 등) '병사 공격성 강화'를 건너뜁니다.");
                Console.WriteLine("    Steam '게임 파일 무결성 검사'로 원본을 받은 뒤 다시 적용할 수 있습니다.");
                ResetConsoleColor();
            }
            return;
        }
        if (on == (state == SoldierState.Applied))
        {
            if (on)
                WriteOk("'병사 공격성 강화'는 이미 적용되어 있습니다.");
            else if (!quietIfVanilla)
                WriteOk("'병사 공격성 강화'는 적용되어 있지 않습니다(원본 유지).");
            return;
        }
        byte[] block = ReadSoldierBlock(dir);
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
        SoldierState now = SoldierStateOf(dir);
        if (now != (on ? SoldierState.Applied : SoldierState.Vanilla))
            throw new InvalidDataException("'병사 공격성 강화' " + (on ? "적용" : "해제") + " 후 검증에 실패했습니다. Steam '게임 파일 무결성 검사'로 원본을 받으세요.");
        WriteOk(on ? "'병사 공격성 강화' 적용 및 검증 완료 (" + SoldierFile + ", 전투 병사 364 슬롯)"
                   : "'병사 공격성 강화'를 원래대로 되돌리고 검증했습니다 (" + SoldierFile + ")");
    }

    private static bool EqualBytes(byte[] left, byte[] right)""")
    s = s.replace("@@TABLE@@", table)

CS.write_text(s, encoding="utf-8-sig")
print("ok", "refresh" if BEGIN in s else "")
