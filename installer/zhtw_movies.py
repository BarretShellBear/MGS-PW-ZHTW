# -*- coding: utf-8 -*-
"""Optional video localisation for the installer: burn the Traditional-Chinese subtitles into the five text-card movies.

The user supplies their own ffmpeg (needs libx264 and libass); nothing is downloaded or bundled.  For each of the 10 files
(Mov/hqMov x 5 cards): verify the SHA-256 of the user's original, decrypt (pwcrypt, MIT, from the pwtr project), black out the old text
(Kant card only), burn our .ass with libass, re-encode like pwtr's hardsub (libx264 high, source level, CRF 18/19, no audio), encrypt under the
final file name, swap it in with the original kept as <name>.zhtw_orig.  On any failure the file is left untouched.
"""
import hashlib, json, os, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
BASE = getattr(sys, "_MEIPASS", HERE)
PAYLOAD = os.path.join(BASE, "payload")
for _d in (os.path.join(BASE, "vendor"), os.path.join(HERE, "vendor")):
    if os.path.isdir(_d) and _d not in sys.path: sys.path.insert(0, _d)
BAK = ".zhtw_orig"; TMP = ".zhtw_tmp"
MOVIES_MANIFEST = "zhtw_movies_manifest.json"
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
CRF = {720: 18, 1080: 19}


def load_movies():
    with open(os.path.join(PAYLOAD, "movies.json"), encoding="utf-8") as f: return json.load(f)


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def tools_from(path):
    """Return (ffmpeg, ffprobe) for a file or folder the user pointed at, or raise RuntimeError."""
    path = (path or "").strip().strip('"')
    if os.path.isdir(path):
        cand = [os.path.join(path, n) for n in ("ffmpeg.exe", "ffmpeg", os.path.join("bin", "ffmpeg.exe"), os.path.join("bin", "ffmpeg"))]
        path = next((c for c in cand if os.path.isfile(c)), "")
    if not path or not os.path.isfile(path): raise RuntimeError("找不到 ffmpeg，請指定 ffmpeg 執行檔或其所在資料夾。")
    d = os.path.dirname(path); ext = os.path.splitext(path)[1]
    probe = os.path.join(d, "ffprobe" + ext)
    if not os.path.isfile(probe): raise RuntimeError("同一個資料夾裡找不到 ffprobe。")
    return path, probe


def check_ffmpeg(ffmpeg):
    def out(args):
        try: return subprocess.run([ffmpeg] + args, capture_output=True, text=True, creationflags=NOWIN, timeout=60).stdout
        except (OSError, subprocess.SubprocessError) as e: raise RuntimeError("無法執行 ffmpeg：%s" % e)
    if "ffmpeg version" not in out(["-version"]): raise RuntimeError("這個檔案不是可用的 ffmpeg。")
    if "libx264" not in out(["-hide_banner", "-encoders"]): raise RuntimeError("這個 ffmpeg 沒有 libx264 編碼器。")
    if " subtitles " not in out(["-hide_banner", "-filters"]): raise RuntimeError("這個 ffmpeg 沒有 libass（subtitles 濾鏡）。")


def _probe(ffprobe, src):
    r = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=level,width,height", "-of", "json", src],
                       capture_output=True, text=True, creationflags=NOWIN, check=True)
    return json.loads(r.stdout)["streams"][0]


