# 설치·갱신·복구

대상은 Steam판 **WARRIORS OROCHI 3 Ultimate Definitive Edition**(App `1879330`), 기준 버전은 **v20261010**입니다. Windows와 .NET Framework 4.x가 필요합니다.

## 1. 준비와 다운로드

1. Steam 라이브러리에서 게임을 우클릭 → **속성 → 언어**를 **简体中文(중국어 간체)** 로 바꿉니다. 다운로드가 끝날 때까지 기다립니다.
2. 게임을 완전히 종료합니다.
3. [WO3U_Steam_KR_v20261010.zip](https://github.com/kimjh-eclipse/musou-orochi-2-ultimate-steam-kor/releases/download/v20261010/WO3U_Steam_KR_v20261010.zip)을 내려받아 압축을 풉니다.

ZIP에는 `WO3U_Steam_KR_Patch.exe`, `WO3U_Steam_KR.pack`, `README_사용법.txt`, `SHA256SUMS.txt`가 들어 있습니다. 패치 데이터가 커서 EXE와 `.pack`을 나눠 두었으므로 **두 파일을 같은 폴더에 두고 실행**합니다.

```powershell
Get-FileHash .\WO3U_Steam_KR_v20261010.zip -Algorithm SHA256
```

예상 값은 [전체 해시 목록](hashes.md)을 참고하세요.

## 2. 적용 대상

패처는 설치 폴더의 데이터 두 파일을 교체하고 `dinput8.dll`을 추가합니다.

```text
...\steamapps\common\WARRIORS OROCHI 3 Ultimate\
  WO3U.exe
  LINKIDX_CHS.BIN     ← 교체
  LINKFILE_CHS.BIN    ← 교체
  dinput8.dll         ← 추가 (실행 파일 속 문장을 실행 중에 한국어로 바꿈)
  (다른 언어·공통 데이터는 그대로)
```

설치 폴더는 Steam 라이브러리에서 게임 우클릭 → **관리 → 로컬 파일 보기**로 열리는 폴더입니다. 패처는 Steam 설정(레지스트리, `libraryfolders.vdf`, `appmanifest_1879330.acf`)에서 이 폴더를 자동으로 찾습니다.

## 3. 처음 적용

1. `WO3U_Steam_KR_Patch.exe`를 실행합니다. **A. Steam 게임 설치 폴더**가 자동으로 채워집니다. 비어 있으면 [자동 찾기] 또는 [찾아보기...]를 사용합니다.
2. **B. 복구 백업 파일** 경로를 확인합니다. 기본값은 설치 폴더 안의 `WO3U_KR.wo3u-backup`입니다.
3. [상태 검사]로 원본 상태인지 확인합니다.
4. 주의사항에 동의하고 [한국어 패치 적용]을 누릅니다.
5. 로그 마지막의 **한국어 패치 적용 및 최종 해시 검증 2/2 완료**를 확인합니다.

Program Files 아래(Steam 기본 위치)에 설치했다면 쓰기 권한이 없어 **관리자 권한으로 다시 실행할지** 묻습니다. 작업 중 약 1.1GB의 여유 공간이 필요합니다.

설치 폴더에 다른 프로그램의 `dinput8.dll`(예: 60프레임 이상 주사율 그래픽 수정 패치)이 이미 있으면 처리 방법을 묻습니다.

- **이어서 쓰기(기본)**: 기존 파일을 `dinput8_wo3u_chain.dll`로 옮기고, 한국어 패치의 `dinput8.dll`이 그 파일을 이어서 불러옵니다. 두 기능을 함께 씁니다.
- **덮어쓰기**: 기존 파일을 `dinput8.dll.wo3u-orig`로 보관합니다. 그 프로그램의 기능은 꺼집니다.
- **건너뛰기**: 한국어 데이터만 적용합니다. 실행 파일 속 문장 27개(언리미티드 모드 알림·전생 설명 등)는 깨져 보입니다.

[원본 복구] 때 보관한 파일을 되돌립니다. 명령줄 `--yes`는 이어서 쓰기를 고르며, `--overwrite-dll` / `--skip-dll`로 바꿀 수 있습니다.

한국어 패치를 먼저 설치한 뒤 다른 프로그램을 넣으면 그 프로그램이 `dinput8.dll`을 덮어씁니다. 이때는 패처를 다시 실행해 이어서 쓰기를 고르세요. 이미 같은 버전이 적용되어 있으면 다시 쓰지 않습니다. 세이브·영상·음성·다른 언어 파일은 패처의 수정 대상이 아닙니다.

## 4. 이전 버전에서 갱신

새 패처에 **이전 패치 때 만든 `.wo3u-backup`** 을 지정하고 [한국어 패치 적용]을 누릅니다. 패처가 이전 버전을 감지하면 백업으로 원본을 재구성하고, 원본 해시를 확인한 뒤 새 버전을 적용합니다. 백업은 새 버전 기준으로 갱신됩니다.

## 5. Steam 무결성 검사·게임 업데이트

Steam의 **게임 파일 무결성 검사**나 게임 업데이트는 데이터 파일을 원본으로 되돌립니다. 그 뒤에는 패처를 다시 실행하면 됩니다. 게임 업데이트로 원본 자체가 바뀌면 패처가 "알 수 없는 상태"로 안내하고 중단합니다. 이때는 새 버전 패치를 기다려 주세요.

## 6. 명령줄 사용

아래 경로는 예시입니다. `--yes`는 확인을 생략하고, `--no-pause`는 종료 때 Enter를 기다리지 않습니다. 설치 폴더를 생략하면 자동으로 찾습니다.

```powershell
.\WO3U_Steam_KR_Patch.exe --verify-only
.\WO3U_Steam_KR_Patch.exe --folder "D:\SteamLibrary\steamapps\common\WARRIORS OROCHI 3 Ultimate" --yes
.\WO3U_Steam_KR_Patch.exe --restore --backup "D:\SteamLibrary\steamapps\common\WARRIORS OROCHI 3 Ultimate\WO3U_KR.wo3u-backup"
```

## 7. 복구

패처의 [원본 복구] 또는 `--restore`에 백업을 지정합니다. 백업으로 원본 파일을 재구성하고 원본 해시가 맞을 때만 교체하며, `dinput8.dll`도 지웁니다. 복구 후에도 백업은 남습니다.

백업이 없어도 Steam **게임 파일 무결성 검사**로 원본을 다시 받을 수 있습니다.

## 오류 제보

[Issues](https://github.com/kimjh-eclipse/musou-orochi-2-ultimate-steam-kor/issues)에 릴리즈 버전, 상태 검사 로그, 화면 진입 경로와 캡처를 남겨 주세요. 개인 경로·계정 정보는 가리고, 게임 파일이나 세이브는 첨부하지 마세요.
