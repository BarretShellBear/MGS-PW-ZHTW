"""Developer tool: build the installer payload (block-diff patches against the ORIGINAL Japanese-pack files).

For each of the 20 files the build writes (pwtr-project/output), compare it with the original file (jp-pack JPN files and the stock FONT)
in 64 KB blocks and store only the blocks that differ (zlib).  The installer rebuilds each new file from the user's own original file plus
these blocks, after checking that the user's original has the expected SHA-256.  No original data is stored in the payload except the
changed blocks of our own translation.
Output : installer/payload/manifest.json and installer/payload/<n>.dat
Usage  : python make_payload.py
"""
import hashlib, json, os, sys, zlib
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__)); JP = os.path.dirname(HERE)
SRC = os.path.join(JP, "pwtr-project", "output")
BASES = {"MLG": os.path.join(JP, "jp-pack", "mgspw", "JPN"), "FONT": os.path.join(JP, "jp-game", "mgspw", "FONT")}
DEST = {"MLG": "JPN", "FONT": "FONT"}          # output top folder -> folder inside the game's mgspw directory
OUT = os.path.join(HERE, "payload"); B = 65536

os.makedirs(OUT, exist_ok=True)
files = []; n = 0
for top in ("MLG", "FONT"):
    for d, _, fs in os.walk(os.path.join(SRC, top)):
        for name in sorted(fs):
            new_p = os.path.join(d, name); rest = os.path.relpath(new_p, os.path.join(SRC, top)).replace("\\", "/")
            old_p = os.path.join(BASES[top], rest)
            if not os.path.isfile(old_p): print("ERROR: original missing:", old_p); sys.exit(1)
            ho = hashlib.sha256(); hn = hashlib.sha256(); blocks = []; off = 0
            dat = "%02d.dat" % n
            with open(old_p, "rb") as fo, open(new_p, "rb") as fn, open(os.path.join(OUT, dat), "wb") as fd:
                idx = 0
                while True:
                    bo = fo.read(B); bn = fn.read(B)
                    if not bo and not bn: break
                    ho.update(bo); hn.update(bn)
                    if bo != bn:
                        z = zlib.compress(bn, 9); fd.write(z); blocks.append([idx, off, len(z)]); off += len(z)
                    idx += 1
            if not blocks: os.remove(os.path.join(OUT, dat)); dat = None
            files.append({"path": DEST[top] + "/" + rest, "old_size": os.path.getsize(old_p), "new_size": os.path.getsize(new_p),
                          "old_sha256": ho.hexdigest(), "new_sha256": hn.hexdigest(), "data": dat, "blocks": blocks})
            print("%-34s %9d -> %9d  blocks %5d  payload %8d" % (files[-1]["path"], files[-1]["old_size"], files[-1]["new_size"], len(blocks), off), flush=True)
            n += 1
json.dump({"block": B, "files": files}, open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
tot = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
print("files", len(files), "payload bytes", tot)
