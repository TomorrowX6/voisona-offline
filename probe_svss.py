#!/usr/bin/env python3
# 用 CDN HEAD 探测 VoiSona SONG(_svss) 声库 ID，切片扫描（供 GitHub Actions 并行调用）。
# 用法: python probe_svss.py <prefix> <start> <end>
#   prefix = f/m/t, start/end = 编号范围（含），例如 f 600 649 扫 techno-sp_ja_JP_f600..f649_svss
import sys, json, urllib.request, urllib.error, concurrent.futures

CDN = "https://cdn.voisona.com/voice"

# 已发售的 ja_JP song 声库 ID（用于标记"新发现/未发售候选"）
KNOWN_JA_SVSS = {
    'f605','f801','f802','f803','f808','f811','f815','f824','f830','f831',
    'f833','f834','f841','f846','f847','f849','f850','f854','f857','f859',
    'f868','f972','f973','f974','f975','m804','m805','m867','m868','t014'
}

VERSIONS = ["1.0.0","2.0.0","2.0.1","2.1.0","2.2.0"]

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

def probe_versions(vid):
    found = []
    for ver in VERSIONS:
        if head(f"{CDN}/{vid}/{ver}/{vid}.tsnvoice") == 200:
            found.append(ver)
    found.sort(key=lambda x: tuple(int(p) for p in x.split(".")))
    return (vid, found)

def main():
    prefix = sys.argv[1]
    start = int(sys.argv[2]); end = int(sys.argv[3])
    ids = [f"techno-sp_ja_JP_{prefix}{code:03d}_svss" for code in range(start, end + 1)]
    slabel = f"{prefix}{start:03d}-{prefix}{end:03d}"
    print(f"[*] slice {slabel} ({len(ids)} ids) probing ...", flush=True)

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=60) as ex:
        for vid, vers in ex.map(probe_versions, ids):
            if vers:
                results[vid] = vers

    report = []
    for vid in sorted(results):
        code = vid.replace("techno-sp_ja_JP_","").replace("_svss","")
        tag = "NEW <-- 未发售候选" if code not in KNOWN_JA_SVSS else "known"
        line = f"  {vid}  versions={','.join(results[vid])}  [{tag}]"
        print(line, flush=True)
        report.append(line)

    outname = f"probe_result_{slabel.replace('-', '_')}.json"
    with open(outname, "w", encoding="utf-8") as f:
        json.dump({"slice": slabel, "results": results}, f, ensure_ascii=False, indent=2)

    if not report:
        print("  (no hits in this slice)", flush=True)

if __name__ == "__main__":
    main()
