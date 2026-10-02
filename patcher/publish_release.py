"""Publish the release: find the draft (or create one) for <tag>, attach the ZIP, set the body, publish.

usage: publish_release.py <tag> <zip> <notes.md> [--repo owner/name]
Reads GITHUB_TOKEN from the workspace .env (never printed). Existing asset with the same name is kept
if its size matches (published assets are immutable).
"""
import json, sys, urllib.parse, urllib.request
from pathlib import Path

ENV = Path(__file__).resolve().parents[2] / ".env"
REPO = "kimjh-eclipse/musou-orochi-2-ultimate-steam-kor"


def token():
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("GITHUB_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("GITHUB_TOKEN not found in .env")


TOKEN = token()


def api(method, url, data=None, ctype="application/json", raw=None):
    body = raw if raw is not None else (json.dumps(data).encode() if data is not None else None)
    req = urllib.request.Request(url, data=body, method=method, headers={
        "Authorization": "Bearer " + TOKEN, "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "Content-Type": ctype, "User-Agent": "wo3u-steam-release"})
    with urllib.request.urlopen(req, timeout=3600) as r:
        t = r.read()
        return json.loads(t) if t else None


def main():
    tag, zip_path, notes = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]).read_text(encoding="utf-8")
    repo = sys.argv[sys.argv.index("--repo") + 1] if "--repo" in sys.argv else REPO
    base = f"https://api.github.com/repos/{repo}"
    rels = api("GET", base + "/releases?per_page=30")
    rel = next((r for r in rels if r["tag_name"] == tag or (r["draft"] and r["name"] == tag)), None)
    fields = {"tag_name": tag, "target_commitish": "main", "name": tag, "body": notes, "prerelease": False}
    if rel is None:
        rel = api("POST", base + "/releases", dict(fields, draft=True))
        print("created draft", rel["id"])
    else:
        if not rel["draft"]:
            sys.exit(f"{tag} is already published ({rel['html_url']}); published releases are immutable - use a new tag")
        rel = api("PATCH", base + f"/releases/{rel['id']}", dict(fields, draft=rel["draft"]))
        print("updated draft", rel["id"])
    size = zip_path.stat().st_size
    have = {a["name"]: a for a in rel.get("assets", [])}
    if zip_path.name in have and have[zip_path.name]["size"] == size and have[zip_path.name]["state"] == "uploaded":
        print("asset already uploaded")
    else:
        if zip_path.name in have:
            api("DELETE", base + f"/releases/assets/{have[zip_path.name]['id']}")
        up = rel["upload_url"].split("{")[0] + "?" + urllib.parse.urlencode({"name": zip_path.name})
        print(f"uploading {zip_path.name} ({size:,} bytes)...", flush=True)
        a = api("POST", up, raw=zip_path.read_bytes(), ctype="application/zip")
        print("uploaded", a["name"], a["size"], a["state"])
        if a["size"] != size:
            sys.exit("uploaded size mismatch")
    if rel["draft"]:
        rel = api("PATCH", base + f"/releases/{rel['id']}", {"draft": False, "make_latest": "true"})
    print("published:", rel["html_url"], "| draft", rel["draft"], "| prerelease", rel["prerelease"])
    for a in rel.get("assets", []):
        print("  asset", a["name"], a["size"], a["browser_download_url"])


if __name__ == "__main__":
    main()
