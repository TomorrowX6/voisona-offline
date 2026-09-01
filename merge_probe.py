#!/usr/bin/env python3
# 合并所有切片的 probe_result_*.json 为一个 merged_result.json。
# 用法: python merge_probe.py <目录>
import sys, json, glob, os

KNOWN_JA_SVSS = {
    'f605','f801','f802','f803','f808','f811','f815','f824','f830','f831',
    'f833','f834','f841','f846','f847','f849','f850','f854','f857','f859',
    'f868','f972','f973','f974','f975','m804','m805','m867','m868','t014'
}

def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "."
    files = sorted(glob.glob(os.path.join(src, "probe_result_*.json")))
    merged = {}
    slices = []
    for fp in files:
        with open(fp, encoding="utf-8-sig") as f:
            data = json.load(f)
        slices.append(data.get("slice"))
        for vid, vers in data.get("results", {}).items():
            merged.setdefault(vid, set()).update(vers)

    def vkey(v):
        return tuple(int(p) for p in v.split("."))

    out = {vid: sorted(merged[vid], key=vkey) for vid in sorted(merged)}
    new = [vid for vid in out if vid.replace("techno-sp_ja_JP_", "").replace("_svss", "") not in KNOWN_JA_SVSS]

    with open("merged_result.json", "w", encoding="utf-8") as f:
        json.dump({"slices": slices, "results": out, "new": new}, f, ensure_ascii=False, indent=2)

    print(f"[*] merged {len(slices)} slices -> {len(out)} voices")
    print(f"[*] NEW (未发售候选): {len(new)}")
    for vid in new:
        print(f"  {vid}  versions={','.join(out[vid])}")

if __name__ == "__main__":
    main()
