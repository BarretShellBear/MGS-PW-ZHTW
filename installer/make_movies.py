"""Developer tool: payload data for the optional video step: SHA-256 of the 10 original movie files and a copy of the five .ass subtitle files,
plus the vendored cipher (pwtr's pwcrypt, MIT) the installer needs.
Output: installer/payload/movies.json, installer/payload/ass/*.ass, installer/vendor/pwcrypt.py + pwpaths.py   Usage: python make_movies.py"""
import hashlib, json, os, shutil, sys
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__)); JP = os.path.dirname(HERE)
STEMS = ["000628aa", "00abbd1b", "00abc51b", "00780c94", "00781494"]
BLANK = {"000628aa"}                                   # Kant card: black out the old text first
SRC = os.path.join(JP, "jp-pack", "mgspw", "JPN", "data")
os.makedirs(os.path.join(HERE, "payload", "ass"), exist_ok=True); os.makedirs(os.path.join(HERE, "vendor"), exist_ok=True)
items = []
for stem in STEMS:
    for folder in ("Mov", "hqMov"):
        p = os.path.join(SRC, folder, stem + ".xmx"); h = hashlib.sha256()
        with open(p, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
        items.append({"path": "JPN/data/%s/%s.xmx" % (folder, stem), "stem": stem, "old_sha256": h.hexdigest(), "blank": stem in BLANK})
    shutil.copyfile(os.path.join(JP, "movie-sample", stem + ".ass"), os.path.join(HERE, "payload", "ass", stem + ".ass"))
json.dump({"items": items}, open(os.path.join(HERE, "payload", "movies.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
fm = os.path.join(JP, "pwtr-jp", "pwtr", "formats")
for n in ("pwcrypt.py", "pwpaths.py"): shutil.copyfile(os.path.join(fm, n), os.path.join(HERE, "vendor", n))
print(len(items), "movies;", "vendor files copied")
