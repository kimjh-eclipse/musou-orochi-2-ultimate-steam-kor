"""Release-page body (GitHub) from the long cafe/blog draft, so both carry the same friendly content.

The long draft (release/<ver>/CAFE_POST_<ver>_붙여넣기용.txt) is the reference text: "■ 섹션", "· 항목", numbered steps,
blank line between lines. This turns it into Markdown and appends the patched-file hashes from RELEASE_NOTES.md.
usage: make_release_body.py <ver>   -> release/<ver>/RELEASE_BODY.md
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")


def main():
    ver = sys.argv[1]
    rel = ROOT / "release" / ver
    src = (rel / f"CAFE_POST_{ver}_붙여넣기용.txt").read_text(encoding="utf-8").strip().splitlines()
    out, bullets = [], False
    for line in src:
        t = line.strip()
        if t.startswith("제목:") or t == "이클립스입니다.":
            continue
        if not t:
            if not bullets:
                out.append("")
            continue
        if t.startswith("■ "):
            bullets = False
            out += ["", "## " + t[2:], ""]
            continue
        if t.startswith("· "):
            bullets = True
            out.append("- " + t[2:])
            continue
        if re.match(r"\d+\. ", t):
            bullets = True
            out.append(t)
            continue
        if bullets:
            out.append("")
        bullets = False
        if re.match(r"https?://\S+$", t):
            out.append(f"<{t}>")
        else:
            out.append(t)
    body = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip() + "\n"
    notes = (rel / "RELEASE_NOTES.md").read_text(encoding="utf-8")
    k = notes.find("패치 후 파일 SHA-256")
    if k >= 0:
        body += "\n## 파일 해시\n\n" + notes[k:].split("[문서 사이트]")[0].strip() + "\n"
    body += "\n[문서 사이트](https://kimjh-eclipse.github.io/musou-orochi-2-ultimate-steam-kor/)에 설치·복구 안내와 기술 문서가 있습니다.\n"
    (rel / "RELEASE_BODY.md").write_text(body, encoding="utf-8")
    print(body)


if __name__ == "__main__":
    main()
