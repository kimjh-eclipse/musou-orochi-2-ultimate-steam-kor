# musou-orochi-2-ultimate-steam-kor

스팀판 무쌍 오로치2 얼티밋 유저 한글화

Steam판 **WARRIORS OROCHI 3 Ultimate Definitive Edition**(무쌍 오로치 2 얼티메이트, App 1879330)용 비공식 한국어 패치의 소스입니다. 게임 파일·추출 데이터·게임 원문 텍스트는 이 저장소에 포함하지 않습니다.

## 최신 배포

**v20260928 — 2026-09-28**

[패치 ZIP 다운로드](https://github.com/kimjh-eclipse/musou-orochi-2-ultimate-steam-kor/releases/download/v20260928/WO3U_Steam_KR_v20260928.zip) · [릴리즈 설명](https://github.com/kimjh-eclipse/musou-orochi-2-ultimate-steam-kor/releases/tag/v20260928) · [문서 사이트](https://kimjh-eclipse.github.io/musou-orochi-2-ultimate-steam-kor/)

1. Steam 게임 속성 → 언어를 **简体中文(중국어 간체)** 로 바꾸고 게임을 종료합니다.
2. ZIP을 풀고 `WO3U_Steam_KR_Patch.exe`를 실행합니다(`WO3U_Steam_KR.pack`과 같은 폴더). 데이터 두 파일을 교체하고 `dinput8.dll`을 추가합니다.
3. 자동으로 채워진 설치 폴더를 확인하고 [상태 검사] → [한국어 패치 적용]을 누릅니다.

[자세한 설치·갱신·복구](docs/install.md) · [알려진 문제](docs/known-issues.md) · [해시](docs/hashes.md)

## 방식

- 게임의 **중국어 간체 슬롯**(`LINKIDX_CHS.BIN` / `LINKFILE_CHS.BIN`)을 한국어로 교체합니다. 게임 언어를 简体中文으로 두고 플레이합니다.
- 텍스트는 일본어 항목을 틀로 삼아 한국어를 만들고, 한글을 중문 폰트의 한자 칸(GBK 코드)에 배치해 인코딩합니다. 중문 글리프는 한글로 다시 그립니다.
- 번역은 PS3판 한국어 패치([musou-orochi-2-ultimate-kor](https://github.com/kimjh-eclipse/musou-orochi-2-ultimate-kor))의 번역을 대응시키고, PC판에만 있는 항목은 새로 번역했습니다.
- 메뉴·타이틀·이름 등 글자가 들어간 이미지(G1T 텍스처)는 원본 모양과 색을 따라 한국어로 다시 그립니다.

## 구성

| 경로 | 내용 |
|---|---|
| `tools/pc_idx.py` `pack_lang.py` | LINKIDX/LINKFILE 읽기, 압축(zlib 블록), 언어 파트 재기록 |
| `tools/kt_text.py` `kt_rebuild.py` | LX/LIST/CONT 텍스트 컨테이너 파싱과 재구성 |
| `tools/ko_charset.py` `ko_encode.py` `build_font.py` `bc3.py` | 한글 ↔ 중문 코드 대응, 폰트 아틀라스(BC3 4096×8192) 생성 |
| `tools/match_tm.py` `ps3_tm.py` `build_text.py` | PS3 번역 대응, 텍스트 빌드 |
| `tools/dump_queue.py` `merge_translations.py` `gen_ko_B_*.py` | 미번역 항목 추출, 번역 병합·검증(제어코드·서식·글리프) |
| `tools/fit40_queue.py` `fit40_check.py` `fit40_audit.py` | 전투 대사 40글자 한도 초과 검출, 다듬은 번역 검사·병합 |
| `tools/g1t_pc.py` `image_labels.py` `image_overpaint.py` `image_logo.py` `build_images.py` | G1T 디코드/인코드, 라벨·자막·로고 교체 |
| `tools/spec_*.py` | 이미지별 교체 스펙 생성기 |
| `mapping/images/*.json` | 이미지 교체 스펙(텍스처·영역·한국어) |
| `mapping/ko_charset.json` | 한글 음절 ↔ 중문 코드 대응표 |
| `tools/build_release.py` `verify_build.py` `install.py` | 빌드, 재읽기 검증, 개발용 설치/복구 |
| `patcher/` | 배포용 패처(C#)와 패치 팩·패키지 빌드 스크립트 |

## 패처

`patcher/WO3USteamPatch.cs`는 PS3판 패처와 같은 화면 구성(설치 경로 → 백업 경로 → 주의사항 동의 → 상태 검사/패치/복구)을 따릅니다.

- Steam 설치 폴더를 레지스트리와 `libraryfolders.vdf`에서 자동으로 찾고, 직접 지정할 수도 있습니다.
- 완성본 `LINKFILE_CHS.BIN`은 원본과 배치가 달라 제자리 구간 기록 대신 **재구성**합니다. 완성본 인덱스 순서대로, 팩에 든 항목은 팩에서, 나머지는 사용자의 원본 파일에서 복사합니다.
- 쓰기 전 원본에서 교체되는 항목만 복구 백업(`.wo3u-backup`)에 저장합니다. 새 파일은 임시 파일로 만든 뒤 SHA-256이 일치할 때만 교체합니다.
- 복구와 이전 버전 갱신도 같은 재구성으로 처리하고 해시로 검증합니다.

```text
WO3U_Steam_KR_Patch.exe                         (GUI)
WO3U_Steam_KR_Patch.exe --verify-only
WO3U_Steam_KR_Patch.exe --folder "<설치 폴더>" --yes
WO3U_Steam_KR_Patch.exe --restore --backup "<백업 파일>"
```

## 빌드

필요: Windows, Python 3.13(numpy, Pillow), .NET Framework 4.x `csc.exe`, Noto Sans/Serif KR 글꼴.

1. 게임을 중국어 간체로 받은 뒤 `tools/inventory.py`로 원본을 기록합니다. 원본 CHS 파일은 `backup/original/`에 둡니다.
2. PS3판 작업 폴더(`../work_wo3u`)의 번역 자료로 `tools/ps3_tm.py`, `tools/match_tm.py`를 실행합니다.
3. `py -3.13 tools/build_release.py <버전>` → `py -3.13 tools/verify_build.py <버전>`
4. `py -3.13 patcher/build_package.py <버전> --rebuild build/<버전>` 으로 팩·EXE·ZIP을 만듭니다.

게임 원문을 담은 번역 자료(`translation_memory/`)와 대응표(`mapping/pc_match.jsonl`)는 저장소에 넣지 않으므로, 텍스트 빌드는 작업 폴더에 이 자료가 있어야 합니다.

`build_steam_pack.py`는 팩을 만든 뒤 원본과 팩만으로 완성본을 다시 만들어 해시를 대조합니다.

## 라이선스

소스 코드는 Apache License 2.0을 따릅니다. 게임 데이터의 권리는 KOEI TECMO GAMES에 있습니다.
