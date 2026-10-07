r"""One-off edit (2026-10-07, issues #10/#11): the patcher also writes the Korean DLC costume source texts into the
common part LINKFILE_003.BIN (pack extra 'LINKFILE_003.patch', made by tools/gen_common003.py).

- applied together with the Korean patch, reverted by [원본 복구]; originals saved to WO3U_KR_003.wo3u-backup
- state per block by SHA-256: original / Korean / other (other = game update or another mod -> left alone)
"""
import shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CS = HERE / "WO3USteamPatch.cs"
s = CS.read_text(encoding="utf-8-sig")
if "Common003" in s:
    sys.exit("already applied")
shutil.copy2(CS, HERE.parent / "backup" / "WO3USteamPatch.cs.before_common003")


def rep(old, new, count=1):
    global s
    if s.count(old) != count:
        sys.exit(f"expected {count} x {old[:70]!r}, found {s.count(old)}")
    s = s.replace(old, new)


rep("        public byte[] DllHash;\n",
    "        public byte[] DllHash;\n        public byte[] Common003;   // LINKFILE_003.patch (DLC costume source texts), see Common003Records\n")
rep("""                    if (name.Equals(ProxyDllName, StringComparison.OrdinalIgnoreCase)) { pack.Dll = data; pack.DllHash = hash; }""",
    """                    if (name.Equals(ProxyDllName, StringComparison.OrdinalIgnoreCase)) { pack.Dll = data; pack.DllHash = hash; }
                    else if (name.Equals(Common003PatchName, StringComparison.OrdinalIgnoreCase)) pack.Common003 = data;""")
rep("""        Console.WriteLine("[*] 패치 데이터 " + pack.Version + ": 교체 항목 " + pack.BlobOffsets.Count.ToString("N0") + "개");
        return pack;""", """        Console.WriteLine("[*] 패치 데이터 " + pack.Version + ": 교체 항목 " + pack.BlobOffsets.Count.ToString("N0") + "개");
        loadedPack = pack;
        return pack;""")

rep("""    private static int Run(Options options)
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
    }""", """    private static int Run(Options options)
    {
        loadedPack = null;
        int result = RunKorean(options);
        string dir = options.FolderPath;
        if (options.VerifyOnly)
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
        }
        return result;
    }""")

