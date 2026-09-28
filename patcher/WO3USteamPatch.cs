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
    private const string ForeignDllSuffix = ".wo3u-orig";  // another program's dinput8.dll kept while ours is installed
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
    }

    // what to do with another program's dinput8.dll: ask (interactive console), overwrite (kept as .wo3u-orig), skip
    private enum ForeignDll
    {
        Ask,
        Overwrite,
        Skip
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
            ClientSize = new Size(900, 850);
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

            Label logLabel = new Label();
            logLabel.Text = "진행 로그";
            logLabel.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
            logLabel.AutoSize = true;
            logLabel.Location = new Point(22, 445);
            Controls.Add(logLabel);

            logBox = new RichTextBox();
            logBox.SetBounds(22, 467, 856, 280);
            logBox.ReadOnly = true;
            logBox.BackColor = Color.FromArgb(22, 28, 34);
            logBox.ForeColor = Color.FromArgb(225, 235, 240);
            logBox.Font = new Font("Consolas", 9F);
            logBox.WordWrap = false;
            Controls.Add(logBox);

            verifyButton = AddButton("상태 검사", 22, 763, 140, false, Color.Empty,
                delegate { StartOperation(UiOperation.Verify); });
            patchButton = AddButton("한국어 패치 적용", 172, 763, 230, true, Color.FromArgb(34, 112, 166),
                delegate { StartOperation(UiOperation.Patch); });
            restoreButton = AddButton("원본 복구", 412, 763, 140, false, Color.Empty,
                delegate { StartOperation(UiOperation.Restore); });
            closeButton = AddButton("닫기", 758, 763, 120, false, Color.Empty, delegate { Close(); });

            progressBar = new ProgressBar();
            progressBar.SetBounds(22, 817, 650, 16);
            progressBar.Minimum = 0;
            progressBar.Maximum = 1000;
            Controls.Add(progressBar);

            statusLabel = new Label();
            statusLabel.Text = "대기 중";
            statusLabel.TextAlign = ContentAlignment.MiddleRight;
            statusLabel.SetBounds(685, 812, 193, 25);
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

            ForeignDll foreign = ForeignDll.Skip;
            if (operation == UiOperation.Patch)
            {
                DialogResult answer = MessageBox.Show(this,
                    "다음 설치 폴더의 LINKIDX_CHS.BIN / LINKFILE_CHS.BIN 을 한국어 버전으로 교체합니다.\r\n\r\n" + targetPath +
                    "\r\n\r\n복구 백업: " + backupPath + "\r\n\r\n게임이 완전히 종료되었습니까?",
                    "패치 확인", MessageBoxButtons.YesNo, MessageBoxIcon.Warning, MessageBoxDefaultButton.Button2);
                if (answer != DialogResult.Yes)
                    return;
                if (IsForeignDll(targetPath))
                {
                    DialogResult choice = MessageBox.Show(this, ForeignDllQuestion(targetPath),
                        "다른 " + ProxyDllName + " 발견", MessageBoxButtons.YesNoCancel, MessageBoxIcon.Question, MessageBoxDefaultButton.Button2);
                    if (choice == DialogResult.Cancel)
                        return;
                    foreign = choice == DialogResult.Yes ? ForeignDll.Overwrite : ForeignDll.Skip;
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
            worker.RunWorkerAsync(new UiWorkItem { Operation = operation, TargetPath = targetPath, BackupPath = backupPath, Foreign = foreign });
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
                warningCheck, verifyButton, patchButton, restoreButton, closeButton
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
            else if (arg.Equals("--overwrite-dll", StringComparison.OrdinalIgnoreCase))
                options.Foreign = ForeignDll.Overwrite;
            else if (arg.Equals("--skip-dll", StringComparison.OrdinalIgnoreCase))
                options.Foreign = ForeignDll.Skip;
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
                    "사용법: WO3U_Steam_KR_Patch.exe [--folder <설치 폴더>] [--backup <백업 파일>] [--verify-only | --restore] [--yes] [--overwrite-dll | --skip-dll] [--no-pause]\r\n" +
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

        bool overwriteForeign = false;
        if (pack.Dll != null && DllState(dir, pack) == 3)
            overwriteForeign = DecideForeignDll(dir, options);

        if (state == FileState.Target && pack.Dll != null && DllState(dir, pack) != 1)
        {
            if (InstallDll(dir, pack, overwriteForeign))
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
            dllInstalled = InstallDll(dir, pack, overwriteForeign);
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
        if (File.Exists(Path.Combine(dir, ProxyDllName + ForeignDllSuffix)))
            Console.WriteLine("[*] 다른 프로그램의 " + ProxyDllName + " 을 보관 중입니다: " + ProxyDllName + ForeignDllSuffix + " (원본 복구 때 되돌립니다)");
        if (state != FileState.Target && pack.Dll != null && DllState(dir, pack) == 3)
            Console.WriteLine("[*] 설치 폴더에 다른 프로그램의 " + ProxyDllName + " 이 있습니다. 패치 적용 때 덮어쓸지 묻습니다.");
        if (state == FileState.Source)
            WriteOk("원본 상태입니다. 한국어 패치(" + pack.Version + ")를 적용할 수 있습니다.");
        else if (state == FileState.Target)
        {
            WriteOk("한국어 패치(" + pack.Version + ")가 적용된 상태입니다.");
            if (pack.Dll != null && DllState(dir, pack) == 3)
            {
                SetConsoleColor(ConsoleColor.Yellow);
                Console.WriteLine("[!] 다른 프로그램의 " + ProxyDllName + " 이 있어 실행 파일 속 문장 27개(언리미티드 모드 알림·전생 설명 등)는 깨져 보입니다.");
                Console.WriteLine("    패치 적용을 누르면 덮어쓸지 묻습니다.");
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
            "예: 기존 파일을 " + ProxyDllName + ForeignDllSuffix + " 로 보관하고 한국어 패치의 " + ProxyDllName + " 로 교체합니다.\r\n" +
            "    그 프로그램(모드)의 기능은 꺼집니다. [원본 복구] 때 기존 파일을 되돌립니다.\r\n\r\n" +
            "아니요: " + ProxyDllName + " 은 건너뛰고 한국어 데이터만 적용합니다.\r\n" +
            "    실행 파일 속 문장 27개(언리미티드 모드 알림·전생 설명 등)는 깨져 보입니다.\r\n\r\n" +
            "취소: 아무것도 바꾸지 않고 중단합니다.";
    }

    // true = overwrite (keep the other file as .wo3u-orig), false = skip the dll
    private static bool DecideForeignDll(string dir, Options options)
    {
        SetConsoleColor(ConsoleColor.Yellow);
        Console.WriteLine("[!] 설치 폴더에 다른 프로그램의 " + ProxyDllName + " 이 있습니다: " + Path.Combine(dir, ProxyDllName));
        ResetConsoleColor();
        if (options.Foreign == ForeignDll.Overwrite)
            return true;
        if (options.Foreign == ForeignDll.Skip || options.Yes)
        {
            Console.WriteLine("    덮어쓰지 않고 건너뜁니다 (덮어쓰려면 --overwrite-dll). 실행 파일 속 문장 27개는 깨져 보입니다.");
            return false;
        }
        Console.WriteLine(ForeignDllQuestion(dir).Replace("예:", "O:").Replace("아니요:", "S:").Replace("취소:", "N:"));
        Console.Write("선택 [O=덮어쓰기 / S=건너뛰기 / N=중단]: ");
        string answer = (Console.ReadLine() ?? "").Trim();
        if (answer.Equals("O", StringComparison.OrdinalIgnoreCase))
            return true;
        if (answer.Equals("S", StringComparison.OrdinalIgnoreCase))
            return false;
        throw new OperationCanceledException("사용자가 작업을 취소했습니다.");
    }

    // returns false when the dll was skipped (another program's dinput8.dll kept in place)
    private static bool InstallDll(string dir, Pack pack, bool overwriteForeign)
    {
        if (pack.Dll == null)
            return false;
        string path = Path.Combine(dir, ProxyDllName);
        if (DllState(dir, pack) == 3)
        {
            if (!overwriteForeign)
            {
                SetConsoleColor(ConsoleColor.Yellow);
                Console.WriteLine("[!] 다른 프로그램의 " + ProxyDllName + " 이 있어 설치하지 않았습니다. 실행 파일 속 문장 27개는 깨져 보입니다.");
                ResetConsoleColor();
                return false;
            }
            string kept = path + ForeignDllSuffix;
            if (File.Exists(kept))
                File.Move(kept, path + "." + DateTime.Now.ToString("yyyyMMddHHmmss") + ForeignDllSuffix);
            File.Move(path, kept);
            WriteOk("기존 " + ProxyDllName + " 보관: " + kept);
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
        string keptOnly = path + ForeignDllSuffix;
        if (s == 0 && File.Exists(keptOnly))
        {
            File.Move(keptOnly, path);
            WriteOk("보관해 둔 다른 프로그램의 " + ProxyDllName + " 을 되돌렸습니다.");
            return false;
        }
        if (s != 1 && s != 2)
            return false;
        File.Delete(path);
        string log = Path.Combine(dir, "WO3U_KR_dll.log");
        if (File.Exists(log))
            File.Delete(log);
        string kept = path + ForeignDllSuffix;
        if (File.Exists(kept))
        {
            File.Move(kept, path);
            WriteOk("보관해 둔 다른 프로그램의 " + ProxyDllName + " 을 되돌렸습니다.");
        }
        return true;
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
