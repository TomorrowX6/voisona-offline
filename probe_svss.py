#!/usr/bin/env python3
# 用 CDN HEAD 探测 VoiSona SONG(_svss) 声库 ID，切片扫描（供 GitHub Actions 并行调用）。
# 用法: python probe_svss.py <start> <end>
#   start/end = f 编号范围（含），例如 600 649 扫 techno-sp_ja_JP_f600..f649_svss
import sys, json, urllib.request, urllib.error, concurrent.futures

CDN = "https://cdn.voisona.com/voice"

# 已发售的 ja_JP song 声库 ID（用于标记"新发现/未发售候选"）
KNOWN_JA_SVSS = {
    'f605','f801','f802','f803','f808','f811','f815','f824','f830','f831',
    'f833','f834','f841','f846','f847','f849','f850','f854','f857','f859',
    'f868','f972','f973','f974','f975','m804','m805','m867','m868','t014'
}

QUICK_VERSIONS = ["1.0.0","2.0.0","2.0.1","2.1.0","2.2.0","3.0.0"]
FULL_VERSIONS = ["1.0.0","1.0.1","1.0.2","1.0.3","1.1.0","1.1.1","1.1.2","1.1.3",
    "1.2.0","1.2.1","1.2.2","1.2.3","1.3.0","1.3.1","1.3.2","1.3.3",
    "1.4.0","1.4.1","1.4.2","1.4.3","1.5.0","1.5.1","1.5.2","1.5.3",
    "1.6.0","1.6.1","1.6.2","1.6.3","1.7.0","1.7.1","1.7.2","1.7.3",
    "1.8.0","1.8.1","1.8.2","1.8.3","1.9.0","1.9.1","1.9.2","1.9.3",
    "2.0.0","2.0.1","2.0.2","2.0.3","2.1.0","2.1.1","2.1.2","2.1.3",
    "2.2.0","2.2.1","2.2.2","2.2.3","2.3.0","2.3.1","2.3.2","2.3.3",
    "2.4.0","2.4.1","2.4.2","2.4.3","2.5.0","2.5.1","2.5.2","2.5.3",
    "2.6.0","2.6.1","2.6.2","2.6.3","2.7.0","2.7.1","2.7.2","2.7.3",
    "2.8.0","2.8.1","2.8.2","2.8.3","2.9.0","2.9.1","2.9.2","2.9.3",
    "3.0.0","3.0.1","3.0.2","3.0.3","3.1.0","3.1.1","3.1.2","3.1.3",
    "3.2.0","3.2.1","3.2.2","3.2.3","3.3.0","3.3.1","3.3.2","3.3.3",
    "3.4.0","3.4.1","3.4.2","3.4.3","3.5.0","3.5.1","3.5.2","3.5.3",
    "4.0.0","4.0.1","4.0.2","4.0.3"]

def head(url):
    req = urllib.request.Request(url, method="HEAD")
    req.add_header("User-Agent", "Mozilla/5.0")
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None

def check_exist(vid):
    for ver in QUICK_VERSIONS:
        if head(f"{CDN}/{vid}/{ver}/{vid}.tsnvoice") == 200:
            return (vid, True)
    return (vid, False)

def probe_versions(vid):
    found = []
    for ver in FULL_VERSIONS:
        if head(f"{CDN}/{vid}/{ver}/{vid}.tsnvoice") == 200:
            found.append(ver)
    found.sort(key=lambda x: tuple(int(p) for p in x.split(".")))
    return (vid, found)

def main():
    start = int(sys.argv[1]); end = int(sys.argv[2])
    ids = [f"techno-sp_ja_JP_f{code}_svss" for code in range(start, end + 1)]
    print(f"[*] slice f{start}-f{end} ({len(ids)} ids) probing ...", flush=True)

    existing = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=60) as ex:
        for vid, ok in ex.map(check_exist, ids):
            if ok:
                existing.append(vid)
    print(f"[*] existence hits: {len(existing)}", flush=True)

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=60) as ex:
        for vid, vers in ex.map(probe_versions, existing):
            results[vid] = vers

    report = []
    for vid in sorted(results):
        code = vid.replace("techno-sp_ja_JP_","").replace("_svss","")
        tag = "NEW <-- 未发售候选" if code not in KNOWN_JA_SVSS else "known"
        latest = results[vid][-1] if results[vid] else "-"
        line = f"  {vid}  latest={latest}  versions={len(results[vid])}  [{tag}]"
        print(line, flush=True)
        report.append(line)

    with open("probe_result.json", "w", encoding="utf-8") as f:
        json.dump({"slice": [start, end], "results": results}, f, ensure_ascii=False, indent=2)

    if not report:
        print("  (no hits in this slice)", flush=True)

if __name__ == "__main__":
    main()
