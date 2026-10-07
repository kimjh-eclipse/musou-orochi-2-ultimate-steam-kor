"""Docs site home (docs/home.md): user-facing block (download link, install summary, cautions, issue reports) taken from
release/<ver>/RELEASE_BODY.md (tools/make_release_body.py), between <!-- release:start --> and <!-- release:end -->.

usage: update_docs_home.py <ver> <repo dir>
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
START, END = "<!-- release:start -->", "<!-- release:end -->"


def section(body, title):
    m = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", body, re.S | re.M)
    return m.group(1).strip() if m else ""


def main():
    ver, repo = sys.argv[1], Path(sys.argv[2])
    body = (ROOT / "release" / ver / "RELEASE_BODY.md").read_text(encoding="utf-8")
    block = "\n\n".join([
        START,
        "## 이번 버전 (" + ver + ")",
        section(body, "바뀐 점"),
        "이전 버전에서 바뀐 것은 [변경 이력](changelog.md)에 있습니다.",
        "## 다운로드",
        section(body, "다운로드"),
        "## 설치·업데이트",
        section(body, "설치·업데이트 방법"),
        "자세한 절차와 복구 방법은 [설치·갱신·복구](install.md)에 있습니다.",
        "## 주의 사항",
        section(body, "주의 사항"),
        "남은 문제는 [알려진 문제](known-issues.md)에 정리했습니다.",
        "## 제보",
        section(body, "제보"),
        END,
    ])
    home = repo / "docs/home.md"
    s = home.read_text(encoding="utf-8")
    if START in s:
        s = s[:s.index(START)] + block + s[s.index(END) + len(END):]
    else:  # first time: replace the old '## 이번 릴리즈' paragraph
        m = re.search(r"^## 이번 릴리즈\n\n.*?\n\n", s, re.S | re.M)
        if not m:
            sys.exit("no '## 이번 릴리즈' section")
        s = s[:m.start()] + block + "\n\n## 이 패치는\n\n" + s[m.end():]
    home.write_text(s, encoding="utf-8")
    print("updated", home)


if __name__ == "__main__":
    main()
