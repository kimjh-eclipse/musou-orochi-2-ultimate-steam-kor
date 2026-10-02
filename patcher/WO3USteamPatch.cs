using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Windows.Forms;
using Microsoft.Win32;

// 무쌍 오로치 2 얼티메이트 Steam판 (WARRIORS OROCHI 3 Ultimate Definitive Edition, App 1879330) 한국어 패처.
//
// - 게임의 중국어 간체 슬롯(LINKIDX_CHS.BIN / LINKFILE_CHS.BIN)을 한국어로 바꾼다. 다른 언어 파일은 건드리지 않는다.
// - 완성본 LINKFILE_CHS.BIN 은 원본과 배치가 다르므로 제자리 구간 기록 대신 재구성한다:
//   완성본 인덱스 순서대로, 팩에 있는 항목은 팩 데이터를, 나머지는 사용자의 원본 파일에서 그대로 복사한다.
// - 쓰기 전 원본에서 교체되는 항목만 복구 백업(.wo3u-backup)에 저장하고, 새 파일은 임시 파일에 만든 뒤
//   SHA-256 이 일치할 때만 교체한다. 복구도 같은 방식으로 원본을 재구성해 해시를 검증한다.
internal static class WO3USteamPatch
{
    private const string AppId = "1879330";
    private const string GameTitle = "무쌍 오로치 2 얼티메이트";
    private const string GameFolderName = "WARRIORS OROCHI 3 Ultimate";
    private const string GameExe = "WO3U.exe";
    private const string PackFileName = "WO3U_Steam_KR.pack";
    private const string PackMagic = "WO3USTM1";
    private const int PackFormatVersion = 2;
    private const string ProxyDllName = "dinput8.dll";
    private static readonly byte[] ProxyMarker = Encoding.ASCII.GetBytes("WO3U_KR dinput8 proxy, mode ");
    private const string BackupMagic = "WO3USBK1";
    private const int BackupFormatVersion = 1;
    private const string BackupExtension = ".wo3u-backup";
    private const string NewSuffix = ".wo3u-new";
    private const string ForeignDllSuffix = ".wo3u-orig";  // another program's dinput8.dll kept (not loaded) while ours is installed
    private const string ChainDllName = "dinput8_wo3u_chain.dll";  // another program's dinput8.dll that our proxy loads and forwards to
    private const string OldSuffix = ".wo3u-old";
    private const uint AttachParentProcess = 0xFFFFFFFF;
    private static readonly string[] TargetNames = { "LINKIDX_CHS.BIN", "LINKFILE_CHS.BIN" };

    private static string versionText = "(팩 미로드)";

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool AttachConsole(uint processId);

    // ------------------------------------------------------------------ 데이터 구조

    private sealed class FileRecord
    {
        public string Name;
        public long SourceSize;
        public byte[] SourceHash;
        public long TargetSize;
        public byte[] TargetHash;
    }

    private sealed class Pack
    {
        public string Version;
        public string Path;
        public List<FileRecord> Files = new List<FileRecord>();
        public byte[] TargetIdx;
        public byte[] Dll;      // dinput8.dll proxy (format 2), replaces the exe's own Chinese strings in memory
        public byte[] DllHash;
        public SortedDictionary<int, long> BlobOffsets = new SortedDictionary<int, long>();
        public Dictionary<int, long> BlobLengths = new Dictionary<int, long>();
    }

    private sealed class Backup
    {
        public string PackVersion;
        public string Path;
        public List<FileRecord> Files = new List<FileRecord>();   // Source = 원본, Target = 백업 당시 패치 완성본
        public byte[] SourceIdx;
        public SortedDictionary<int, long> BlobOffsets = new SortedDictionary<int, long>();
        public Dictionary<int, long> BlobLengths = new Dictionary<int, long>();
    }

    private struct IdxRecord
    {
        public long Offset;
        public long Unpacked;
        public long Stored;
        public long Compressed;
    }

    private enum FileState
    {
        Source,
        Target,
        Unknown
    }

    private sealed class Options
    {
        public string FolderPath;
        public string BackupPath;
        public bool Yes;
        public bool VerifyOnly;
        public bool Restore;
        public bool Pause;
        public ForeignDll Foreign;
        public bool? Soldier;   // null = leave the soldier setting as it is
    }

    // what to do with another program's dinput8.dll: ask (interactive console), chain (kept as dinput8_wo3u_chain.dll and
    // loaded by our proxy, both keep working), overwrite (kept as .wo3u-orig, not loaded), skip (data only)
    private enum ForeignDll
    {
        Ask,
        Chain,
        Overwrite,
        Skip
    }

    private sealed class ForeignDllForm : Form
    {
        public ForeignDll Choice = ForeignDll.Ask;

        public ForeignDllForm(string dir)
        {
            Text = "다른 " + ProxyDllName + " 발견";
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = false;
            StartPosition = FormStartPosition.CenterParent;
            ClientSize = new Size(560, 330);
            Font = new Font("Malgun Gothic", 9F);
            Label text = new Label();
            text.SetBounds(16, 14, 528, 250);
            text.Text = ForeignDllQuestion(dir);
            Controls.Add(text);
            AddButton("이어서 쓰기 (권장)", ForeignDll.Chain, 16, true);
            AddButton("덮어쓰기", ForeignDll.Overwrite, 176, false);
            AddButton("건너뛰기", ForeignDll.Skip, 296, false);
            AddButton("취소", ForeignDll.Ask, 416, false);
        }

        private void AddButton(string label, ForeignDll value, int x, bool isDefault)
        {
            Button b = new Button();
            b.Text = label;
            b.SetBounds(x, 280, isDefault ? 150 : 110, 32);
            b.Click += delegate { Choice = value; DialogResult = value == ForeignDll.Ask ? DialogResult.Cancel : DialogResult.OK; Close(); };
            Controls.Add(b);
            if (isDefault)
                AcceptButton = b;
            else if (value == ForeignDll.Ask)
                CancelButton = b;
        }
    }

    private enum UiOperation
    {
        Verify,
        Patch,
        Restore
    }

    private sealed class UiWorkItem
    {
        public UiOperation Operation;
        public string TargetPath;
        public string BackupPath;
        public ForeignDll Foreign;
        public bool Soldier;
    }

    private sealed class UiResult
    {
        public int ExitCode;
        public Exception Error;
        public UiOperation Operation;
        public string TargetPath;
    }

    private sealed class UiTextWriter : TextWriter
    {
        private readonly Action<string> append;

        public UiTextWriter(Action<string> appendText)
        {
            append = appendText;
        }

        public override Encoding Encoding { get { return Encoding.UTF8; } }

        public override void Write(string value)
        {
            if (!String.IsNullOrEmpty(value))
                append(value);
        }

        public override void Write(char value)
        {
            append(value.ToString());
        }

        public override void WriteLine(string value)
        {
            append((value ?? String.Empty) + Environment.NewLine);
        }

        public override void WriteLine()
        {
            append(Environment.NewLine);
        }
    }

    // ------------------------------------------------------------------ GUI

    private sealed class MainForm : Form
    {
        private readonly TextBox folderPathBox;
        private readonly Button folderBrowseButton;
        private readonly Button detectButton;
        private readonly TextBox backupBox;
        private readonly Button backupBrowseButton;
        private readonly CheckBox warningCheck;
        private readonly CheckBox soldierCheck;
        private readonly Button verifyButton;
        private readonly Button patchButton;
        private readonly Button restoreButton;
        private readonly Button closeButton;
        private readonly RichTextBox logBox;
        private readonly ProgressBar progressBar;
        private readonly Label statusLabel;
        private readonly BackgroundWorker worker;
        private bool busyState;
        private bool backupCustomized;

