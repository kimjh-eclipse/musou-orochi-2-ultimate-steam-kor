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

설치 폴더의 LINKIDX_CHS.BIN / LINKFILE_CHS.BIN 을 교체하고 dinput8.dll 을 추가합니다.
dinput8.dll 은 게임 실행 파일 안에 있는 문장(언리미티드 모드 알림, 전생 도움말 등)을
실행 중에만 한국어로 바꿉니다. WO3U.exe 파일 자체는 수정하지 않습니다.
이미 다른 프로그램(60프레임 수정 패치 등)의 dinput8.dll 이 있으면 처리 방법을 묻습니다.
이어서 쓰기(기본): 기존 파일을 dinput8_wo3u_chain.dll 로 옮기고 한국어 패치 DLL이 이어서 불러옵니다. 두 기능을 함께 씁니다.
덮어쓰기: 기존 파일을 dinput8.dll.wo3u-orig 로 보관합니다(그 기능은 꺼짐). 건너뛰기: 한국어 데이터만 적용합니다.
원본 복구 때 보관한 파일을 되돌립니다.
기본 위치(설치 폴더 안)에 WO3U_KR.wo3u-backup 백업이 생깁니다.
이 백업으로 원본 복구와 다음 버전 갱신을 합니다. 삭제하지 마세요.

[선택: 병사 공격성 강화]
패처의 '병사 공격성 강화'를 체크하고 [한국어 패치 적용]을 누르면 일반 병사가 무장처럼 적극적으로 공격합니다.
- 공통 데이터 LINKFILE_000.BIN 의 유닛 표에서 전투 병사 364 슬롯만 바꿉니다(게임 언어와 무관하게 적용).
  근접 병사는 무장 AI로, 원거리 병사(궁병·총병·술사 등)는 원래 행동을 유지하고 AI 단계만 올립니다.
  병기·백성·진지 가게·동물·장수는 바꾸지 않습니다. 난이도가 올라갑니다.
- 체크를 해제하고 [한국어 패치 적용]을 누르거나 [원본 복구]를 하면 원래대로 되돌립니다.
- 다른 유닛 데이터 모드로 수정된 상태면 건너뜁니다. Steam 무결성 검사를 하면 원래대로 돌아갑니다.
- 유닛 표 구조는 PythWare 의 WO3 Unit Editor / Super Aggressive AI, 병사 AI 값 조사는
  디시인사이드 진삼국무쌍8 갤러리 SPlT 님의 글을 참고했습니다.

[선택: 장수 공격성 한 단계 올리기]
패처의 '장수 공격성 한 단계 올리기'를 체크하고 [한국어 패치 적용]을 누르면 이름 있는 장수의 AI 단계를
한 단계 올립니다(일반 장수 3→4, 무쌍 장수 5→6, 여포는 그대로). 병사 옵션과 따로 켜고 끌 수 있습니다.
- 유닛 데이터에 아군·적군 구분이 없어 아군 장수에도 똑같이 적용됩니다.
- 체크를 해제하고 [한국어 패치 적용]을 누르거나 [원본 복구]를 하면 원래대로 되돌립니다.

[복구]
- 패처의 [원본 복구] 또는 Steam '게임 파일 무결성 검사'로 원본에 돌아갈 수 있습니다.
- 원본 복구는 dinput8.dll 도 함께 지우고, 병사·장수 공격성 옵션도 되돌립니다.
- Steam 무결성 검사나 게임 업데이트 뒤에는 데이터 파일이 원본으로 돌아가므로 패처를 다시 실행하세요.

[명령줄]
  WO3U_Steam_KR_Patch.exe --verify-only
  WO3U_Steam_KR_Patch.exe --folder "D:\\SteamLibrary\\steamapps\\common\\WARRIORS OROCHI 3 Ultimate" --yes
  WO3U_Steam_KR_Patch.exe --yes --soldier-ai        (병사 공격성 강화 적용, 해제는 --no-soldier-ai / 장수는 --officer-ai, --no-officer-ai)
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
