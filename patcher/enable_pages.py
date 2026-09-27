"""Enable GitHub Pages (branch main, /docs) for the repo and print its status. Token from .env via publish_release."""
import sys, time, urllib.error
from publish_release import api, REPO

repo = sys.argv[1] if len(sys.argv) > 1 else REPO
base = f"https://api.github.com/repos/{repo}/pages"
try:
    info = api("GET", base)
    print("pages already enabled:", info["html_url"], info.get("source"))
except urllib.error.HTTPError as e:
    if e.code != 404:
        raise
    info = api("POST", base, {"source": {"branch": "main", "path": "/docs"}})
    print("pages enabled:", info["html_url"], info.get("source"))
for _ in range(30):
    b = api("GET", base + "/builds/latest") if True else None
    print("build:", b.get("status"), b.get("error", {}).get("message"))
    if b.get("status") in ("built", "errored"):
        break
    time.sleep(10)