        public MainForm(string initialFolderPath, string initialBackupPath)
        {
            Text = GameTitle + " Steam판 한국어 패처 " + versionText;
            StartPosition = FormStartPosition.CenterScreen;
            FormBorderStyle = FormBorderStyle.FixedSingle;
            MaximizeBox = false;
            ClientSize = new Size(900, 884);
            Font = new Font("Segoe UI", 9F);
            BackColor = Color.FromArgb(242, 246, 250);
            AllowDrop = true;

            Panel titlePanel = new Panel();
            titlePanel.SetBounds(0, 0, 900, 78);
            titlePanel.BackColor = Color.FromArgb(86, 30, 30);
            Controls.Add(titlePanel);

            Label title = new Label();
            title.Text = GameTitle + " Steam판 한국어 패처";
            title.ForeColor = Color.White;
            title.Font = new Font("Segoe UI", 18F, FontStyle.Bold);
            title.AutoSize = true;
            title.Location = new Point(24, 13);
            titlePanel.Controls.Add(title);

            Label subtitle = new Label();
            subtitle.Text = "WARRIORS OROCHI 3 Ultimate Definitive Edition (Steam " + AppId + ") 설치 폴더를 검증한 뒤 중국어 간체 슬롯을 한국어로 교체합니다.  " + versionText;
            subtitle.ForeColor = Color.FromArgb(242, 215, 205);
            subtitle.AutoSize = true;
            subtitle.Location = new Point(27, 51);
            titlePanel.Controls.Add(subtitle);

            int y = 92;
            AddSectionLabel("A. Steam 게임 설치 폴더 (" + GameFolderName + ")", y);
            folderPathBox = AddPathBox(y + 22, initialFolderPath, 646);
            detectButton = new Button();
            detectButton.Text = "자동 찾기";
            detectButton.SetBounds(678, y + 20, 96, 30);
            detectButton.Click += delegate { DetectFolder(true); };
            Controls.Add(detectButton);
            folderBrowseButton = AddBrowseButton(y + 20, delegate { BrowseFolder(); });
            AddSmallLabel("Steam 라이브러리 → 게임 우클릭 → 관리 → 로컬 파일 보기 에서 열리는 폴더입니다. 비워 두면 자동으로 찾습니다.", y + 54);

            y = 172;
            AddSectionLabel("B. 복구 백업 파일 (기존 백업이 있으면 그 파일을 선택)", y);
            backupBox = AddPathBox(y + 22, initialBackupPath ?? String.Empty, 750);
            backupBrowseButton = AddBrowseButton(y + 20, delegate { BrowseBackup(); });
            backupBox.TextChanged += delegate { if (backupBox.Focused) backupCustomized = true; };
            folderPathBox.TextChanged += delegate { UpdateDefaultBackup(); };
            if (!String.IsNullOrWhiteSpace(initialBackupPath))
                backupCustomized = true;

            GroupBox warningGroup = new GroupBox();
            warningGroup.Text = "반드시 확인할 주의사항";
            warningGroup.Font = new Font("Segoe UI", 10F, FontStyle.Bold);
            warningGroup.ForeColor = Color.FromArgb(123, 72, 0);
            warningGroup.BackColor = Color.FromArgb(255, 248, 220);
            warningGroup.SetBounds(22, 240, 856, 192);
            Controls.Add(warningGroup);

            Label warnings = new Label();
            warnings.Font = new Font("Segoe UI", 9.5F, FontStyle.Regular);
            warnings.ForeColor = Color.FromArgb(70, 48, 10);
            warnings.AutoSize = false;
            warnings.SetBounds(18, 28, 820, 124);
            warnings.Text =
                "1. Steam판 WARRIORS OROCHI 3 Ultimate Definitive Edition 전용입니다. 게임 언어를 중국어 간체(简体中文)로 설정해야 한국어가 나옵니다.\r\n" +
                "2. LINKIDX·LINKFILE_CHS.BIN 교체, dinput8.dll(실행 파일 속 문장 한국어화) 추가. WO3U.exe·세이브는 그대로입니다.\r\n" +
                "3. 작업 중 게임(" + GameExe + ")을 완전히 종료하세요. 실행 중이면 패처가 중단합니다.\r\n" +
                "4. 쓰기 전 원본에서 교체되는 부분을 백업 파일(" + BackupExtension + ")에 저장합니다. 이 파일로 복구·다음 버전 갱신을 합니다.\r\n" +
                "5. 작업 중 여유 공간이 약 1.1GB 필요합니다. Program Files 아래 설치라면 관리자 권한을 요청합니다.\r\n" +
                "6. Steam '게임 파일 무결성 검사'나 게임 업데이트는 데이터 파일을 원본으로 되돌립니다. 그 뒤에는 패처를 다시 실행하세요.";
            warningGroup.Controls.Add(warnings);

            warningCheck = new CheckBox();
            warningCheck.Text = "위 주의사항을 확인했으며, 선택한 설치 폴더의 게임 파일이 직접 교체되는 것에 동의합니다.";
            warningCheck.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
            warningCheck.AutoSize = true;
            warningCheck.Location = new Point(20, 160);
            warningGroup.Controls.Add(warningCheck);

            soldierCheck = new CheckBox();
            soldierCheck.Text = "선택: 병사 공격성 강화 — 일반 병사가 무장처럼 적극적으로 공격합니다 (난이도 상승, 게임 언어와 무관, 해제 후 적용하면 원래대로)";
            soldierCheck.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
            soldierCheck.ForeColor = Color.FromArgb(120, 30, 30);
            soldierCheck.AutoSize = true;
            soldierCheck.Location = new Point(24, 442);
            Controls.Add(soldierCheck);

            Label logLabel = new Label();
            logLabel.Text = "진행 로그";
            logLabel.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
            logLabel.AutoSize = true;
            logLabel.Location = new Point(22, 479);
            Controls.Add(logLabel);

            logBox = new RichTextBox();
            logBox.SetBounds(22, 501, 856, 280);
            logBox.ReadOnly = true;
            logBox.BackColor = Color.FromArgb(22, 28, 34);
            logBox.ForeColor = Color.FromArgb(225, 235, 240);
            logBox.Font = new Font("Consolas", 9F);
            logBox.WordWrap = false;
            Controls.Add(logBox);

            verifyButton = AddButton("상태 검사", 22, 797, 140, false, Color.Empty,
                delegate { StartOperation(UiOperation.Verify); });
            patchButton = AddButton("한국어 패치 적용", 172, 797, 230, true, Color.FromArgb(34, 112, 166),
                delegate { StartOperation(UiOperation.Patch); });
            restoreButton = AddButton("원본 복구", 412, 797, 140, false, Color.Empty,
                delegate { StartOperation(UiOperation.Restore); });
            closeButton = AddButton("닫기", 758, 797, 120, false, Color.Empty, delegate { Close(); });

            progressBar = new ProgressBar();
            progressBar.SetBounds(22, 851, 650, 16);
            progressBar.Minimum = 0;
            progressBar.Maximum = 1000;
            Controls.Add(progressBar);

            statusLabel = new Label();
            statusLabel.Text = "대기 중";
            statusLabel.TextAlign = ContentAlignment.MiddleRight;
            statusLabel.SetBounds(685, 846, 193, 25);
            Controls.Add(statusLabel);

            worker = new BackgroundWorker();
            worker.WorkerReportsProgress = true;
            worker.DoWork += WorkerDoWork;
            worker.ProgressChanged += delegate(object s, ProgressChangedEventArgs e) { progressBar.Value = Math.Max(0, Math.Min(1000, e.ProgressPercentage)); };
            worker.RunWorkerCompleted += WorkerCompleted;

            DragEnter += FormDragEnter;
            DragDrop += FormDragDrop;
            FormClosing += MainFormClosing;
            Shown += delegate
            {
                if (String.IsNullOrWhiteSpace(folderPathBox.Text))
                    DetectFolder(false);
                else
                    UpdateDefaultBackup();
            };
        }

        private void AddSectionLabel(string text, int y)
        {
            Label label = new Label();
            label.Text = text;
            label.Font = new Font("Segoe UI", 9.5F, FontStyle.Bold);
            label.AutoSize = true;
            label.Location = new Point(22, y);
            Controls.Add(label);
        }

        private void AddSmallLabel(string text, int y)
        {
            Label label = new Label();
            label.Text = text;
            label.AutoSize = true;
            label.ForeColor = Color.FromArgb(70, 80, 90);
            label.Location = new Point(22, y);
            Controls.Add(label);
        }

        private TextBox AddPathBox(int y, string text, int width)
        {
            TextBox box = new TextBox();
            box.SetBounds(22, y, width, 27);
            box.Text = text ?? String.Empty;
            Controls.Add(box);
            return box;
        }

        private Button AddBrowseButton(int y, EventHandler handler)
        {
            Button button = new Button();
            button.Text = "찾아보기...";
            button.SetBounds(782, y, 96, 30);
            button.Click += handler;
            Controls.Add(button);
            return button;
        }

        private Button AddButton(string text, int x, int y, int width, bool primary, Color color, EventHandler handler)
        {
            Button button = new Button();
            button.Text = text;
            button.SetBounds(x, y, width, 38);
            if (primary)
            {
                button.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
                button.BackColor = color;
                button.ForeColor = Color.White;
                button.FlatStyle = FlatStyle.Flat;
            }
            button.Click += handler;
            Controls.Add(button);
            return button;
        }

