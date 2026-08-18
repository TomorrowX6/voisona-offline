#!/usr/bin/env python3
# VoiSona Talk 全量 TTS 声库发现 + 下载 (CDN 直连, 无需登录)
# URL: https://cdn.voisona.com/voice/{id}/{version}/{id}.tsnvoice
# 用法: python download_talk_voices.py [list] [download]
import sys, os, urllib.request, concurrent.futures

CDN = "https://cdn.voisona.com/voice"
VOICE_ROOT = os.path.join(os.environ["APPDATA"], "Techno-Speech", "VoiSona Talk", "voices", "Talker")

VENDORS = [
    "techno-sp_ja_JP", "techno-sp_en_US", "techno-sp_zh_CN", "techno-sp_zh_TW",
    "s-s-s-llc_ja_JP", "nitech-jp_ja_JP", "nitech-jp_en_US",
]
TTS_VERSIONS = [
    "1.0.0","1.0.1","1.0.2","1.0.3","1.1.0","1.1.1","1.1.2","1.1.3",
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
    "4.0.0","4.0.1","4.0.2","4.0.3",
]

def gen_ids():
    ids = []
    for ven in VENDORS:
        for code in range(600, 1000):
            for pfx in ("f", "m", "t"):
                ids.append(f"{ven}_{pfx}{code}_tts")
    return ids

def head(url):
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=6) as r:
            return r.status, r.headers.get("Content-Length")
    except Exception:
        return None, None

def probe_exists(vid):
    # 用几个常见版本快速判断是否存在 (403=不存在, 200=存在)
    for ver in ("2.0.1", "2.0.0", "2.1.0", "1.0.0"):
        st, _ = head(f"{CDN}/{vid}/{ver}/{vid}.tsnvoice")
        if st == 200:
            return vid
    return None

def probe_versions(vid):
    found = []
    for ver in TTS_VERSIONS:
        st, ln = head(f"{CDN}/{vid}/{ver}/{vid}.tsnvoice")
        if st == 200:
            found.append((ver, int(ln) if ln else 0))
    return found

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "list"
    ids = gen_ids()
    print(f"[*] 探测 {len(ids)} 个候选 TTS ID ...", flush=True)

    existing = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as ex:
        for vid in ex.map(probe_exists, ids):
            if vid:
                existing.append(vid)
    print(f"[*] 发现 {len(existing)} 个 TTS 声库", flush=True)

    # 对每个已发现的 ID, 探测全部版本
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as ex:
        for vid, vers in zip(existing, ex.map(probe_versions, existing)):
            if vers:
                vers.sort(key=lambda x: tuple(int(p) for p in x[0].split(".")))
                results.append((vid, vers))

    total = 0
    for vid, vers in sorted(results):
        latest = vers[-1]
        sz = latest[1]
        total += sz
        print(f"  {vid}  最新 v{latest[0]}  ({sz/1e6:.1f} MB)  共 {len(vers)} 版本", flush=True)

    print(f"\n[*] 合计 {len(results)} 个声库, 最新版总大小 {total/1e9:.2f} GB", flush=True)

    if mode == "download":
        for vid, vers in sorted(results):
            latest = vers[-1]
            ver, sz = latest
            url = f"{CDN}/{vid}/{ver}/{vid}.tsnvoice"
            d = os.path.join(VOICE_ROOT, vid, ver)
            out = os.path.join(d, f"{vid}.tsnvoice")
            if os.path.exists(out) and os.path.getsize(out) == sz:
                print(f"  [跳过] {vid} v{ver}", flush=True)
                continue
            os.makedirs(d, exist_ok=True)
            print(f"  [下载] {vid} v{ver} -> {out}", flush=True)
            try:
                urllib.request.urlretrieve(url, out)
                print(f"  [完成] {vid}", flush=True)
            except Exception as e:
                print(f"  [失败] {vid}: {e}", flush=True)
                if os.path.exists(out):
                    os.remove(out)

if __name__ == "__main__":
    main()
