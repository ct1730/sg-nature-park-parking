#!/usr/bin/env python
"""Monthly refresh of the SG Nature Park Parking site (official data only).

Pipeline
  1. re-download the three data.gov.sg datasets (NParks parks, NParks car park lots, HDB carparks)
  2. re-scrape the NParks sitemap + all park-detail pages (official parking/hours/coords)
  3. re-parse -> rebuild site/data/parks.json -> regenerate site/data/data.js
  4. commit + push to GitHub Pages if anything changed, and print a short report

Runs under any Python 3: it re-execs itself with the project venv (which has pyproj + shapely).
Exit code non-zero on a real failure so the Hermes scheduler raises an alert.
"""
import datetime, hashlib, json, os, re, subprocess, sys, time

PROJECT = r"C:\Hermes_Workspace\sg-park-drive"
VENV_PY = os.path.join(PROJECT, ".venv", "Scripts", "python.exe")
SITE = os.path.join(PROJECT, "site")
DATA = os.path.join(PROJECT, "data")
SITE_URL = "https://ct1730.github.io/sg-nature-park-parking/"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

DS = {
    "parks": "d_77d7ec97be83d44f61b85454f844382f",
    "carpark_lots": "d_d5594e4c43e838380155f05f53f58567",
    "hdb": "d_23f946fa557947f93a8043bbef41dd09",
}

# ---------------------------------------------------------------- re-exec in the project venv
def ensure_deps():
    try:
        import pyproj, shapely, requests  # noqa: F401
        return
    except ImportError:
        pass
    if not os.path.exists(VENV_PY):
        print("ERROR: project venv missing at " + VENV_PY)
        sys.exit(3)
    sys.exit(subprocess.run([VENV_PY, os.path.abspath(__file__)] + sys.argv[1:]).returncode)

ensure_deps()
import requests  # noqa: E402
from concurrent.futures import ThreadPoolExecutor  # noqa: E402


def log(*a):
    # progress goes to stderr: for a no_agent cron only stdout is delivered to the user
    print(*a, file=sys.stderr, flush=True)


def get(url, tries=5, timeout=90, **kw):
    for i in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=timeout, **kw)
            if r.status_code in (200, 201):
                return r
            log(f"  [warn] {r.status_code} {url[:90]} (try {i+1})")
        except Exception as e:
            log(f"  [warn] {type(e).__name__} {url[:90]} (try {i+1})")
        time.sleep(8 + 6 * i)
    return None


def download_datasets():
    ok = True
    for key, did in DS.items():
        if key == "hdb":
            r = get(f"https://data.gov.sg/api/action/datastore_search?resource_id={did}&limit=5000")
            if not r:
                ok = False; log("  [FAIL] HDB carpark download"); continue
            recs = r.json()["result"]["records"]
            json.dump({"result": {"records": recs}}, open(os.path.join(DATA, "hdb_carpark_raw.json"), "w", encoding="utf-8"))
            log(f"  [ok] HDB Carpark Information: {len(recs)} car parks")
        else:
            r = get(f"https://api-open.data.gov.sg/v1/public/api/datasets/{did}/poll-download")
            if not r or r.json().get("code") != 0:
                ok = False; log(f"  [FAIL] poll-download {key}"); continue
            s3 = r.json()["data"]["url"]
            r2 = get(s3, timeout=300)
            if not r2 or len(r2.content) < 1000:
                ok = False; log(f"  [FAIL] download {key}"); continue
            dest = os.path.join(DATA, "nparks_parks.geojson" if key == "parks" else "nparks_carpark_lots.geojson")
            open(dest, "wb").write(r2.content)
            log(f"  [ok] {key}: {len(r2.content)//1024} KB")
    return ok