        private void DetectFolder(bool report)
        {
            string found = FindSteamInstall();
            if (found != null)
            {
                folderPathBox.Text = found;
                UpdateDefaultBackup();
                if (report)
                    AppendLog("[OK] Steam 설치 폴더를 찾았습니다: " + found + Environment.NewLine);
            }
            else if (report)
                MessageBox.Show(this, "Steam 라이브러리에서 " + GameFolderName + " 설치 폴더를 찾지 못했습니다.\r\n찾아보기로 직접 선택하세요.",
                    "자동 찾기", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }

        private void BrowseFolder()
        {
            using (FolderBrowserDialog dialog = new FolderBrowserDialog())
            {
                dialog.Description = "Steam 의 " + GameFolderName + " 설치 폴더(" + GameExe + " 가 있는 폴더)를 선택하세요.";
                dialog.ShowNewFolderButton = false;
                string current = folderPathBox.Text.Trim().Trim('"');
                if (!String.IsNullOrWhiteSpace(current) && Directory.Exists(current))
                    dialog.SelectedPath = current;
                if (dialog.ShowDialog(this) == DialogResult.OK)
                    folderPathBox.Text = dialog.SelectedPath;
            }
        }

        private void BrowseBackup()
        {
            using (SaveFileDialog dialog = new SaveFileDialog())
            {
                dialog.Title = "복구 백업 파일 선택";
                dialog.Filter = "WO3U 복구 백업 (*" + BackupExtension + ")|*" + BackupExtension + "|모든 파일 (*.*)|*.*";
                dialog.AddExtension = false;
                dialog.OverwritePrompt = false;
                string current = backupBox.Text.Trim().Trim('"');
                dialog.FileName = Path.GetFileName(current);
                string directory = String.IsNullOrWhiteSpace(current) ? null : Path.GetDirectoryName(current);
                if (!String.IsNullOrWhiteSpace(directory) && Directory.Exists(directory))
                    dialog.InitialDirectory = directory;
                if (dialog.ShowDialog(this) == DialogResult.OK)
                {
                    backupCustomized = true;
                    backupBox.Text = dialog.FileName;
                }
            }
        }

        private void UpdateDefaultBackup()
        {
            RefreshSoldierCheck();
            if (backupCustomized)
                return;
            string folder = folderPathBox.Text.Trim().Trim('"');
            try
            {
                backupBox.Text = String.IsNullOrWhiteSpace(folder) ? String.Empty : DefaultBackupPath(ResolveGameDir(folder));
            }
            catch
            {
                backupBox.Text = String.Empty;
            }
        }

        private void RefreshSoldierCheck()
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

        private void FormDragEnter(object sender, DragEventArgs e)
        {
            if (e.Data.GetDataPresent(DataFormats.FileDrop))
                e.Effect = DragDropEffects.Copy;
        }

        private void FormDragDrop(object sender, DragEventArgs e)
        {
            string[] files = e.Data.GetData(DataFormats.FileDrop) as string[];
            if (files == null || files.Length != 1)
                return;
            if (Directory.Exists(files[0]))
                folderPathBox.Text = files[0];
            else if (files[0].EndsWith(BackupExtension, StringComparison.OrdinalIgnoreCase))
            {
                backupCustomized = true;
                backupBox.Text = files[0];
            }
            else if (File.Exists(files[0]))
                folderPathBox.Text = Path.GetDirectoryName(files[0]);
        }

        private void StartOperation(UiOperation operation)
        {
            string targetPath;
            try
            {
                string typed = folderPathBox.Text.Trim().Trim('"');
                if (String.IsNullOrWhiteSpace(typed))
                {
                    DetectFolder(false);
                    typed = folderPathBox.Text.Trim().Trim('"');
                }
                targetPath = ResolveGameDir(typed);
            }
            catch (Exception ex)
            {
                MessageBox.Show(this, ex.Message, "설치 폴더 확인", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }
            string backupPath = backupBox.Text.Trim().Trim('"');
            if (String.IsNullOrWhiteSpace(backupPath))
            {
                MessageBox.Show(this, "복구 백업 파일의 저장 위치를 지정하세요.", "백업 경로 필요",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }
            backupPath = Path.GetFullPath(backupPath);
            if (operation != UiOperation.Verify)
            {
                string backupDirectory = Path.GetDirectoryName(backupPath);
                if (String.IsNullOrWhiteSpace(backupDirectory) || !Directory.Exists(backupDirectory))
                {
                    MessageBox.Show(this, "백업 파일을 저장할 폴더가 존재하지 않습니다.", "백업 경로 오류",
                        MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    return;
                }
                if (operation == UiOperation.Restore && !File.Exists(backupPath))
                {
                    MessageBox.Show(this, "선택한 복구 백업 파일이 없습니다.\r\n백업이 없다면 Steam '게임 파일 무결성 검사'로도 원본을 받을 수 있습니다.",
                        "백업 파일 확인", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    return;
                }
                if (!warningCheck.Checked)
                {
                    MessageBox.Show(this, "패치 또는 복구 전에 주의사항 확인란을 체크하세요.", "주의사항 확인 필요",
                        MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    return;
                }
                if (!CanWrite(targetPath) || !CanWrite(Path.GetDirectoryName(backupPath)))
                {
                    DialogResult elevate = MessageBox.Show(this,
                        "선택한 폴더에 쓸 권한이 없습니다 (Program Files 아래 설치 등).\r\n관리자 권한으로 패처를 다시 실행하시겠습니까?",
                        "관리자 권한 필요", MessageBoxButtons.YesNo, MessageBoxIcon.Question);
                    if (elevate == DialogResult.Yes && RelaunchElevated(targetPath, backupPath))
                        Close();
                    return;
                }
            }

            ForeignDll foreign = ForeignDll.Chain;
            if (operation == UiOperation.Patch)
            {
                DialogResult answer = MessageBox.Show(this,
                    "다음 설치 폴더의 LINKIDX_CHS.BIN / LINKFILE_CHS.BIN 을 한국어 버전으로 교체합니다.\r\n\r\n" + targetPath +
                    "\r\n\r\n복구 백업: " + backupPath +
                    (soldierCheck.Checked ? "\r\n\r\n선택 기능 '병사 공격성 강화'도 적용합니다 (LINKFILE_000.BIN 의 유닛 데이터 일부 수정)." :
                        "\r\n\r\n'병사 공격성 강화'는 적용하지 않습니다 (적용되어 있었다면 원래대로 되돌립니다).") +
                    "\r\n\r\n게임이 완전히 종료되었습니까?",
                    "패치 확인", MessageBoxButtons.YesNo, MessageBoxIcon.Warning, MessageBoxDefaultButton.Button2);
                if (answer != DialogResult.Yes)
                    return;
                if (IsForeignDll(targetPath))
                {
                    using (ForeignDllForm form = new ForeignDllForm(targetPath))
                    {
                        if (form.ShowDialog(this) != DialogResult.OK)
                            return;
                        foreign = form.Choice;
                    }
                }
            }
            else if (operation == UiOperation.Restore)
            {
                DialogResult answer = MessageBox.Show(this,
                    "지정한 백업 파일로 패치 전 원본 상태로 복구합니다. 계속하시겠습니까?\r\n\r\n" + backupPath,
                    "원본 복구 확인", MessageBoxButtons.YesNo, MessageBoxIcon.Question, MessageBoxDefaultButton.Button2);
                if (answer != DialogResult.Yes)
                    return;
            }

            logBox.Clear();
            SetBusy(true, operation == UiOperation.Verify ? "상태 검사 중..." :
                (operation == UiOperation.Patch ? "패치 적용 중..." : "원본 복구 중..."));
            worker.RunWorkerAsync(new UiWorkItem { Operation = operation, TargetPath = targetPath, BackupPath = backupPath, Foreign = foreign, Soldier = soldierCheck.Checked });
        }

        private void WorkerDoWork(object sender, DoWorkEventArgs e)
        {
            UiWorkItem work = (UiWorkItem)e.Argument;
            UiResult result = new UiResult();
            result.Operation = work.Operation;
            result.TargetPath = work.TargetPath;

            TextWriter originalOutput = Console.Out;
            try
            {
                Console.SetOut(new UiTextWriter(AppendLog));
                progress = delegate(double f) { worker.ReportProgress((int)(f * 1000)); };
                Options options = new Options();
                options.FolderPath = work.TargetPath;
                options.BackupPath = work.BackupPath;
                options.Yes = true;
                options.VerifyOnly = work.Operation == UiOperation.Verify;
                options.Restore = work.Operation == UiOperation.Restore;
                options.Pause = false;
                options.Foreign = work.Foreign;
                options.Soldier = work.Operation == UiOperation.Patch ? (bool?)work.Soldier : null;
                result.ExitCode = Run(options);
            }
            catch (Exception ex)
            {
                result.ExitCode = 1;
                result.Error = ex;
                AppendLog(Environment.NewLine + "[실패] " + ex.Message + Environment.NewLine);
            }
            finally
            {
                progress = null;
                Console.SetOut(originalOutput);
            }
            e.Result = result;
        }

        private void WorkerCompleted(object sender, RunWorkerCompletedEventArgs e)
        {
            if (IsDisposed || Disposing)
                return;
            SetBusy(false, "대기 중");
            RefreshSoldierCheck();
            UiResult result = e.Result as UiResult;
            if (result == null || result.Error != null || result.ExitCode != 0)
            {
                string message = result != null && result.Error != null ? result.Error.Message :
                    "검사 또는 작업이 성공적으로 끝나지 않았습니다. 진행 로그를 확인하세요.";
                MessageBox.Show(this, message, "작업 실패", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }
            progressBar.Value = 1000;
            if (result.Operation == UiOperation.Verify)
                MessageBox.Show(this, "상태 검사가 완료되었습니다.\r\n자세한 상태는 진행 로그를 확인하세요.",
                    "검사 완료", MessageBoxButtons.OK, MessageBoxIcon.Information);
            else if (result.Operation == UiOperation.Patch)
                MessageBox.Show(this, "한국어 패치 적용과 최종 해시 검증이 완료되었습니다.\r\n\r\n" + result.TargetPath +
                    "\r\n\r\nSteam 게임 속성의 언어가 중국어 간체(简体中文)인지 확인한 뒤 게임을 실행하세요.",
                    "패치 완료", MessageBoxButtons.OK, MessageBoxIcon.Information);
            else
                MessageBox.Show(this, "원본 복구와 해시 검증이 완료되었습니다.",
                    "복구 완료", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }

        private void AppendLog(string text)
        {
            if (IsDisposed)
                return;
            if (InvokeRequired)
            {
                try { BeginInvoke(new Action<string>(AppendLog), text); } catch { }
                return;
            }
            logBox.AppendText(text);
            logBox.SelectionStart = logBox.TextLength;
            logBox.ScrollToCaret();
        }

        private void MainFormClosing(object sender, FormClosingEventArgs e)
        {
            if (!busyState)
                return;
            e.Cancel = true;
            MessageBox.Show(this, "작업 중에는 창을 닫을 수 없습니다. 완료될 때까지 기다리세요.",
                "작업 진행 중", MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }

        private void SetBusy(bool busy, string status)
        {
            busyState = busy;
            Control[] controls =
            {
                folderPathBox, folderBrowseButton, detectButton, backupBox, backupBrowseButton,
                warningCheck, soldierCheck, verifyButton, patchButton, restoreButton, closeButton
            };
            foreach (Control control in controls)
                control.Enabled = !busy;
            if (busy)
                progressBar.Value = 0;
            statusLabel.Text = status;
        }
    }

    private static Action<double> progress;

    private static void Report(double fraction)
    {
        Action<double> p = progress;
        if (p != null)
            p(fraction);
    }

    // ------------------------------------------------------------------ 진입점

    [STAThread]
    private static int Main(string[] args)
    {
        try
        {
            versionText = ReadPackVersion(DefaultPackPath());
        }
        catch (Exception ex)
        {
            versionText = "(팩 오류: " + ex.Message + ")";
        }

        bool commandLineMode = args.Any(delegate(string arg) { return arg.StartsWith("--", StringComparison.Ordinal) && !arg.Equals("--gui", StringComparison.OrdinalIgnoreCase); });
        if (!commandLineMode)
        {
            string initialFolder = null;
            string initialBackup = null;
            for (int i = 0; i < args.Length; i++)
            {
                if (args[i].Equals("--gui", StringComparison.OrdinalIgnoreCase))
                    continue;
                if (args[i].EndsWith(BackupExtension, StringComparison.OrdinalIgnoreCase))
                    initialBackup = args[i];
                else if (initialFolder == null)
                    initialFolder = args[i];
            }
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new MainForm(initialFolder, initialBackup));
            return 0;
        }

        InitializeConsoleForCli();
        bool pauseRequested = !args.Any(delegate(string arg)
        {
            return arg.Equals("--no-pause", StringComparison.OrdinalIgnoreCase) || arg.Equals("--headless", StringComparison.OrdinalIgnoreCase);
        });
        Options options = null;
        int result = 1;
        try
        {
            Console.OutputEncoding = new UTF8Encoding(false);
            Console.Title = GameTitle + " Steam판 한국어 패처 " + versionText;
            options = ParseOptions(args);
            result = Run(options);
        }
        catch (Exception ex)
        {
            SetConsoleColor(ConsoleColor.Red);
            Console.WriteLine();
            Console.WriteLine("[실패] " + ex.Message);
            ResetConsoleColor();
            result = 1;
        }
        finally
        {
            if ((options == null && pauseRequested) || (options != null && options.Pause))
            {
                Console.WriteLine();
                Console.Write("Enter 키를 누르면 종료합니다...");
                try { Console.ReadLine(); } catch { }
            }
        }
        return result;
    }

    private static void InitializeConsoleForCli()
    {
        try
        {
            AttachConsole(AttachParentProcess);
            Stream output = Console.OpenStandardOutput();
            if (output != null && output.CanWrite)
            {
                StreamWriter writer = new StreamWriter(output, new UTF8Encoding(false));
                writer.AutoFlush = true;
                Console.SetOut(writer);
            }
            Stream error = Console.OpenStandardError();
            if (error != null && error.CanWrite)
            {
                StreamWriter writer = new StreamWriter(error, new UTF8Encoding(false));
                writer.AutoFlush = true;
                Console.SetError(writer);
            }
        }
        catch
        {
        }
    }

    private static Options ParseOptions(string[] args)
    {
        Options options = new Options();
        options.Pause = true;
        for (int index = 0; index < args.Length; index++)
        {
            string arg = args[index].Trim();
            if (arg.Equals("--yes", StringComparison.OrdinalIgnoreCase))
                options.Yes = true;
            else if (arg.Equals("--verify-only", StringComparison.OrdinalIgnoreCase))
                options.VerifyOnly = true;
            else if (arg.Equals("--restore", StringComparison.OrdinalIgnoreCase))
                options.Restore = true;
            else if (arg.Equals("--chain-dll", StringComparison.OrdinalIgnoreCase))
                options.Foreign = ForeignDll.Chain;
            else if (arg.Equals("--overwrite-dll", StringComparison.OrdinalIgnoreCase))
                options.Foreign = ForeignDll.Overwrite;
            else if (arg.Equals("--skip-dll", StringComparison.OrdinalIgnoreCase))
                options.Foreign = ForeignDll.Skip;
            else if (arg.Equals("--soldier-ai", StringComparison.OrdinalIgnoreCase))
                options.Soldier = true;
            else if (arg.Equals("--no-soldier-ai", StringComparison.OrdinalIgnoreCase))
                options.Soldier = false;
            else if (arg.Equals("--no-pause", StringComparison.OrdinalIgnoreCase) || arg.Equals("--headless", StringComparison.OrdinalIgnoreCase))
                options.Pause = false;
            else if (arg.Equals("--backup", StringComparison.OrdinalIgnoreCase))
            {
                if (index + 1 >= args.Length)
                    throw new ArgumentException("--backup 다음에 백업 파일 경로를 지정하세요.");
                options.BackupPath = args[++index].Trim().Trim('"');
            }
            else if (arg.Equals("--folder", StringComparison.OrdinalIgnoreCase))
            {
                if (index + 1 >= args.Length)
                    throw new ArgumentException("--folder 다음에 게임 설치 폴더 경로를 지정하세요.");
                options.FolderPath = args[++index].Trim().Trim('"');
            }
            else if (arg.StartsWith("--", StringComparison.Ordinal))
                throw new ArgumentException("알 수 없는 옵션입니다: " + arg);
            else if (options.FolderPath == null)
                options.FolderPath = arg;
            else
                throw new ArgumentException("대상 경로는 하나만 지정할 수 있습니다.");
        }
        if (String.IsNullOrWhiteSpace(options.FolderPath))
        {
            options.FolderPath = FindSteamInstall();
            if (options.FolderPath == null)
                throw new ArgumentException(
                    "사용법: WO3U_Steam_KR_Patch.exe [--folder <설치 폴더>] [--backup <백업 파일>] [--verify-only | --restore] [--yes] [--chain-dll | --overwrite-dll | --skip-dll] [--soldier-ai | --no-soldier-ai] [--no-pause]\r\n" +
                    "설치 폴더를 자동으로 찾지 못했습니다. --folder 로 지정하세요.");
        }
        options.FolderPath = ResolveGameDir(options.FolderPath);
        if (!String.IsNullOrWhiteSpace(options.BackupPath))
            options.BackupPath = Path.GetFullPath(options.BackupPath);
        return options;
    }

    // ------------------------------------------------------------------ 경로

    private static string DefaultPackPath()
    {
        return Path.Combine(AppDomain.CurrentDomain.BaseDirectory, PackFileName);
    }

    private static string ResolveGameDir(string selectedPath)
    {
        if (String.IsNullOrWhiteSpace(selectedPath) || !Directory.Exists(selectedPath))
            throw new DirectoryNotFoundException("Steam 의 " + GameFolderName + " 설치 폴더를 선택하세요.");
        string full = Path.GetFullPath(selectedPath).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        string[] candidates =
        {
            full,
            Path.Combine(full, GameFolderName),
            Path.Combine(full, "common", GameFolderName),
            Path.Combine(full, "steamapps", "common", GameFolderName)
        };
        foreach (string candidate in candidates.Distinct(StringComparer.OrdinalIgnoreCase))
        {
            if (Directory.Exists(candidate) && File.Exists(Path.Combine(candidate, GameExe)) &&
                TargetNames.All(delegate(string name) { return File.Exists(Path.Combine(candidate, name)); }))
                return Path.GetFullPath(candidate);
        }
        throw new DirectoryNotFoundException(
            "선택한 경로에서 " + GameExe + " / LINKIDX_CHS.BIN / LINKFILE_CHS.BIN 을 찾지 못했습니다.\r\n\r\n" +
            "지원 예시:\r\n" +
            "  ...\\steamapps\\common\\" + GameFolderName + "\r\n" +
            "  Steam 라이브러리 폴더 (steamapps\\common 자동 탐색)\r\n\r\n" +
            "중국어 간체 파일이 없다면 Steam 게임 속성 → 언어에서 简体中文 을 선택해 받은 뒤 다시 시도하세요.");
    }

    private static string DefaultBackupPath(string gameDir)
    {
        // ...\steamapps\common\WARRIORS OROCHI 3 Ultimate → 같은 폴더 안 (Steam 무결성 검사가 지우지 않는 이름)
        return Path.Combine(gameDir, "WO3U_KR" + BackupExtension);
    }

    private static string FindSteamInstall()
    {
        List<string> roots = new List<string>();
        foreach (string key in new[] { @"HKEY_CURRENT_USER\Software\Valve\Steam", @"HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Valve\Steam", @"HKEY_LOCAL_MACHINE\SOFTWARE\Valve\Steam" })
        {
            foreach (string name in new[] { "SteamPath", "InstallPath" })
            {
                try
                {
                    object value = Registry.GetValue(key, name, null);
                    if (value != null)
                        roots.Add(value.ToString().Replace('/', '\\'));
                }
                catch { }
            }
        }
        roots.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), "Steam"));
        List<string> libraries = new List<string>();
        foreach (string root in roots.Distinct(StringComparer.OrdinalIgnoreCase))
        {
            libraries.Add(root);
            string vdf = Path.Combine(root, "steamapps", "libraryfolders.vdf");
            try
            {
                if (File.Exists(vdf))
                    foreach (Match m in Regex.Matches(File.ReadAllText(vdf), "\"path\"\\s+\"([^\"]+)\""))
                        libraries.Add(m.Groups[1].Value.Replace(@"\\", @"\"));
            }
            catch { }
        }
        foreach (string lib in libraries.Distinct(StringComparer.OrdinalIgnoreCase))
        {
            string dir = Path.Combine(lib, "steamapps", "common", GameFolderName);
            try
            {
                string manifest = Path.Combine(lib, "steamapps", "appmanifest_" + AppId + ".acf");
                if (File.Exists(manifest))
                {
                    Match m = Regex.Match(File.ReadAllText(manifest), "\"installdir\"\\s+\"([^\"]+)\"");
                    if (m.Success)
                        dir = Path.Combine(lib, "steamapps", "common", m.Groups[1].Value);
                }
                if (File.Exists(Path.Combine(dir, GameExe)))
                    return dir;
            }
            catch { }
        }
        return null;
    }

    private static bool CanWrite(string directory)
    {
        try
        {
            string probe = Path.Combine(directory, ".wo3u-write-test-" + Guid.NewGuid().ToString("N"));
            File.WriteAllBytes(probe, new byte[] { 0 });
            File.Delete(probe);
            return true;
        }
        catch
        {
            return false;
        }
    }

    private static bool RelaunchElevated(string folder, string backup)
    {
        try
        {
            ProcessStartInfo info = new ProcessStartInfo(Application.ExecutablePath);
            info.Arguments = "--gui \"" + folder + "\" \"" + backup + "\"";
            info.Verb = "runas";
            info.UseShellExecute = true;
            Process.Start(info);
            return true;
        }
        catch
        {
            return false;
        }
    }

    // ------------------------------------------------------------------ 실행 본체

    private static int Run(Options options)
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
        WriteHeader();
        if (Process.GetProcessesByName(Path.GetFileNameWithoutExtension(GameExe)).Length != 0)
            throw new InvalidOperationException("게임(" + GameExe + ")이 실행 중입니다. 완전히 종료한 뒤 다시 실행하세요.");

        Pack pack = LoadPack(DefaultPackPath());
        string dir = options.FolderPath;
        string backupPath = Path.GetFullPath(String.IsNullOrWhiteSpace(options.BackupPath) ? DefaultBackupPath(dir) : options.BackupPath);
        Console.WriteLine("대상 폴더: " + dir);
        Console.WriteLine("방식: LINKIDX_CHS.BIN / LINKFILE_CHS.BIN 을 원본 + 한국어 팩으로 재구성해 교체 (다른 파일 불변)");
        Console.WriteLine("백업: " + backupPath);
        Console.WriteLine();

        FileState state = DetectState(dir, pack.Files);
        Backup backup = File.Exists(backupPath) ? LoadBackup(backupPath) : null;
        if (backup != null)
            Console.WriteLine("[*] 복구 백업 확인: 패치 " + backup.PackVersion + " 적용 시 생성");

        if (options.VerifyOnly)
        {
            PrintState(state, pack, backup, dir);
            return state == FileState.Unknown && (backup == null || DetectState(dir, backup.Files) != FileState.Target) ? 2 : 0;
        }

        if (options.Restore)
            return RestoreMode(dir, pack, backup, backupPath, options.Yes);

        ForeignDll foreignMode = ForeignDll.Skip;
        if (pack.Dll != null && DllState(dir, pack) == 3)
            foreignMode = DecideForeignDll(dir, options);

        if (state == FileState.Target && pack.Dll != null && DllState(dir, pack) != 1)
        {
            if (InstallDll(dir, pack, foreignMode))
                WriteOk("한국어 데이터는 이미 적용되어 있어 " + ProxyDllName + " 만 설치했습니다.");
            else
                WriteOk("한국어 데이터는 이미 적용되어 있습니다. " + ProxyDllName + " 은 건너뛰었습니다.");
            return 0;
        }

        if (state == FileState.Target)
        {
            WriteOk("이미 이 버전(" + pack.Version + ")의 한국어 패치가 적용된 상태입니다.");
            if (backup != null && !options.Yes && AskYes("한국어 패치를 제거하고 원본으로 복구하시겠습니까? [Y/N]: "))
                return RestoreMode(dir, pack, backup, backupPath, true);
            return 0;
        }

        if (state == FileState.Unknown)
        {
            if (backup == null || DetectState(dir, backup.Files) != FileState.Target)
                throw new InvalidDataException(
                    "설치 폴더의 중국어 간체 파일이 이 패처가 아는 원본도 완성본도 아닙니다.\r\n" +
                    "이전 버전 패치를 썼다면 당시 만든 백업 파일(" + BackupExtension + ")을 선택하세요.\r\n" +
                    "백업이 없거나 게임이 업데이트되었다면 Steam '게임 파일 무결성 검사'로 원본을 받은 뒤 다시 실행하세요.");
            SetConsoleColor(ConsoleColor.Yellow);
            Console.WriteLine("[!] 이전 패치 버전(" + backup.PackVersion + ")을 감지했습니다.");
            Console.WriteLine("    백업으로 원본을 재구성한 뒤 현재 버전을 적용합니다.");
            ResetConsoleColor();
            Confirm(options.Yes, "복구 후 패치를 다시 적용하시겠습니까? [Y/N]: ");
            RestoreFromBackup(dir, backup);
            if (DetectState(dir, pack.Files) != FileState.Source)
                throw new InvalidDataException("백업 복구 후에도 원본 해시가 일치하지 않습니다. 설치 폴더를 확인하세요.");
            WriteOk("이전 버전 복구 완료");
        }

        SetConsoleColor(ConsoleColor.Yellow);
        Console.WriteLine("주의: 이 작업은 설치 폴더의 LINKIDX_CHS.BIN / LINKFILE_CHS.BIN 을 교체합니다.");
        Console.WriteLine("원상복구 및 다음 버전 갱신용 백업은 지정한 경로에 보존됩니다.");
        ResetConsoleColor();
        Confirm(options.Yes, "계속하시겠습니까? [Y/N]: ");
        CheckFreeSpace(dir, pack.Files[1].TargetSize + pack.BlobLengths.Values.Sum() + (64L << 20));

        bool refreshing = File.Exists(backupPath);
        CreateBackup(dir, pack, backupPath);
        WriteOk((refreshing ? "기존 복구 백업 갱신 완료: " : "원상복구 백업 생성 완료: ") + backupPath);

        bool dllInstalled = false;
        try
        {
            ApplyPack(dir, pack);
            if (DetectState(dir, pack.Files) != FileState.Target)
                throw new InvalidDataException("패치 후 최종 해시가 일치하지 않습니다.");
            dllInstalled = InstallDll(dir, pack, foreignMode);
        }
        catch
        {
            SetConsoleColor(ConsoleColor.Yellow);
            Console.WriteLine("[!] 적용 실패. 원본 상태를 확인합니다.");
            ResetConsoleColor();
            CleanupTemp(dir);
            RemoveDll(dir, pack);
            FileState now = DetectState(dir, pack.Files);
            if (now == FileState.Target)
            {
                Backup made = LoadBackup(backupPath);
                RestoreFromBackup(dir, made);
                now = DetectState(dir, pack.Files);
            }
            if (now != FileState.Source)
                throw new InvalidDataException("자동 복구 검증에 실패했습니다. 백업 파일을 지우지 말고 원본 복구를 다시 실행하거나 Steam 무결성 검사를 하세요.");
            WriteOk("원본 상태 유지 확인");
            throw;
        }

        Console.WriteLine();
        WriteOk("한국어 패치 적용 및 최종 해시 검증 완료 (" + pack.Version + ", 데이터 2/2" +
            (pack.Dll == null ? "" : dllInstalled ? " + " + ProxyDllName : ", " + ProxyDllName + " 건너뜀") + ")");
        Console.WriteLine("게임 언어를 중국어 간체(简体中文)로 설정하면 한국어로 표시됩니다.");
        Console.WriteLine("복구하려면: WO3U_Steam_KR_Patch.exe --restore --backup \"" + backupPath + "\" --folder \"" + dir + "\"");
        Console.WriteLine("복구 백업은 삭제하지 않는 것을 권장합니다: " + backupPath);
        return 0;
    }

    private static int RestoreMode(string dir, Pack pack, Backup backup, string backupPath, bool automaticYes)
    {
        if (DetectState(dir, pack.Files) == FileState.Source)
        {
            if (RemoveDll(dir, pack))
                WriteOk(ProxyDllName + " 제거 완료");
            WriteOk("이미 원본 상태입니다.");
            return 0;
        }
        if (backup == null)
            throw new FileNotFoundException("복구 백업이 없습니다. Steam '게임 파일 무결성 검사'로 원본을 받을 수 있습니다.", backupPath);
        if (DetectState(dir, backup.Files) != FileState.Target)
            throw new InvalidDataException("현재 파일이 이 백업을 만든 패치 상태(" + backup.PackVersion + ")와 다릅니다. Steam '게임 파일 무결성 검사'로 원본을 받으세요.");
        Confirm(automaticYes, "한국어 패치를 제거하고 원본으로 복구하시겠습니까? [Y/N]: ");
        CheckFreeSpace(dir, backup.Files[1].SourceSize + (64L << 20));
        RestoreFromBackup(dir, backup);
        if (DetectState(dir, backup.Files) != FileState.Source)
            throw new InvalidDataException("복구 후 원본 해시 검증에 실패했습니다. 백업을 삭제하지 마세요.");
        if (RemoveDll(dir, pack))
            WriteOk(ProxyDllName + " 제거 완료");
        WriteOk("원본 복구 및 해시 검증 2/2 완료");
        Console.WriteLine("백업은 재적용에 대비해 그대로 보존했습니다: " + backupPath);
        return 0;
    }

    private static void PrintState(FileState state, Pack pack, Backup backup, string dir)
    {
        Console.WriteLine();
        if (File.Exists(Path.Combine(dir, ChainDllName)))
            Console.WriteLine("[*] 다른 프로그램의 " + ProxyDllName + " 을 이어서 쓰는 중입니다: " + ChainDllName + " (원본 복구 때 되돌립니다)");
        if (File.Exists(Path.Combine(dir, ProxyDllName + ForeignDllSuffix)))
            Console.WriteLine("[*] 다른 프로그램의 " + ProxyDllName + " 을 보관 중입니다: " + ProxyDllName + ForeignDllSuffix + " (원본 복구 때 되돌립니다)");
        if (state != FileState.Target && pack.Dll != null && DllState(dir, pack) == 3)
            Console.WriteLine("[*] 설치 폴더에 다른 프로그램의 " + ProxyDllName + " 이 있습니다. 패치 적용 때 처리 방법을 묻습니다.");
        if (state == FileState.Source)
            WriteOk("원본 상태입니다. 한국어 패치(" + pack.Version + ")를 적용할 수 있습니다.");
        else if (state == FileState.Target)
        {
            WriteOk("한국어 패치(" + pack.Version + ")가 적용된 상태입니다.");
            if (pack.Dll != null && DllState(dir, pack) == 3)
            {
                SetConsoleColor(ConsoleColor.Yellow);
                Console.WriteLine("[!] 다른 프로그램의 " + ProxyDllName + " 이 있어 실행 파일 속 문장 27개(언리미티드 모드 알림·전생 설명 등)는 깨져 보입니다.");
                Console.WriteLine("    패치 적용을 누르면 처리 방법(이어서 쓰기/덮어쓰기/건너뛰기)을 묻습니다.");
                ResetConsoleColor();
            }
            else if (pack.Dll != null && DllState(dir, pack) != 1)
            {
                SetConsoleColor(ConsoleColor.Yellow);
                Console.WriteLine("[!] " + ProxyDllName + " 이 없거나 다른 버전입니다. 패치 적용을 누르면 설치합니다.");
                ResetConsoleColor();
            }
        }
        else if (backup != null && DetectState(dir, backup.Files) == FileState.Target)
        {
            SetConsoleColor(ConsoleColor.Yellow);
            Console.WriteLine("[!] 이전 패치 버전(" + backup.PackVersion + ")이 적용된 상태입니다. 패치 적용 시 자동으로 갱신합니다.");
            ResetConsoleColor();
        }
        else
        {
            SetConsoleColor(ConsoleColor.Yellow);
            Console.WriteLine("[!] 알 수 없는 상태입니다. 게임 업데이트 또는 다른 수정이 있었을 수 있습니다.");
            Console.WriteLine("    Steam '게임 파일 무결성 검사' 후 다시 검사하세요.");
            ResetConsoleColor();
        }
    }

    // 0 = no dinput8.dll, 1 = ours and current, 2 = ours but another version, 3 = someone else's
    private static int DllState(string dir, Pack pack)
    {
        string path = Path.Combine(dir, ProxyDllName);
        if (!File.Exists(path))
            return 0;
        byte[] data = File.ReadAllBytes(path);
        using (SHA256 sha = SHA256.Create())
            if (pack.DllHash != null && EqualBytes(sha.ComputeHash(data), pack.DllHash))
                return 1;
        return IndexOf(data, ProxyMarker) >= 0 ? 2 : 3;
    }

    private static bool IsForeignDll(string dir)
    {
        string path = Path.Combine(dir, ProxyDllName);
        return File.Exists(path) && IndexOf(File.ReadAllBytes(path), ProxyMarker) < 0;
    }

    private static string ForeignDllQuestion(string dir)
    {
        return "설치 폴더에 다른 프로그램의 " + ProxyDllName + " 이 있습니다.\r\n" + Path.Combine(dir, ProxyDllName) + "\r\n\r\n" +
            "이어서 쓰기(권장): 기존 파일을 " + ChainDllName + " 로 옮기고, 한국어 패치의 " + ProxyDllName + " 이\r\n" +
            "    그 파일을 이어서 불러옵니다. 두 기능을 함께 씁니다. [원본 복구] 때 기존 파일을 되돌립니다.\r\n\r\n" +
            "덮어쓰기: 기존 파일을 " + ProxyDllName + ForeignDllSuffix + " 로 보관하고 한국어 패치의 " + ProxyDllName + " 로 교체합니다.\r\n" +
            "    그 프로그램(모드)의 기능은 꺼집니다. [원본 복구] 때 기존 파일을 되돌립니다.\r\n\r\n" +
            "건너뛰기: " + ProxyDllName + " 은 설치하지 않고 한국어 데이터만 적용합니다.\r\n" +
            "    실행 파일 속 문장 27개(언리미티드 모드 알림·전생 설명 등)는 깨져 보입니다.\r\n\r\n" +
            "취소: 아무것도 바꾸지 않고 중단합니다.";
    }

    private static ForeignDll DecideForeignDll(string dir, Options options)
    {
        SetConsoleColor(ConsoleColor.Yellow);
        Console.WriteLine("[!] 설치 폴더에 다른 프로그램의 " + ProxyDllName + " 이 있습니다: " + Path.Combine(dir, ProxyDllName));
        ResetConsoleColor();
        if (options.Foreign != ForeignDll.Ask)
            return options.Foreign;
        if (options.Yes)
        {
            Console.WriteLine("    이어서 씁니다 (덮어쓰려면 --overwrite-dll, 건너뛰려면 --skip-dll).");
            return ForeignDll.Chain;
        }
        Console.WriteLine(ForeignDllQuestion(dir).Replace("이어서 쓰기(권장):", "C 이어서 쓰기(권장):")
            .Replace("덮어쓰기:", "O 덮어쓰기:").Replace("건너뛰기:", "S 건너뛰기:").Replace("취소:", "N 취소:"));
        Console.Write("선택 [C=이어서 쓰기(Enter) / O=덮어쓰기 / S=건너뛰기 / N=중단]: ");
        string answer = (Console.ReadLine() ?? "").Trim();
        if (answer.Length == 0 || answer.Equals("C", StringComparison.OrdinalIgnoreCase))
            return ForeignDll.Chain;
        if (answer.Equals("O", StringComparison.OrdinalIgnoreCase))
            return ForeignDll.Overwrite;
        if (answer.Equals("S", StringComparison.OrdinalIgnoreCase))
            return ForeignDll.Skip;
        throw new OperationCanceledException("사용자가 작업을 취소했습니다.");
    }

    // moves 'from' to 'to'; an older file already at 'to' is kept under a timestamped name
    private static void KeepAs(string from, string to)
    {
        if (File.Exists(to))
            File.Move(to, Path.Combine(Path.GetDirectoryName(to),
                Path.GetFileNameWithoutExtension(to) + "." + DateTime.Now.ToString("yyyyMMddHHmmss") + Path.GetExtension(to)));
        File.Move(from, to);
    }

    // returns false when the dll was skipped (another program's dinput8.dll kept in place)
    private static bool InstallDll(string dir, Pack pack, ForeignDll foreignMode)
    {
        if (pack.Dll == null)
            return false;
        string path = Path.Combine(dir, ProxyDllName);
        if (DllState(dir, pack) == 3)
        {
            if (foreignMode == ForeignDll.Skip)
            {
                SetConsoleColor(ConsoleColor.Yellow);
                Console.WriteLine("[!] 다른 프로그램의 " + ProxyDllName + " 이 있어 설치하지 않았습니다. 실행 파일 속 문장 27개는 깨져 보입니다.");
                ResetConsoleColor();
                return false;
            }
            if (foreignMode == ForeignDll.Chain)
            {
                KeepAs(path, Path.Combine(dir, ChainDllName));
                WriteOk("기존 " + ProxyDllName + " 을 이어서 씁니다: " + ChainDllName + " (한국어 패치 DLL이 불러옵니다)");
            }
            else
            {
                KeepAs(path, path + ForeignDllSuffix);
                WriteOk("기존 " + ProxyDllName + " 보관: " + path + ForeignDllSuffix);
            }
        }
        File.WriteAllBytes(path + NewSuffix, pack.Dll);
        if (File.Exists(path))
            File.Delete(path);
        File.Move(path + NewSuffix, path);
        if (DllState(dir, pack) != 1)
            throw new InvalidDataException(ProxyDllName + " 설치 후 해시가 맞지 않습니다.");
        WriteOk(ProxyDllName + " 설치 완료 (실행 파일 속 문장 한국어화)");
        return true;
    }

    private static bool RemoveDll(string dir, Pack pack)
    {
        string path = Path.Combine(dir, ProxyDllName);
        int s = DllState(dir, pack);
        if (s == 0)
        {
            RestoreForeignDll(dir);
            return false;
        }
        if (s != 1 && s != 2)
            return false;
        File.Delete(path);
        string log = Path.Combine(dir, "WO3U_KR_dll.log");
        if (File.Exists(log))
            File.Delete(log);
        RestoreForeignDll(dir);
        return true;
    }

    // puts another program's dinput8.dll back (chained copy first, then the overwrite keep) when the name is free
    private static void RestoreForeignDll(string dir)
    {
        string path = Path.Combine(dir, ProxyDllName);
        foreach (string kept in new[] { Path.Combine(dir, ChainDllName), path + ForeignDllSuffix })
        {
            if (File.Exists(path) || !File.Exists(kept))
                continue;
            File.Move(kept, path);
            WriteOk("보관해 둔 다른 프로그램의 " + ProxyDllName + " 을 되돌렸습니다.");
        }
    }

    private static int IndexOf(byte[] data, byte[] pat)
    {
        for (int i = 0; i + pat.Length <= data.Length; i++)
        {
            int k = 0;
            while (k < pat.Length && data[i + k] == pat[k])
                k++;
            if (k == pat.Length)
                return i;
        }
        return -1;
    }

    private static void Confirm(bool automaticYes, string message)
    {
        if (automaticYes)
            return;
        if (!AskYes(message))
            throw new OperationCanceledException("사용자가 작업을 취소했습니다.");
    }

    private static bool AskYes(string message)
    {
        Console.Write(message);
        string answer = Console.ReadLine();
        return String.Equals(answer, "Y", StringComparison.OrdinalIgnoreCase);
    }

    private static void SetConsoleColor(ConsoleColor color)
    {
        try { Console.ForegroundColor = color; } catch { }
    }

    private static void ResetConsoleColor()
    {
        try { Console.ResetColor(); } catch { }
    }

    private static void WriteHeader()
    {
        SetConsoleColor(ConsoleColor.Cyan);
        Console.WriteLine("============================================================");
        Console.WriteLine(" " + GameTitle + " Steam판 (App " + AppId + ") 한국어 패처 " + versionText);
        Console.WriteLine("============================================================");
        ResetConsoleColor();
    }

    private static void WriteOk(string message)
    {
        SetConsoleColor(ConsoleColor.Green);
        Console.WriteLine("[OK] " + message);
        ResetConsoleColor();
    }

    private static void CheckFreeSpace(string dir, long need)
    {
        try
        {
            DriveInfo drive = new DriveInfo(Path.GetPathRoot(dir));
            if (drive.AvailableFreeSpace < need)
                throw new IOException(String.Format("여유 공간이 부족합니다. 필요 {0:N0} MB / 남은 공간 {1:N0} MB",
                    need >> 20, drive.AvailableFreeSpace >> 20));
        }
        catch (ArgumentException)
        {
        }
    }

    // ------------------------------------------------------------------ 팩 / 백업 읽기

    private static string ReadPackVersion(string path)
    {
        if (!File.Exists(path))
            return "(팩 없음: " + PackFileName + ")";
        using (BinaryReader reader = new BinaryReader(File.OpenRead(path), Encoding.UTF8))
        {
            if (Encoding.ASCII.GetString(ReadExactly(reader, 8)) != PackMagic)
                return "(팩 형식 오류)";
            reader.ReadInt32();
            return Encoding.UTF8.GetString(ReadExactly(reader, reader.ReadUInt16()));
        }
    }

    private static List<FileRecord> ReadFileRecords(BinaryReader reader)
    {
        List<FileRecord> files = new List<FileRecord>();
        for (int i = 0; i < TargetNames.Length; i++)
        {
            FileRecord f = new FileRecord();
            f.Name = Encoding.UTF8.GetString(ReadExactly(reader, reader.ReadUInt16()));
            if (!f.Name.Equals(TargetNames[i], StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException("파일 순서가 예상과 다릅니다: " + f.Name);
            f.SourceSize = checked((long)reader.ReadUInt64());
            f.SourceHash = ReadExactly(reader, 32);
            f.TargetSize = checked((long)reader.ReadUInt64());
            f.TargetHash = ReadExactly(reader, 32);
            files.Add(f);
        }
        return files;
    }

    private static void WriteFileRecords(BinaryWriter writer, List<FileRecord> files)
    {
        foreach (FileRecord f in files)
        {
            byte[] name = Encoding.UTF8.GetBytes(f.Name);
            writer.Write((ushort)name.Length);
            writer.Write(name);
            writer.Write((ulong)f.SourceSize);
            writer.Write(f.SourceHash);
            writer.Write((ulong)f.TargetSize);
            writer.Write(f.TargetHash);
        }
    }

    private static void ReadBlobIndex(BinaryReader reader, SortedDictionary<int, long> offsets, Dictionary<int, long> lengths, long streamLength)
    {
        int count = checked((int)reader.ReadUInt32());
        int previous = -1;
        for (int i = 0; i < count; i++)
        {
            int id = checked((int)reader.ReadUInt32());
            long length = checked((long)reader.ReadUInt64());
            long offset = reader.BaseStream.Position;
            if (id <= previous || length < 0 || offset + length > streamLength)
                throw new InvalidDataException("항목 데이터가 손상되었습니다 (id " + id + ").");
            offsets[id] = offset;
            lengths[id] = length;
            reader.BaseStream.Seek(length, SeekOrigin.Current);
            previous = id;
        }
        if (reader.BaseStream.Position != streamLength)
            throw new InvalidDataException("데이터 끝에 알 수 없는 내용이 있습니다.");
    }

    private static Pack LoadPack(string path)
    {
        if (!File.Exists(path))
            throw new FileNotFoundException("패치 데이터 파일이 없습니다. 패처 EXE 와 같은 폴더에 " + PackFileName + " 를 두세요.", path);
        Pack pack = new Pack();
        pack.Path = path;
        using (FileStream stream = File.OpenRead(path))
        using (BinaryReader reader = new BinaryReader(stream, Encoding.UTF8))
        {
            if (Encoding.ASCII.GetString(ReadExactly(reader, 8)) != PackMagic)
                throw new InvalidDataException("패치 데이터 형식이 올바르지 않습니다.");
            int format = reader.ReadInt32();
            if (format != 1 && format != PackFormatVersion)
                throw new InvalidDataException("지원하지 않는 패치 데이터 버전입니다.");
            pack.Version = Encoding.UTF8.GetString(ReadExactly(reader, reader.ReadUInt16()));
            pack.Files = ReadFileRecords(reader);
            pack.TargetIdx = ReadExactly(reader, checked((int)reader.ReadUInt32()));
            if (format >= 2)
            {
                int extras = checked((int)reader.ReadUInt32());
                for (int i = 0; i < extras; i++)
                {
                    string name = Encoding.UTF8.GetString(ReadExactly(reader, reader.ReadUInt16()));
                    byte[] hash = ReadExactly(reader, 32);
                    byte[] data = ReadExactly(reader, checked((int)reader.ReadUInt32()));
                    using (SHA256 sha = SHA256.Create())
                        if (!EqualBytes(sha.ComputeHash(data), hash))
                            throw new InvalidDataException("팩 안의 " + name + " 해시가 맞지 않습니다.");
                    if (name.Equals(ProxyDllName, StringComparison.OrdinalIgnoreCase)) { pack.Dll = data; pack.DllHash = hash; }
                }
            }
            if (pack.TargetIdx.Length != pack.Files[0].TargetSize)
                throw new InvalidDataException("팩의 인덱스 크기가 올바르지 않습니다.");
            ReadBlobIndex(reader, pack.BlobOffsets, pack.BlobLengths, stream.Length);
        }
        Console.WriteLine("[*] 패치 데이터 " + pack.Version + ": 교체 항목 " + pack.BlobOffsets.Count.ToString("N0") + "개");
        return pack;
    }

    private static Backup LoadBackup(string path)
    {
        Backup backup = new Backup();
        backup.Path = path;
        using (FileStream stream = File.OpenRead(path))
        using (BinaryReader reader = new BinaryReader(stream, Encoding.UTF8))
        {
            if (Encoding.ASCII.GetString(ReadExactly(reader, 8)) != BackupMagic)
                throw new InvalidDataException("선택한 파일은 이 패처의 복구 백업이 아닙니다: " + path);
            if (reader.ReadInt32() != BackupFormatVersion)
                throw new InvalidDataException("지원하지 않는 백업 형식입니다.");
            backup.PackVersion = Encoding.UTF8.GetString(ReadExactly(reader, reader.ReadUInt16()));
            backup.Files = ReadFileRecords(reader);
            backup.SourceIdx = ReadExactly(reader, checked((int)reader.ReadUInt32()));
            ReadBlobIndex(reader, backup.BlobOffsets, backup.BlobLengths, stream.Length);
        }
        return backup;
    }

    private static byte[] ReadExactly(BinaryReader reader, int count)
    {
        byte[] data = reader.ReadBytes(count);
        if (data.Length != count)
            throw new EndOfStreamException("데이터를 읽는 중 파일 끝에 도달했습니다.");
        return data;
    }

    private static IdxRecord[] ParseIdx(byte[] data)
    {
        IdxRecord[] records = new IdxRecord[data.Length / 32];
        for (int i = 0; i < records.Length; i++)
        {
            records[i].Offset = BitConverter.ToInt64(data, i * 32);
            records[i].Unpacked = BitConverter.ToInt64(data, i * 32 + 8);
            records[i].Stored = BitConverter.ToInt64(data, i * 32 + 16);
            records[i].Compressed = BitConverter.ToInt64(data, i * 32 + 24);
        }
        return records;
    }

    // ------------------------------------------------------------------ 상태 판별

    private static FileState DetectState(string dir, List<FileRecord> files)
    {
        bool source = true, target = true;
        for (int i = 0; i < files.Count; i++)
        {
            string path = Path.Combine(dir, files[i].Name);
            long size = new FileInfo(path).Length;
            bool maybeSource = size == files[i].SourceSize, maybeTarget = size == files[i].TargetSize;
            if (!maybeSource && !maybeTarget)
                return FileState.Unknown;
            byte[] hash = HashFile(path, files[i].Name);
            source &= maybeSource && EqualBytes(hash, files[i].SourceHash);
            target &= maybeTarget && EqualBytes(hash, files[i].TargetHash);
            if (!source && !target)
                return FileState.Unknown;
        }
        return source ? FileState.Source : (target ? FileState.Target : FileState.Unknown);
    }

    private static byte[] HashFile(string path, string label)
    {
        using (FileStream stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read, 1 << 20))
        using (SHA256 sha = SHA256.Create())
        {
            byte[] buffer = new byte[4 << 20];
            long total = stream.Length, done = 0;
            int read;
            while ((read = stream.Read(buffer, 0, buffer.Length)) > 0)
            {
                sha.TransformBlock(buffer, 0, read, null, 0);
                done += read;
                Report(total == 0 ? 1 : (double)done / total);
            }
            sha.TransformFinalBlock(buffer, 0, 0);
            Console.WriteLine("    SHA-256 " + label + " = " + ToHex(sha.Hash).Substring(0, 16) + "…");
            return sha.Hash;
        }
    }

    // ------------------------------------------------------------------ 재구성

    // baseBin/baseIdx(현재 파일)에서 targetIdx 배치로 새 파일을 만든다. blobs 에 있는 항목은 blobFile 에서 읽는다.
    private static byte[] Reconstruct(string baseBinPath, IdxRecord[] baseIdx, IdxRecord[] targetIdx,
        string blobFile, SortedDictionary<int, long> blobOffsets, Dictionary<int, long> blobLengths,
        long targetSize, string outPath)
    {
        List<int> ids = new List<int>();
        for (int i = 0; i < targetIdx.Length; i++)
            if (targetIdx[i].Stored != 0)
                ids.Add(i);
        ids.Sort(delegate(int a, int b) { return targetIdx[a].Offset.CompareTo(targetIdx[b].Offset); });

        byte[] buffer = new byte[4 << 20];
        byte[] zeros = new byte[0x10000];
        using (FileStream src = new FileStream(baseBinPath, FileMode.Open, FileAccess.Read, FileShare.Read, 1 << 20))
        using (FileStream blobs = new FileStream(blobFile, FileMode.Open, FileAccess.Read, FileShare.Read, 1 << 20))
        using (FileStream dst = new FileStream(outPath, FileMode.Create, FileAccess.Write, FileShare.None, 1 << 20))
        using (SHA256 sha = SHA256.Create())
        {
            long pos = 0;
            int n = 0;
            foreach (int id in ids)
            {
                IdxRecord t = targetIdx[id];
                if (t.Offset < pos)
                    throw new InvalidDataException("인덱스 배치가 겹칩니다 (id " + id + ").");
                WriteZeros(dst, sha, zeros, t.Offset - pos);
                FileStream from;
                long offset, length;
                if (blobOffsets.ContainsKey(id))
                {
                    from = blobs;
                    offset = blobOffsets[id];
                    length = blobLengths[id];
                }
                else
                {
                    if (id >= baseIdx.Length)
                        throw new InvalidDataException("원본 인덱스에 없는 항목입니다 (id " + id + ").");
                    from = src;
                    offset = baseIdx[id].Offset;
                    length = baseIdx[id].Stored;
                }
                if (length != t.Stored)
                    throw new InvalidDataException("항목 크기가 인덱스와 다릅니다 (id " + id + ").");
                from.Seek(offset, SeekOrigin.Begin);
                long left = length;
                while (left > 0)
                {
                    int chunk = (int)Math.Min(buffer.Length, left);
                    ReadFully(from, buffer, 0, chunk);
                    dst.Write(buffer, 0, chunk);
                    sha.TransformBlock(buffer, 0, chunk, null, 0);
                    left -= chunk;
                }
                pos = t.Offset + t.Stored;
                if (++n % 64 == 0)
                    Report((double)pos / targetSize);
            }
            if (pos > targetSize)
                throw new InvalidDataException("재구성 결과가 예상 크기보다 큽니다.");
            WriteZeros(dst, sha, zeros, targetSize - pos);
            sha.TransformFinalBlock(buffer, 0, 0);
            dst.Flush(true);
            Report(1);
            return sha.Hash;
        }
    }

    private static void WriteZeros(FileStream dst, SHA256 sha, byte[] zeros, long count)
    {
        while (count > 0)
        {
            int chunk = (int)Math.Min(zeros.Length, count);
            dst.Write(zeros, 0, chunk);
            sha.TransformBlock(zeros, 0, chunk, null, 0);
            count -= chunk;
        }
    }

    private static void ApplyPack(string dir, Pack pack)
    {
        string idxPath = Path.Combine(dir, TargetNames[0]);
        string binPath = Path.Combine(dir, TargetNames[1]);
        IdxRecord[] sourceIdx = ParseIdx(File.ReadAllBytes(idxPath));
        IdxRecord[] targetIdx = ParseIdx(pack.TargetIdx);
        Console.WriteLine("[*] 한국어 LINKFILE_CHS.BIN 재구성 중... (" + (pack.Files[1].TargetSize >> 20).ToString("N0") + " MB)");
        byte[] hash = Reconstruct(binPath, sourceIdx, targetIdx, pack.Path, pack.BlobOffsets, pack.BlobLengths,
            pack.Files[1].TargetSize, binPath + NewSuffix);
        if (!EqualBytes(hash, pack.Files[1].TargetHash))
        {
            File.Delete(binPath + NewSuffix);
            throw new InvalidDataException("재구성한 LINKFILE_CHS.BIN 의 해시가 일치하지 않습니다.");
        }
        WriteOk("재구성 결과 해시 일치");
        File.WriteAllBytes(idxPath + NewSuffix, pack.TargetIdx);
        SwapIn(dir);
    }

    private static void RestoreFromBackup(string dir, Backup backup)
    {
        string idxPath = Path.Combine(dir, TargetNames[0]);
        string binPath = Path.Combine(dir, TargetNames[1]);
        IdxRecord[] currentIdx = ParseIdx(File.ReadAllBytes(idxPath));
        IdxRecord[] sourceIdx = ParseIdx(backup.SourceIdx);
        Console.WriteLine("[*] 원본 LINKFILE_CHS.BIN 재구성 중...");
        byte[] hash = Reconstruct(binPath, currentIdx, sourceIdx, backup.Path, backup.BlobOffsets, backup.BlobLengths,
            backup.Files[1].SourceSize, binPath + NewSuffix);
        if (!EqualBytes(hash, backup.Files[1].SourceHash))
        {
            File.Delete(binPath + NewSuffix);
            throw new InvalidDataException("재구성한 원본 LINKFILE_CHS.BIN 의 해시가 일치하지 않습니다.");
        }
        WriteOk("원본 재구성 결과 해시 일치");
        File.WriteAllBytes(idxPath + NewSuffix, backup.SourceIdx);
        SwapIn(dir);
    }

    // 두 파일을 .wo3u-new 로 교체한다. 교체 도중 실패하면 .wo3u-old 로 되돌린다.
    private static void SwapIn(string dir)
    {
        List<string> swapped = new List<string>();
        try
        {
            foreach (string name in TargetNames)
            {
                string path = Path.Combine(dir, name);
                if (File.Exists(path + OldSuffix))
                    File.Delete(path + OldSuffix);
                File.Move(path, path + OldSuffix);
                File.Move(path + NewSuffix, path);
                swapped.Add(path);
            }
        }
        catch
        {
            foreach (string name in TargetNames)
            {
                string path = Path.Combine(dir, name);
                if (File.Exists(path + OldSuffix))
                {
                    if (File.Exists(path))
                        File.Delete(path);
                    File.Move(path + OldSuffix, path);
                }
            }
            throw;
        }
        foreach (string path in swapped)
            File.Delete(path + OldSuffix);
    }

    private static void CleanupTemp(string dir)
    {
        foreach (string name in TargetNames)
        {
            string path = Path.Combine(dir, name);
            try
            {
                if (File.Exists(path + NewSuffix))
                    File.Delete(path + NewSuffix);
                if (File.Exists(path + OldSuffix) && !File.Exists(path))
                    File.Move(path + OldSuffix, path);
            }
            catch { }
        }
    }

    // ------------------------------------------------------------------ 백업

    // 원본에서 팩이 교체하는 항목의 원본 저장 바이트 + 원본 인덱스를 저장한다.
    private static void CreateBackup(string dir, Pack pack, string backupPath)
    {
        string idxPath = Path.Combine(dir, TargetNames[0]);
        string binPath = Path.Combine(dir, TargetNames[1]);
        byte[] sourceIdxBytes = File.ReadAllBytes(idxPath);
        IdxRecord[] sourceIdx = ParseIdx(sourceIdxBytes);
        string temp = backupPath + ".tmp";
        byte[] buffer = new byte[4 << 20];
        using (FileStream src = new FileStream(binPath, FileMode.Open, FileAccess.Read, FileShare.Read, 1 << 20))
        using (FileStream dst = new FileStream(temp, FileMode.Create, FileAccess.Write, FileShare.None, 1 << 20))
        using (BinaryWriter writer = new BinaryWriter(dst, Encoding.UTF8))
        {
            writer.Write(Encoding.ASCII.GetBytes(BackupMagic));
            writer.Write(BackupFormatVersion);
            byte[] version = Encoding.UTF8.GetBytes(pack.Version);
            writer.Write((ushort)version.Length);
            writer.Write(version);
            WriteFileRecords(writer, pack.Files);
            writer.Write((uint)sourceIdxBytes.Length);
            writer.Write(sourceIdxBytes);
            writer.Write((uint)pack.BlobOffsets.Count);
            int n = 0;
            foreach (int id in pack.BlobOffsets.Keys)
            {
                if (id >= sourceIdx.Length || sourceIdx[id].Stored == 0)
                    throw new InvalidDataException("원본에 없는 항목을 교체하려 합니다 (id " + id + ").");
                writer.Write((uint)id);
                writer.Write((ulong)sourceIdx[id].Stored);
                src.Seek(sourceIdx[id].Offset, SeekOrigin.Begin);
                long left = sourceIdx[id].Stored;
                while (left > 0)
                {
                    int chunk = (int)Math.Min(buffer.Length, left);
                    ReadFully(src, buffer, 0, chunk);
                    writer.Write(buffer, 0, chunk);
                    left -= chunk;
                }
                if (++n % 32 == 0)
                    Report((double)n / pack.BlobOffsets.Count);
            }
            writer.Flush();
            dst.Flush(true);
        }
        LoadBackup(temp);   // 구조 검증
        if (File.Exists(backupPath))
            File.Delete(backupPath);
        File.Move(temp, backupPath);
    }

    private static void ReadFully(Stream stream, byte[] buffer, int offset, int count)
    {
        while (count > 0)
        {
            int read = stream.Read(buffer, offset, count);
            if (read <= 0)
                throw new EndOfStreamException("파일을 읽는 중 끝에 도달했습니다.");
            offset += read;
            count -= read;
        }
    }

    // ------------------------------------------------------------------ 선택: 병사 공격성 강화
    // LINKFILE_000.BIN (공통 데이터) 0x44CDA 의 유닛 표(2206 슬롯 x 40 바이트). 전투 병사 364 슬롯의 AI 단계(+32)를
    // 1(일반)/3(오로치·대장)으로 올리고, 근접 병사 289 슬롯은 분류(+34)=1·행동(+35)=4(무장 AI)로 바꾼다.
    // 원거리 병사·병기·백성·동물·장수는 그대로. 아래 표는 바뀌는 바이트마다 "표 안 위치(5)·원래 값(2)·새 값(2)" 16진.
    // 원래 값이 표에 들어 있으므로 따로 백업하지 않고, 표 전체 SHA-256 으로 원본/적용 상태를 판별한다.
    private const string SoldierFile = "LINKFILE_000.BIN";
    private const long SoldierOffset = 0x44CDA;
    private const int SoldierBlockSize = 2206 * 40;
    // <soldier-ai-table>
    private const string SoldierVanillaSha = "A6B62541DBE6CEF544B28FADB3524E12933F0D99CD19258C6634280E2DA2EA3D";
    private const string SoldierTargetSha = "791E7F8135942A894087CD4DFABEBB8926EDEB22CE7866B9F54876ED186093F2";
    private const string SoldierDiff =
        "0E23800010E23A00010E23B00040E91800030E91A00010E91B00040F90800030F90A00010F90B00040F98000010F98200010F9830004" +
        "0F9A800010F9AA00010F9AB00040F9D000010F9D200010F9D300040F9F800030F9FA00010F9FB00040FA2000030FA2200010FA230004" +
        "0FA4800030FA4A00010FA4B00040FA7000030FA7200010FA7300040FA9800010FA9A00010FA9B00040FAC000010FAC200010FAC30004" +
        "0FAE800010FAEA00010FAEB00040FB1000010FB1200010FB1300040FB3800030FB3A14010FB3B00040FB6000010FB6200010FB630204" +
        "0FB8800010FBD800010FC0000010FC0200010FC030F040FCC800010FCF000010FCF200010FCF300040FD1800010FD1A00010FD1B0004" +
        "0FD4000010FD4200010FD4300040FD6800010FD6A00010FD6B00040FD9000030FD9200010FD9300040FDB800030FDBA00010FDBB0004" +
        "0FDE000030FDE200010FDE300040FE0800030FE0A00010FE0B00040FE3000010FE3200010FE3300040FE5800010FE5A00010FE5B0004" +
        "0FE8000010FE8200010FE8300040FEA800010FEAA00010FEAB00040FED000030FED214010FED300040FEF800010FEFA00010FEFB0204" +
        "0FF2000010FF7000010FF9800010FF9A00010FF9B0F041006000011008800011008A00011008B0004103F80003103FA0001103FB0004" +
        "1042000031042200011042300041044800031044A00011044B00041047000031047200011047300041049800031049A00011049B0004" +
        "104C00003104C20001104C30004104E80003104EA0001104EB00041051000031051200011051300041053800031053A00011053B0004" +
        "1056000031056200011056300041058800031058A00011058B0004105B00003105B20001105B30004105D80003105DA0001105DB0004" +
        "1060000031060200011060300041062800031062A00011062B00041065000031065200011065300041067800011067A00011067B0004" +
        "106A00001106A20001106A30004106C80001106CA0001106CB0004106F00001106F20001106F300041071800011071A00011071B0004" +
        "1074000011074200011074300041076800011076A00011076B0004107900001107920001107930004107B80001107BA0001107BB0004" +
        "107E00001107E20001107E300041080800011080A00011080B00041083000011083200011083300041085800011085A00011085B0004" +
        "108800001108820001108830004108A80001108AA0001108AB0004108D00001108D20001108D30004108F80001108FA0001108FB0004" +
        "1092000011092200011092300041094800011094A00011094B00041097000011097200011097300041099800011099A00011099B0004" +
        "109C00001109C20001109C30004109E80001109EA0001109EB000410A10000110A12000110A13000410BA0000110BA2000110BA30004" +
        "10BC8000310BCA000110BCB000410BF0000110BF2000110BF3000410C18000110C1A000110C1B000410C40000310C42000110C430004" +
        "10C68000110C6A000110C6B000410D58000310D5A000110D5B000410D80000310D82000110D83000410DA8000310DAA000110DAB0004" +
        "10DD0000310DD2000110DD3000410DF8000310DFA000110DFB000410E20000310E22000110E23000410E48000310E4A000110E4B0004" +
        "10E70000310E72000110E73000410E98000310E9A000110E9B000410EC0000310EC2000110EC3000410EE8000310EEA000110EEB0004" +
        "10F10000310F12140110F13000410F38000310F3A000110F3B020410F60000310F88000310F8A040110F8B0A0410FB0000310FD80003" +
        "10FDA000110FDB0F04110000003110020001110030004110500003110521601110530B041107800031107A16011107B0004110A00003" +
        "110C80003110CA0001110CB0004111900001111920001111930004111B80001111E00001111E20001111E300041120800011120A0001" +
        "1120B00041123000011123200011123300041125800011125A00011125B0004112A80001112AA0001112AB0004112D00001112D20001" +
        "112D30004112F80001112FA0001112FB00041132000011134800011139800011139A00011139B0004113C00001113C20001113C30004" +
        "1141000031141200011141300041143800011143A00011143B00041146000011146200011146300041148800031148A14011148B0F04" +
        "114B00003114B21401114B30F04114D80003114DA1401114DB0F04115000003115021401115030F041152800031152A14011152B0F04" +
        "115500003115520001115530004115A00003115A20001115A30004115C80001115CA0001115CB00041166800031166A14011166B0F04" +
        "11D98000111D9A000111D9B000411DC0000111DC2000111DC3000411DE8000111DEA000111DEB000411E10000311E12000111E130004" +
        "11E38000311E3A000111E3B000411E60000311E62000111E63000411E88000311E8A000111E8B000411EB0000111EB2000111EB30004" +
        "11ED8000111EDA000111EDB000411F00000111F02000111F03000411F28000111F2A000111F2B000411F50000311F52140111F530004" +
        "11F78000111F7A000111F7B020411FA0000111FF000011201800011201A00011201B0F04120E000011210800011210A00011210B0004" +
        "1213000011213200011213300041215800011215A00011215B0004121800001121820001121830004121A80003121AA0001121AB0004" +
        "121D00003121D20001121D30004121F80003121FA0001121FB00041222000031222200011222300041224800011224A00011224B0004" +
        "1227000011227200011227300041229800011229A00011229B0004122C00001122C20001122C30004122E80003122EA1401122EB0004" +
        "123100001123120001123130204123380001123880001123B00001123B20001123B30F04124780001124A00001124A20001124A30004" +
        "124C80003124CA0001124CB0004124F00003124F20001124F300041251800031251A00011251B0004125400003125420001125430004" +
        "1256800031256A00011256B0004125900003125920001125930004125B80003125BA0001125BB0004125E00003125E20001125E30004" +
        "1260800031260A00011260B00041263000031263200011263300041265800031265A00011265B0004126800003126821401126830004" +
        "126A80003126AA0001126AB0204126D00003126F80003126FA0401126FB0A041272000031274800031274A00011274B0F04127700003" +
        "1277200011277300041279800031279A00011279B0004127C00003127C21601127C30B04127E80003127EA1601127EB0004128100003" +
        "1283800031283A00011283B000412C70000112C73030412C98000112C9B030412CC0000112CC3030412CE8000112CEB030412D100001" +
        "12D13030412D38000112D3B030412D60000112D63030412D88000112D8B030412DB0000112DB3030412E28000312E2B0304139900001" +
        "139920001139936004139B80001139BA0001139BB6004139E00001139E20001139E3600413A08000113A0A000113A0B600413A300001" +
        "13A32000113A33600413A58000113A5A000113A5B600413A80000113A82000113A83600413AA8000113AAA000113AAB600413AD00001" +
        "13AD2000113AD3600413AF8000113AFA000113AFB600413B20000113B22000113B23600413B48000113B4A000113B4B600413B700001" +
        "13B72000113B73600413B98000113B9A000113B9B600413BC0000113BC2000113BC3600413BE8000113BEA000113BEB400413C100001" +
        "13C12000113C13400413C38000113C3A000113C3B400413C60000113C62000113C63400413C88000113C8A000113C8B400413CB00001" +
        "13CB2000113CB3400413CD8000113CDA000113CDB400413D00000113D02000113D03400413D28000113D2A000113D2B400413D500003" +
        "13D52000113D53400413D78000313D7A000113D7B400413DA0000313DA2000113DA3400413DC8000313DCA000113DCB400413DF00003" +
        "13DF2000113DF3400413E18000313E1A000113E1B400413E40000113E42000113E43400413E68000113E6A000113E6B400413E900001" +
        "13E92000113E93400413EB8000113EBA000113EBB470413EE0000113EE2000113EE3470413F08000113F0A000113F0B470413F300001" +
        "13F32000113F334704140980001140C00001140E80001141100001141380001141600001141880001141B00001141D80001142000001" +
        "142280001142500001142C80003142F00003143180001143400001143680001143900001143B80001143BA0001143BB5404143E00001" +
        "143E20001143E35404144580003144800003144A80001144D000011459800011459A00011459B4004145C00001145C20001145C34004" +
        "1493000011493200011493360041495800011495A00011495B6004149800001149820001149836004149A80001149AA0001149AB6004" +
        "149D00001149D20001149D36004149F80001149FA0001149FB600414A20000114A22000114A23600414A48000114A4A000114A4B6004" +
        "14A70000114A72000114A73600414A98000114A9A000114A9B600414AC0000114AC2000114AC3600414AE8000114AEA000114AEB6004" +
        "14B10000114B12000114B13600414B38000114B3A000114B3B600414B60000114B62000114B63600414B88000114B8A000114B8B4004" +
        "14BB0000114BB2000114BB3400414BD8000114BDA000114BDB400414C00000114C02000114C03400414C28000114C2A000114C2B4004" +
        "14C50000114C52000114C53400414C78000114C7A000114C7B400414CA0000114CA2000114CA3400414CC8000114CCA000114CCB4004" +
        "14CF0000314CF2000114CF3400414D18000314D1A000114D1B400414D40000314D42000114D43400414D68000314D6A000114D6B4004" +
        "14D90000314D92000114D93400414DB8000314DBA000114DBB400414DE0000114DE2000114DE3400414E08000114E0A000114E0B4004" +
        "14E30000114E32000114E33400414E58000114E5A000114E5B470414E80000114E82000114E83470414EA8000114EAA000114EAB4704" +
        "14ED0000114ED2000114ED3470414EF8000114EFA000114EFB470414F20000114F22000114F23470414F48000114F4A000114F4B4104" +
        "14F70000114F72000114F73410414F98000114F9A000114F9B410414FC0000114FC2000114FC3410414FE8000114FEA000114FEB6804" +
        "150100001150120001150136804150380001150600001150880001150B00001150D80001151000001151280001151500001151780001" +
        "151A00001151C80001151F000011521800011521A00011521B5404152400001152420001152435404152680003152900003152B80001" +
        "152E000011530800011533000011535800011535A00011535B5404153800001153820001153835404153A80001153AA0001153AB5404" +
        "153D00001153D20001153D35404153F800031542000031544800011547000011549800011549A00011549B6804154C00001154C20001" +
        "154C36804154E80001154EA0001154EB40041551000011551200011551340041553800011553A00011553B4004155600001155620001" +
        "1556340041558800011558A00011558B4004155B00001155B20001155B34004155D80001155DA0001155DBFF04156000001156020001" +
        "15603FF041562800011562A00011562BFF0415650000115652000115653FF041567800011567A00011567BFF04156A00001156A20001" +
        "156A3FF04156C80001156CA0001156CBFF04156F00001156F20001156F3FF041571800011571A00011571BFF04157400001157420001" +
        "15743FF041576800011576A00011576BFF0415790000115792000115793FF04157B80001157BA0001157BBFF04157E00001157E20001" +
        "157E3FF041580800011580A00011580BFF0415830000115832000115833FF041585800011585A00011585BFF04158800001158820001" +
        "15883FF04158A80001158AA0001158ABFF04";
    // </soldier-ai-table>

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

    private static bool EqualBytes(byte[] left, byte[] right)
    {
        if (left == null || right == null || left.Length != right.Length)
            return false;
        for (int i = 0; i < left.Length; i++)
            if (left[i] != right[i])
                return false;
        return true;
    }

    private static string ToHex(byte[] data)
    {
        StringBuilder builder = new StringBuilder(data.Length * 2);
        foreach (byte value in data)
            builder.Append(value.ToString("X2"));
        return builder.ToString();
    }
}