rep("""    // ------------------------------------------------------------------ 선택: 병사 공격성 강화""", r"""    // ------------------------------------------------------------------ 공통 데이터: DLC 의상 출전 문구
    // DLC 의상마다 공통 파일 LINKFILE_003.BIN 에 4개 언어(일·영·번체·간체) 문구가 든 작은 압축 항목이 있다.
    // 게임 언어가 간체이면 간체 문구를 보여 주므로, 그 자리에 한국어를 넣은 항목(같은 저장 크기)으로 바꾼다.
    // 팩의 LINKFILE_003.patch: "WO3UC003" u32 개수, 항목마다 u32 id, u64 위치, u32 크기, 원본 SHA-256, 한국어 SHA-256, 한국어 바이트.
    // 원본 블록은 처음 쓸 때 WO3U_KR_003.wo3u-backup 에 저장하고, [원본 복구] 때 되돌린다.
    private const string Common003PatchName = "LINKFILE_003.patch";
    private const string Common003File = "LINKFILE_003.BIN";
    private const string Common003Backup = "WO3U_KR_003" + BackupExtension;
    private static Pack loadedPack;

    private sealed class Common003Record
    {
        public long Offset;
        public int Size;
        public byte[] OrigHash;
        public byte[] NewHash;
        public byte[] Data;
    }

    private static List<Common003Record> Common003Records(Pack pack)
    {
        List<Common003Record> list = new List<Common003Record>();
        if (pack == null || pack.Common003 == null)
            return list;
        using (BinaryReader reader = new BinaryReader(new MemoryStream(pack.Common003)))
        {
            if (Encoding.ASCII.GetString(reader.ReadBytes(8)) != "WO3UC003")
                throw new InvalidDataException(Common003PatchName + " 형식이 올바르지 않습니다.");
            int count = reader.ReadInt32();
            for (int i = 0; i < count; i++)
            {
                Common003Record r = new Common003Record();
                reader.ReadUInt32();
                r.Offset = reader.ReadInt64();
                r.Size = reader.ReadInt32();
                r.OrigHash = reader.ReadBytes(32);
                r.NewHash = reader.ReadBytes(32);
                r.Data = reader.ReadBytes(r.Size);
                list.Add(r);
            }
        }
        return list;
    }

    // 0 = 원본, 1 = 한국어, 2 = 기타. counts[3] 반환
    private static int[] Common003Counts(string dir, List<Common003Record> records)
    {
        int[] counts = new int[3];
        string path = Path.Combine(dir, Common003File);
        if (!File.Exists(path))
        {
            counts[2] = records.Count;
            return counts;
        }
        using (FileStream stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read))
        using (SHA256 sha = SHA256.Create())
        {
            foreach (Common003Record r in records)
            {
                byte[] cur = new byte[r.Size];
                stream.Position = r.Offset;
                ReadFully(stream, cur, 0, cur.Length);
                byte[] h = sha.ComputeHash(cur);
                counts[EqualBytes(h, r.OrigHash) ? 0 : EqualBytes(h, r.NewHash) ? 1 : 2]++;
            }
        }
        return counts;
    }

    private static void PrintCommon003State(string dir, Pack pack)
    {
        List<Common003Record> records = Common003Records(pack);
        if (records.Count == 0)
            return;
        int[] c = Common003Counts(dir, records);
        if (c[1] == records.Count)
            Console.WriteLine("[*] DLC 의상 출전 문구(" + Common003File + ") " + records.Count + "개가 한국어입니다.");
        else if (c[0] == records.Count)
            Console.WriteLine("[*] DLC 의상 출전 문구(" + Common003File + ")는 원본입니다. 패치 적용 때 한국어로 바꿉니다.");
        else
            Console.WriteLine("[*] DLC 의상 출전 문구: 원본 " + c[0] + " / 한국어 " + c[1] + " / 기타 " + c[2] + " (" + Common003File + ")");
    }

    // on = 한국어로, off = 원본으로. 블록마다 해시를 보고 원본/한국어인 것만 바꾼다(기타는 건드리지 않음).
    private static void SetCommon003(string dir, Pack pack, bool on)
    {
        List<Common003Record> records = Common003Records(pack);
        string path = Path.Combine(dir, Common003File);
        if (records.Count == 0 || !File.Exists(path))
            return;
        int[] before = Common003Counts(dir, records);
        string backupPath = Path.Combine(dir, Common003Backup);
        if (on && before[1] == records.Count)
        {
            WriteOk("DLC 의상 출전 문구는 이미 한국어입니다 (" + records.Count + "개).");
            return;
        }
        if (!on && before[1] == 0)
            return;
        Dictionary<long, byte[]> originals = new Dictionary<long, byte[]>();
        if (File.Exists(backupPath))
            using (BinaryReader reader = new BinaryReader(File.OpenRead(backupPath)))
            {
                if (Encoding.ASCII.GetString(reader.ReadBytes(8)) == "WO3UB003")
                {
                    int count = reader.ReadInt32();
                    for (int i = 0; i < count; i++)
                    {
                        long offset = reader.ReadInt64();
                        originals[offset] = reader.ReadBytes(reader.ReadInt32());
                    }
                }
            }
        int changed = 0, skipped = 0;
        using (FileStream stream = new FileStream(path, FileMode.Open, FileAccess.ReadWrite, FileShare.None))
        using (SHA256 sha = SHA256.Create())
        {
            // 1) decide every block first (and collect the originals that are about to be overwritten)
            List<KeyValuePair<long, byte[]>> writes = new List<KeyValuePair<long, byte[]>>();
            foreach (Common003Record r in records)
            {
                byte[] cur = new byte[r.Size];
                stream.Position = r.Offset;
                ReadFully(stream, cur, 0, cur.Length);
                byte[] h = sha.ComputeHash(cur);
                bool isOrig = EqualBytes(h, r.OrigHash), isNew = EqualBytes(h, r.NewHash);
                if (on && isOrig)
                {
                    originals[r.Offset] = cur;
                    writes.Add(new KeyValuePair<long, byte[]>(r.Offset, r.Data));
                }
                else if (!on && isNew)
                {
                    byte[] orig;
                    if (originals.TryGetValue(r.Offset, out orig) && EqualBytes(sha.ComputeHash(orig), r.OrigHash))
                        writes.Add(new KeyValuePair<long, byte[]>(r.Offset, orig));
                    else
                        skipped++;
                }
                else if (!isOrig && !isNew)
                    skipped++;
            }
            // 2) keep the originals on disk before the first write, then write
            if (on && writes.Count > 0)
                SaveCommon003Backup(backupPath, originals);
            foreach (KeyValuePair<long, byte[]> w in writes)
            {
                stream.Position = w.Key;
                stream.Write(w.Value, 0, w.Value.Length);
                changed++;
            }
            stream.Flush(true);
        }
        int[] after = Common003Counts(dir, records);
        if (on && after[1] != before[1] + changed || !on && after[0] != before[0] + changed)
            throw new InvalidDataException("DLC 의상 출전 문구(" + Common003File + ") 쓰기 후 검증에 실패했습니다. Steam '게임 파일 무결성 검사'로 원본을 받으세요.");
        if (changed > 0)
            WriteOk(on ? "DLC 의상 출전 문구 " + changed + "개를 한국어로 바꾸고 검증했습니다 (" + Common003File + ")"
                       : "DLC 의상 출전 문구 " + changed + "개를 원본으로 되돌리고 검증했습니다 (" + Common003File + ")");
        if (skipped > 0)
        {
            SetConsoleColor(ConsoleColor.Yellow);
            Console.WriteLine("[!] DLC 의상 출전 문구 " + skipped + "개는 원본도 패치본도 아니어서(게임 업데이트 등) 건드리지 않았습니다.");
            ResetConsoleColor();
        }
    }

    private static void SaveCommon003Backup(string backupPath, Dictionary<long, byte[]> originals)
    {
        string temp = backupPath + ".tmp";
        using (BinaryWriter writer = new BinaryWriter(File.Create(temp)))
        {
            writer.Write(Encoding.ASCII.GetBytes("WO3UB003"));
            writer.Write(originals.Count);
            foreach (KeyValuePair<long, byte[]> pair in originals)
            {
                writer.Write(pair.Key);
                writer.Write(pair.Value.Length);
                writer.Write(pair.Value);
            }
        }
        if (File.Exists(backupPath))
            File.Delete(backupPath);
        File.Move(temp, backupPath);
    }

    // ------------------------------------------------------------------ 선택: 병사 공격성 강화""")

CS.write_text(s, encoding="utf-8-sig")
print("ok")
