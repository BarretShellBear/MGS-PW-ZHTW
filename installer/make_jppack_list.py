"""Developer tool: list the files of the Japanese language pack (names and sizes only, no content) so the installer can recognise a pack folder.
Output: installer/payload/jppack_files.json   Usage: python make_jppack_list.py"""
import json, os, sys
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__)); JP = os.path.dirname(HERE)
ROOT = os.path.join(JP, "jp-pack", "mgspw")
out = []
for top in ("FONT", "JPN", "ms0"):
    for d, _, fs in os.walk(os.path.join(ROOT, top)):
        for n in sorted(fs):
            p = os.path.join(d, n); out.append({"path": os.path.relpath(p, ROOT).replace("\\", "/"), "size": os.path.getsize(p)})
out.sort(key=lambda e: e["path"])
os.makedirs(os.path.join(HERE, "payload"), exist_ok=True)
json.dump(out, open(os.path.join(HERE, "payload", "jppack_files.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(len(out), "files", sum(e["size"] for e in out), "bytes")