def _blank_ink(ffmpeg, src, info):
    """drawbox filter that blacks out only the rows carrying text in a still at 4 s (numpy only; no Pillow)."""
    import numpy as np
    w, h = int(info["width"]), int(info["height"])
    r = subprocess.run([ffmpeg, "-v", "error", "-ss", "4", "-i", src, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                       capture_output=True, creationflags=NOWIN, check=True)
    grey = np.frombuffer(r.stdout, np.uint8)
    if grey.size != w * h: return ""
    rows = np.where(grey.reshape(h, w).max(axis=1) > 40)[0]
    if rows.size == 0: return ""
    bands = []; prev = None
    for row in rows:
        if prev is None or row - prev > 8: bands.append([int(row), int(row)])
        else: bands[-1][1] = int(row)
        prev = row
    top = max(0, min(b[0] for b in bands) - 16); bottom = min(h, max(b[1] for b in bands) + 16)
    return "drawbox=x=0:y=%d:w=%d:h=%d:color=black:t=fill" % (top, w, bottom - top)


def encode_one(ffmpeg, ffprobe, src_xmx, name, ass_path, blank, work):
    """Return the bytes of the translated, encrypted movie for the original file src_xmx (which has file name `name`)."""
    import pwcrypt
    plain = os.path.join(work, "src.mp4"); out = os.path.join(work, "zh.mp4")
    with open(src_xmx, "rb") as f: data = f.read()
    with open(plain, "wb") as f: f.write(pwcrypt.crypt(data, name))
    info = _probe(ffprobe, plain)
    chain = []
    if blank:
        b = _blank_ink(ffmpeg, plain, info)
        if b: chain.append(b)
    shutil.copyfile(ass_path, os.path.join(work, "sub.ass"))
    chain.append("subtitles=sub.ass")                      # relative to cwd=work: no path escaping needed
    cmd = [ffmpeg, "-v", "error", "-y", "-i", "src.mp4", "-vf", ",".join(chain), "-c:v", "libx264", "-profile:v", "high",
           "-level", str(int(info["level"]) / 10), "-crf", str(CRF.get(int(info["height"]), 19)), "-pix_fmt", "yuv420p", "-an",
           "-movflags", "+faststart", "zh.mp4"]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=work, creationflags=NOWIN)
    if r.returncode != 0 or not os.path.isfile(out): raise RuntimeError("ffmpeg 失敗：" + (r.stderr or "")[-300:])
    with open(out, "rb") as f: return pwcrypt.crypt(f.read(), name)


def check_originals(game, log):
    """Return a list of problems (missing files or originals that do not have the expected SHA-256)."""
    probs = []
    for m in load_movies()["items"]:
        p = os.path.join(game, *m["path"].split("/"))
        src = p + BAK if os.path.isfile(p + BAK) else p
        if not os.path.isfile(src): probs.append("找不到影片：" + m["path"]); continue
        log("檢查影片 " + m["path"])
        if _sha(src) != m["old_sha256"]: probs.append("影片與預期不符：" + m["path"])
    return probs


def install_movies(game, ffmpeg_path, log, progress, cancel=lambda: None):
    ffmpeg, ffprobe = tools_from(ffmpeg_path); check_ffmpeg(ffmpeg)
    items = load_movies()["items"]
    probs = check_originals(game, log)
    if probs: raise RuntimeError("影片檢查未通過，已略過影片（保持日文）：\n" + "\n".join(probs[:6]))
    done = []
    for i, m in enumerate(items):
        cancel(); progress(i / len(items))
        p = os.path.join(game, *m["path"].split("/")); bak = p + BAK; src = bak if os.path.isfile(bak) else p
        log("處理影片 %s（%d/%d）" % (m["path"], i + 1, len(items)))
        with tempfile.TemporaryDirectory(prefix="zhtw_mov_") as work:
            new = encode_one(ffmpeg, ffprobe, src, os.path.basename(p), os.path.join(PAYLOAD, "ass", m["stem"] + ".ass"), m.get("blank", False), work)
        tmp = p + TMP
        with open(tmp, "wb") as f: f.write(new)
        if not os.path.isfile(bak): os.replace(p, bak)
        os.replace(tmp, p); done.append({"path": m["path"], "size": len(new)})
    with open(os.path.join(game, MOVIES_MANIFEST), "w", encoding="utf-8") as fh:
        json.dump({"installed_at": time.strftime("%Y-%m-%d %H:%M:%S"), "files": done}, fh, ensure_ascii=False, indent=1)
    progress(1.0); log("影片完成")


def remove_movies(game, log):
    mp = os.path.join(game, MOVIES_MANIFEST)
    if not os.path.isfile(mp): return
    for r in json.load(open(mp, encoding="utf-8"))["files"]:
        p = os.path.join(game, *r["path"].split("/")); bak = p + BAK
        if os.path.isfile(bak):
            if os.path.isfile(p): os.remove(p)
            os.replace(bak, p); log("已還原影片 " + r["path"])
        else: log("警告：找不到影片備份，未還原 " + r["path"])
    os.remove(mp)