def refresh_park_pages():
    r = get("https://www.nparks.gov.sg/sitemap/sitemap.xml")
    if not r:
        log("  [FAIL] nparks sitemap"); return False
    open(os.path.join(DATA, "np_sitemap.xml"), "w", encoding="utf-8").write(r.text)
    urls = sorted({u for u in re.findall(r"<loc>([^<]+)</loc>", r.text) if "park-detail" in u})
    out = os.path.join(DATA, "pd")
    os.makedirs(out, exist_ok=True)
    known = {f[:-5] for f in os.listdir(out) if f.endswith(".html")}

    def fetch(u):
        slug = u.rstrip("/").split("/")[-1]
        rr = get(u, tries=3, timeout=60)
        if rr and len(rr.text) > 20000 and "<title>Page not found" not in rr.text:
            open(os.path.join(out, slug + ".html"), "w", encoding="utf-8").write(rr.text)
            return slug, True
        return slug, False

    with ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(fetch, urls))
    good = [s for s, k in res if k]
    new = sorted(set(good) - known)
    log(f"  [ok] NParks park pages: {len(good)}/{len(urls)} fetched"
        + (f" | NEW pages: {', '.join(new)}" if new else ""))
    return len(good) > 300


def run(script):
    r = subprocess.run([VENV_PY, os.path.join(PROJECT, script)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1800, cwd=PROJECT)
    if r.returncode:
        log(f"  [FAIL] {script}\n{(r.stderr or '')[-1200:]}")
    return r.returncode == 0, (r.stdout or "")


def snapshot():
    p = os.path.join(SITE, "data", "parks.json")
    if not os.path.exists(p):
        return {}
    d = json.load(open(p, encoding="utf-8"))
    return {x["name"]: (x.get("published_car_lots_total"), x.get("hours"), x.get("parking_text")) for x in d["parks"]}


def git(*args, check=False):
    return subprocess.run(["git", "-C", SITE] + list(args), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def main():
    log("SG Nature Park Parking — monthly official-data refresh")
    before = snapshot()
    log("1/4 downloading data.gov.sg datasets")
    if not download_datasets():
        log("ERROR: dataset download failed"); sys.exit(2)
    log("2/4 re-scraping NParks park pages")
    if not refresh_park_pages():
        log("ERROR: NParks scrape failed"); sys.exit(2)
    log("3/4 rebuilding dataset")
    for s in ("parse_parks.py", "build_site_data.py"):
        ok, out = run(s)
        if not ok:
            log("ERROR: rebuild failed"); sys.exit(2)
    ok, out = run(os.path.join("site", "make_data_js.py"))
    if not ok:
        log("ERROR: data.js generation failed"); sys.exit(2)
    after = snapshot()

    # ---- what changed?
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = []
    for n in sorted(set(before) & set(after)):
        o, w = before[n], after[n]
        if o[0] != w[0] or o[2] != w[2]:
            changed.append(f"{n} {o[0] if o[0] is not None else '–'}→{w[0] if w[0] is not None else '–'} lots")
    tot = sum(v[0] or 0 for v in after.values())

    log("4/4 publishing")
    stamp = datetime.date.today().strftime("%d %b %Y")
    if git("status", "--porcelain").stdout.strip() == "":
        # silent run: no stdout means the no_agent cron delivers nothing
        log("  nothing to publish (no file changes)")
        log(f"RESULT {len(after)} parks · {tot} lots · unchanged — staying silent")
        return
    git("add", "-A")
    git("-c", "user.name=KrisP774", "-c", "user.email=krisdipong.petpiroon@gmail.com",
        "commit", "-m", f"Monthly official-data refresh — {stamp}")
    push = git("push", "origin", "main")
    if push.returncode:
        log("ERROR: git push failed:\n" + (push.stderr or "")[-800:])
        sys.exit(2)

    lines = [f"🅿️ SG Nature Park Parking data refreshed — {stamp}",
             f"{len(after)} parks · {tot} published car lots · live: {SITE_URL}"]
    if added:
        lines.append("New parks: " + "; ".join(added[:6]) + ("…" if len(added) > 6 else ""))
    if removed:
        lines.append("No longer listed: " + "; ".join(removed[:6]))
    if changed:
        lines.append("Changes: " + "; ".join(changed[:8]) + ("…" if len(changed) > 8 else ""))
    if not (added or removed or changed):
        lines.append("No changes to park or parking figures vs last run.")
    lines.append("Pushed to GitHub Pages — live in ~1 min.")
    log("RESULT " + f"{len(after)} parks · {tot} lots · +{len(added)}/-{len(removed)} parks · {len(changed)} changed")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
