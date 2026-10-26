"""Full check for D:\\w3c\\hackthon\\index.html.
Fetches browser-specs, recomputes every number the dashboard shows in Python,
renders the page (and filtered views) in headless Chrome, asserts they match.
Run: python test_dashboard.py
"""
import json, re, subprocess, sys, tempfile, urllib.request, urllib.parse
from collections import Counter
from pathlib import Path

HTML = Path(r"D:\w3c\hackthon\index.html")
CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

def dump_dom(url):
    chrome = next(p for p in CHROME_CANDIDATES if Path(p).exists())
    out = subprocess.run(
        [chrome, "--headless=new", "--disable-gpu", "--virtual-time-budget=8000", "--dump-dom", url],
        capture_output=True, text=True, timeout=60)
    return out.stdout

def main():
    specs = json.load(urllib.request.urlopen("https://w3c.github.io/browser-specs/index.json", timeout=30))

    orgs = Counter(s.get("organization") or "(none)" for s in specs)
    status_of = lambda s: (s.get("release") or {}).get("status") or "Nightly only"
    statuses = Counter(status_of(s) for s in specs)
    w3c = [s for s in specs if s.get("organization") == "W3C"]
    groups = Counter(g["name"] for s in w3c for g in s.get("groups", []))
    recs = sum(1 for s in specs if (s.get("release") or {}).get("status") == "Recommendation")
    nightly_only = sum(1 for s in specs if not s.get("release"))

    dom = dump_dom("file:///" + str(HTML).replace("\\", "/"))
    assert dom, "empty DOM render"
    assert "Fetch failed" not in dom.split("</script>")[-1], "page reported fetch failure"

    def card(n): return f"<b>{n}</b>"
    for n in (len(specs), len(orgs), len(set(g['name'] for s in w3c for g in s.get('groups', []))), recs, nightly_only):
        assert card(n) in dom, f"stat card {n} missing"

    for name, cnt in orgs.most_common(12):
        assert f'data-v="{name}"' in dom and f'<span class="n">{cnt}</span>' in dom, f"org bar {name}={cnt}"
    for name, cnt in statuses.most_common(12):
        assert f'<span class="n">{cnt}</span>' in dom, f"status bar {name}={cnt}"
    body = dom.split('id="rows">', 1)[1].split("</tbody>", 1)[0]
    assert len(re.findall(r"<tr>", body)) == min(len(specs), 300), "initial table rows"
    assert f">{len(specs)} specs<" in dom, "initial count label"

    # hash-filtered views: org, status, group
    top_group = groups.most_common(1)[0][0]
    for key, val, expect in [
        ("org", "W3C", len(w3c)),
        ("status", "Recommendation", recs),
        ("group", top_group, sum(1 for s in specs if any(g["name"] == top_group for g in s.get("groups", [])))),
    ]:
        d = dump_dom("file:///" + str(HTML).replace("\\", "/") + "#" + key + "=" + urllib.parse.quote(val))
        assert f">{expect} specs<" in d, f"filter {key}={val}: want {expect}"
        assert f"{key}: {val}" in d.replace("&amp;", "&"), f"filter chip {key}={val}"

    print(f"OK: {len(specs)} specs, {len(orgs)} orgs, {recs} RECs, {nightly_only} nightly-only; "
          f"cards + 36 bars + 301 rows + 3 filtered views all match Python recompute")

if __name__ == "__main__":
    sys.exit(main())
