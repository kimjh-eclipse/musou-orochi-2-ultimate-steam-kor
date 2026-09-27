"""Steam patch package: (build_steam_pack.py) -> csc -> package folder (EXE + pack + README + SHA256SUMS) -> ZIP.

usage: build_package.py <version> [--rebuild <build dir>]
  --rebuild: regenerate WO3U_Steam_KR.pack from backup/original + <build dir> first.
Needs Windows .NET Framework 4.x csc.exe.
"""
import hashlib, json, shutil, subprocess, sys, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "out"
CSC = Path(r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe")
SOURCE = HERE / "WO3USteamPatch.cs"
EXE_NAME = "WO3U_Steam_KR_Patch.exe"
PACK = OUT / "WO3U_Steam_KR.pack"
MANIFEST = OUT / "WO3U_Steam_KR.manifest.json"

README = """무쌍 오로치 2 얼티메이트 Steam판 한국어 패치 {version}
대상: Steam WARRIORS OROCHI 3 Ultimate Definitive Edition (App 1879330)

[설치]
1. Steam 에서 게임 속성 → 언어를 중국어 간체(简体中文)로 바꾸고 다운로드가 끝날 때까지 기다립니다.
2. 게임을 완전히 종료합니다.
3. 이 폴더의 WO3U_Steam_KR_Patch.exe 를 실행합니다. (WO3U_Steam_KR.pack 과 같은 폴더에 두세요)
4. 설치 폴더가 자동으로 채워집니다. 비어 있으면 [자동 찾기] 또는 [찾아보기...]로
   ...\\steamapps\\common\\WARRIORS OROCHI 3 Ultimate 폴더를 지정합니다.
5. [상태 검사]로 원본 상태인지 확인합니다.
6. 주의사항에 동의한 뒤 [한국어 패치 적용]을 누릅니다.
   Program Files 아래에 설치했다면 관리자 권한 실행을 묻습니다.

설치 폴더의 LINKIDX_CHS.BIN / LINKFILE_CHS.BIN 두 파일만 교체되며,
기본 위치(설치 폴더 안)에 WO3U_KR.wo3u-backup 백업이 생깁니다.
이 백업으로 원본 복구와 다음 버전 갱신을 합니다. 삭제하지 마세요.

[복구]
- 패처의 [원본 복구] 또는 Steam '게임 파일 무결성 검사'로 원본에 돌아갈 수 있습니다.
- Steam 무결성 검사나 게임 업데이트 뒤에는 두 파일이 원본으로 돌아가므로 패처를 다시 실행하세요.

[명령줄]
  WO3U_Steam_KR_Patch.exe --verify-only
  WO3U_Steam_KR_Patch.exe --folder "D:\\SteamLibrary\\steamapps\\common\\WARRIORS OROCHI 3 Ultimate" --yes
  WO3U_Steam_KR_Patch.exe --restore --backup "D:\\...\\WO3U_KR.wo3u-backup"

패치 후 파일 SHA-256
{target_lines}

원본(중국어 간체) 파일 SHA-256
{source_lines}
"""


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def run(*args):
    subprocess.run([str(a) for a in args], check=True)


def main():
    version = sys.argv[1]
    if "--rebuild" in sys.argv:
        run(sys.executable, HERE / "build_steam_pack.py", version, sys.argv[sys.argv.index("--rebuild") + 1])
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["version"] == version and manifest["reconstruct_ok"], manifest
    assert digest(PACK) == manifest["pack_sha256"], "pack changed after manifest"
    exe = OUT / EXE_NAME
    run(CSC, "/nologo", "/target:winexe", "/optimize+", "/platform:anycpu", "/out:" + str(exe), SOURCE)

    rel = ROOT / "release" / version
    pkg = rel / ("WO3U_Steam_KR_" + version)
    if pkg.exists():
        shutil.rmtree(pkg)
    pkg.mkdir(parents=True)
    shutil.copy2(exe, pkg / EXE_NAME)
    shutil.copy2(PACK, pkg / PACK.name)
    lines = lambda key: "\n".join(f"{f['name']:<17} {f[key]}" for f in manifest["files"])
    text = README.format(version=version, target_lines=lines("target_sha256"), source_lines=lines("source_sha256"))
    (pkg / "README_사용법.txt").write_bytes(b"\xef\xbb\xbf" + text.replace("\n", "\r\n").encode("utf-8"))
    files = sorted((p for p in pkg.rglob("*") if p.is_file()), key=lambda p: p.name)
    (pkg / "SHA256SUMS.txt").write_text("\n".join(f"{digest(p)}  {p.name}" for p in files) + "\n", encoding="utf-8")

    zip_path = rel / (pkg.name + ".zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(pkg.rglob("*")):
            z.write(p, p.relative_to(rel))
    check = rel / "_zip_verify"
    if check.exists():
        shutil.rmtree(check)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(check)
    for p in pkg.rglob("*"):
        if p.is_file() and digest(p) != digest(check / p.relative_to(rel)):
            raise AssertionError("ZIP 재추출 불일치: " + p.name)
    shutil.rmtree(check)
    print(f"zip={zip_path} size={zip_path.stat().st_size:,} sha256={digest(zip_path)}")


if __name__ == "__main__":
    main()
