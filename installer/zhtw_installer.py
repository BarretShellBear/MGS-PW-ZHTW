#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MGS Peace Walker (Master Collection) 繁體中文化 安裝程式（Windows／SteamOS 共用）。

有視窗介面（tkinter）時開精靈；沒有 tkinter 或加 --cli 時用命令列。
Usage:
  zhtw_installer.py                      開啟安裝精靈
  zhtw_installer.py --cli                命令列互動
  zhtw_installer.py --cli --game PATH --accept install|remove|status    非互動（PATH 為 MGS_PW 或其下的 mgspw 資料夾）
"""
import argparse, hashlib, json, os, re, shutil, sys, time, zlib

VERSION = "Beta 0.2"
APP = "MGS Peace Walker 繁體中文化"
HERE = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
PAYLOAD = os.path.join(HERE if os.path.isdir(os.path.join(HERE, "payload")) else getattr(sys, "_MEIPASS", HERE), "payload")   # next to the program (exe or script)
MANIFEST_NAME = "zhtw_manifest.json"       # written into the game's mgspw folder
JP_MANIFEST = "jppack_manifest.json"       # what this installer copied from the Japanese pack (for clean removal)
JP_BAK = ".jppack_orig"
VERSION_FILE = "zhtw_version.txt"
BAK = ".zhtw_orig"; TMP = ".zhtw_tmp"
IS_LINUX = sys.platform.startswith("linux")

DISCLAIMER = [
    "本繁中化包為非官方的玩家自製作品，與 Konami 及任何版權方無關。",
    "本繁中化包的翻譯、程式與文件由 AI（Anthropic 的 Claude）協助製作，並經製作者逐步檢視與修正；仍可能有誤譯、不通順、用詞不一致或缺字漏字，歡迎回報。",
    "本繁中化包只適用於日文版（以日文版為基礎，需搭配日文語言包）；英文版的繁體中文模組也將會製作。本繁中化包不含遊戲本體，也不含日文語言包；使用者須自行擁有正版遊戲，日文語言包須自行取得，本程式不提供來源。",
    "安裝前請自行備份存檔。本程式會備份被取代的檔案，但製作者對任何資料損失、遊戲無法執行或其他後果不負責任。",
    "禁止商用，禁止轉售。",
    "遊戲內容與商標的著作權屬於原權利人。",
    "請自行確認所在地區的法律是否允許使用本繁中化包。",
    "目前為測試階段，翻譯可能不完整，或有缺字、漏字，歡迎回報；回報請至 GitHub Issues，並附上版本號。"
    "不想繼續使用時，可重新執行本安裝程式選擇「移除繁中化包」，會還原原本的檔案。收到回報後會修正並釋出新版本。",
]
DISCLAIMER_STEAMOS = ("製作者沒有 SteamOS 設備，SteamOS 版安裝程式只是順便製作，未經實機測試；"
                      "若發現重大執行瑕疵，將中止 SteamOS 版安裝程式的更新。回報時請註明設備型號與 SteamOS 版本。")
FINISH_TEXT = ("安裝完成。\n\n版本：%s\n\n回報問題請至 https://github.com/BarretShellBear/MGS-PW-ZHTW/issues ，並附上版本號（也記錄在遊戲資料夾的 " + VERSION_FILE + "）。\n\n"
               "強烈建議另外安裝 MGSPatriotFix（本程式不內附）：\nhttps://www.nexusmods.com/metalgearsolidpeacewalkermc/mods/1")


if HERE not in sys.path: sys.path.insert(0, HERE)
try:
    import zhtw_movies
except Exception:          # video step unavailable (module missing): everything else still works
    zhtw_movies = None


class Cancel(Exception): pass


def sha256_file(path, cb=None):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b: break
            h.update(b)
            if cb: cb(len(b))
    return h.hexdigest()


def load_payload():
    with open(os.path.join(PAYLOAD, "manifest.json"), encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- game folder detection
def _steam_roots():
    roots = []
    if sys.platform == "win32":
        try:
            import winreg
            for hive, key in ((winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"), (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")):
                try:
                    with winreg.OpenKey(hive, key) as k: roots.append(winreg.QueryValueEx(k, "SteamPath" if hive == winreg.HKEY_CURRENT_USER else "InstallPath")[0])
                except OSError: pass
        except ImportError: pass
        roots += [r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam"]
    else:
        h = os.path.expanduser("~")
        roots += [h + "/.local/share/Steam", h + "/.steam/steam", h + "/.steam/root", h + "/.var/app/com.valvesoftware.Steam/.local/share/Steam"]
    return [os.path.normpath(r) for r in roots if r and os.path.isdir(r)]


def find_game():
    """Return the game's mgspw folder if Steam has Peace Walker (appid 2492660) installed, else None."""
    libs = []
    for r in _steam_roots():
        libs.append(r)
        vdf = os.path.join(r, "steamapps", "libraryfolders.vdf")
        if os.path.isfile(vdf):
            try:
                for m in re.finditer(r'"path"\s+"([^"]+)"', open(vdf, encoding="utf-8", errors="replace").read()):
                    libs.append(os.path.normpath(m.group(1).replace("\\\\", "\\")))
            except OSError: pass
    for lib in dict.fromkeys(libs):
        common = os.path.join(lib, "steamapps", "common")
        name = "MGS_PW"
        acf = os.path.join(lib, "steamapps", "appmanifest_2492660.acf")
        if os.path.isfile(acf):
            m = re.search(r'"installdir"\s+"([^"]+)"', open(acf, encoding="utf-8", errors="replace").read())
            if m: name = m.group(1)
        g = resolve_game(os.path.join(common, name))
        if g: return g
    return None


def resolve_game(path):
    """Accept the MGS_PW folder or its mgspw subfolder; return the mgspw folder or None."""
    if not path: return None
    path = os.path.normpath(path)
    for cand in (path, os.path.join(path, "mgspw")):
        if os.path.isdir(cand) and os.path.basename(cand).lower() == "mgspw": return cand
    return None


def default_game_hint():
    if sys.platform == "win32": return r"C:\Program Files (x86)\Steam\steamapps\common\MGS_PW\mgspw"
    return os.path.expanduser("~/.local/share/Steam/steamapps/common/MGS_PW/mgspw")


# ---------------------------------------------------------------- state / checks
def read_manifest(game):
    p = os.path.join(game, MANIFEST_NAME)
    if os.path.isfile(p):
        try: return json.load(open(p, encoding="utf-8"))
        except (OSError, ValueError): return None
    return None


def installed_state(game):
    """'none' | 'installed' | 'partial' based on the manifest and the files present."""
    m = read_manifest(game)
    if not m: return "none"
    ok = 0
    for f in m["files"]:
        p = os.path.join(game, *f["path"].split("/"))
        if os.path.isfile(p) and os.path.getsize(p) == f["new_size"] and os.path.isfile(p + BAK): ok += 1
    return "installed" if ok == len(m["files"]) else "partial"


def check_game(game, payload, log, pack_given=False):
    """Preflight: every file must exist and be either the expected original, already patched, or restorable from our backup."""
    problems = []
    if pack_given: return problems
    for f in payload["files"]:
        p = os.path.join(game, *f["path"].split("/"))
        if not os.path.isfile(p) and not os.path.isfile(p + BAK):
            problems.append("找不到檔案：" + f["path"] + "（日文語言包與遊戲是否已安裝？）")
    return problems


def free_space_ok(game, payload, extra=0):
    need = max(f["new_size"] for f in payload["files"]) * 2 + sum(f["new_size"] for f in payload["files"]) // 4 + (300 << 20) + extra
    free = shutil.disk_usage(game).free
    return free >= need, need, free


# ---------------------------------------------------------------- install / remove
def build_file(src_path, f, B, dat_path, out_path, progress):
    h = hashlib.sha256(); changed = {b[0]: (b[1], b[2]) for b in f["blocks"]}
    nblocks = (f["new_size"] + B - 1) // B
    with open(src_path, "rb") as so, open(out_path, "wb") as out:
        dat = open(dat_path, "rb") if f["data"] else None
        try:
            for idx in range(nblocks):
                if idx in changed:
                    off, ln = changed[idx]; dat.seek(off); b = zlib.decompress(dat.read(ln))
                else:
                    so.seek(idx * B); b = so.read(B)
                out.write(b); h.update(b); progress(len(b))
        finally:
            if dat: dat.close()
    return h.hexdigest()


def install(game, payload, log, progress, cancel=lambda: None):
    """Install or repair.  Originals are kept next to the new files as <name>.zhtw_orig."""
    B = payload["block"]; done = []
    # phase 1: verify every source file first, so a mismatch stops the run before anything is modified
    for f in payload["files"]:
        cancel()
        p = os.path.join(game, *f["path"].split("/")); bak = p + BAK
        if os.path.isfile(p) and os.path.getsize(p) == f["new_size"] and os.path.isfile(bak) and sha256_file(p) == f["new_sha256"]:
            continue
        log("檢查原始檔 " + f["path"])
        if sha256_file(bak if os.path.isfile(bak) else p) != f["old_sha256"]:
            raise RuntimeError("原始檔案與預期不符，已停止（沒有改動任何檔案）：" + f["path"] +
                               "\n可能原因：遊戲版本不同、檔案已被其他 MOD 修改。請以 Steam「驗證遊戲檔案完整性」還原後再試。")
    total = sum(f["new_size"] for f in payload["files"]); state = {"n": 0}
    def prog(n):
        state["n"] += n; progress(min(1.0, state["n"] / total))
        cancel()
    for f in payload["files"]:
        cancel()
        p = os.path.join(game, *f["path"].split("/")); bak = p + BAK; tmp = p + TMP
        log("處理 " + f["path"])
        if os.path.isfile(p) and os.path.getsize(p) == f["new_size"] and sha256_file(p) == f["new_sha256"] and os.path.isfile(bak):
            log("  已是繁中化版，略過"); state["n"] += f["new_size"]; progress(min(1.0, state["n"] / total)); done.append(f); continue
        # find the original: the backup if we made one, else the file itself
        if os.path.isfile(bak):
            src = bak
        else:
            src = p
        if os.path.isfile(tmp): os.remove(tmp)
        new_hash = build_file(src, f, B, os.path.join(PAYLOAD, f["data"]) if f["data"] else None, tmp, prog)
        if new_hash != f["new_sha256"]:
            os.remove(tmp); raise RuntimeError("產生的檔案驗證失敗，已停止：" + f["path"])
        if not os.path.isfile(bak): os.replace(p, bak)
        os.replace(tmp, p); done.append(f)
    manifest = {"version": VERSION, "installed_at": time.strftime("%Y-%m-%d %H:%M:%S"), "files": done}
    with open(os.path.join(game, MANIFEST_NAME), "w", encoding="utf-8") as fh: json.dump(manifest, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(game, VERSION_FILE), "w", encoding="utf-8") as fh: fh.write("MGS Peace Walker 繁體中文化 " + VERSION + "\n")
    log("完成")


def remove(game, log):
    """Put the originals back.  Only files named in our manifest are touched."""
    if zhtw_movies: zhtw_movies.remove_movies(game, log)
    m = read_manifest(game)
    if not m: raise RuntimeError("找不到安裝紀錄（" + MANIFEST_NAME + "），沒有可移除的繁中化包。")
    for f in m["files"]:
        p = os.path.join(game, *f["path"].split("/")); bak = p + BAK
        if os.path.isfile(bak):
            if os.path.isfile(p): os.remove(p)
            os.replace(bak, p); log("已還原 " + f["path"])
        else:
            log("警告：找不到備份，未還原 " + f["path"] + "（可用 Steam「驗證遊戲檔案完整性」還原）")
    for n in (MANIFEST_NAME, VERSION_FILE):
        q = os.path.join(game, n)
        if os.path.isfile(q): os.remove(q)
    log("繁中化包已移除")


# ---------------------------------------------------------------- Japanese language pack (only ever copied from the user's own folder)
def jp_list():
    p = os.environ.get("ZHTW_JPLIST") or os.path.join(PAYLOAD, "jppack_files.json")
    with open(p, encoding="utf-8") as f: return json.load(f)


def jp_status(game):
    """('installed', []) when every pack file is in the game folder with the expected size (a file our patch replaced may have its new size),
    else ('missing', [relative paths])."""
    alt = {}
    try:
        for f in load_payload()["files"]: alt[f["path"]] = {f["old_size"], f["new_size"]}
    except OSError: pass
    missing = []
    for e in jp_list():
        p = os.path.join(game, *e["path"].split("/"))
        ok = os.path.isfile(p) and os.path.getsize(p) in ({e["size"]} | alt.get(e["path"], set()))
        if not ok: missing.append(e["path"])
    return ("installed" if not missing else "missing"), missing


def resolve_pack(path):
    """Accept the folder that holds FONT/JPN/ms0 (or its parent whose child is mgspw).  Return (root, problems)."""
    if not path: return None, ["尚未指定資料夾"]
    path = os.path.normpath(path)
    cands = [path, os.path.join(path, "mgspw")]
    best = None
    for c in cands:
        if all(os.path.isdir(os.path.join(c, d)) for d in ("FONT", "JPN", "ms0")): best = c; break
    if not best: return None, ["這個資料夾裡找不到 FONT、JPN、ms0 三個子資料夾"]
    probs = []
    for e in jp_list():
        p = os.path.join(best, *e["path"].split("/"))
        if not os.path.isfile(p): probs.append("缺少檔案：" + e["path"])
        elif os.path.getsize(p) != e["size"]: probs.append("大小不符：" + e["path"])
    return (best if not probs else None), probs


def install_jppack(game, src_root, log, progress, cancel=lambda: None):
    """Copy the pack files that are missing from the game folder.  Existing files of the same size are left alone; a file of a
    different size is set aside as <name>.jppack_orig before being replaced.  Everything done is recorded for clean removal."""
    entries = jp_list(); total = sum(e["size"] for e in entries); doneb = [0]; rec = []
    old = {}
    mp = os.path.join(game, JP_MANIFEST)
    if os.path.isfile(mp):
        try: old = {r["path"]: r for r in json.load(open(mp, encoding="utf-8"))["files"]}
        except (OSError, ValueError, KeyError): old = {}
    for e in entries:
        cancel()
        rel = e["path"]; dst = os.path.join(game, *rel.split("/")); src = os.path.join(src_root, *rel.split("/"))
        if rel in old: rec.append(old[rel])
        if os.path.isfile(dst) and os.path.getsize(dst) == e["size"]:
            doneb[0] += e["size"]; progress(doneb[0] / total); continue
        os.makedirs(os.path.dirname(dst), exist_ok=True); tmp = dst + TMP
        log("複製 " + rel)
        with open(src, "rb") as a, open(tmp, "wb") as b:
            while True:
                chunk = a.read(4 << 20)
                if not chunk: break
                b.write(chunk); doneb[0] += len(chunk); progress(min(1.0, doneb[0] / total)); cancel()
        if os.path.getsize(tmp) != e["size"]: os.remove(tmp); raise RuntimeError("複製後大小不符：" + rel)
        action = "added"
        if os.path.isfile(dst): os.replace(dst, dst + JP_BAK); action = "replaced"
        os.replace(tmp, dst); rec.append({"path": rel, "action": action, "size": e["size"]})
    with open(mp, "w", encoding="utf-8") as fh:
        json.dump({"installed_at": time.strftime("%Y-%m-%d %H:%M:%S"), "files": rec}, fh, ensure_ascii=False, indent=1)
    log("日文包完成（%d 個檔案由本程式處理）" % len(rec))


def remove_jppack(game, log):
    mp = os.path.join(game, JP_MANIFEST)
    if not os.path.isfile(mp): log("日文包不是由本程式安裝的（沒有安裝紀錄），保留不動。"); return
    files = json.load(open(mp, encoding="utf-8"))["files"]; dirs = set()
    for r in files:
        dst = os.path.join(game, *r["path"].split("/")); dirs.add(os.path.dirname(dst))
        if r["action"] == "replaced" and os.path.isfile(dst + JP_BAK):
            if os.path.isfile(dst): os.remove(dst)
            os.replace(dst + JP_BAK, dst); log("已還原 " + r["path"])
        elif r["action"] == "added":
            if os.path.isfile(dst): os.remove(dst); log("已移除 " + r["path"])
    for d in sorted(dirs, key=len, reverse=True):
        while os.path.normpath(d) != os.path.normpath(game):          # climb up, removing folders this removal left empty
            try:
                if os.listdir(d): break
                os.rmdir(d)
            except OSError: break
            d = os.path.dirname(d)
    os.remove(mp); log("日文包已移除（只移除由本程式複製的檔案）")


# ---------------------------------------------------------------- 代勞模式 (auto mode): look for things so the user does not have to
def find_pack_auto(game=None):
    """Search the usual places for a complete Japanese-pack folder (FONT + JPN + ms0, every file with the right size)."""
    h = os.path.expanduser("~"); roots = [os.path.join(h, n) for n in ("Downloads", "Desktop", "Documents")]
    if sys.platform == "win32":
        roots += [h] + ["%s:%s" % (c, os.sep) for c in "DEFGH" if os.path.isdir("%s:%s" % (c, os.sep))]
    else:
        roots += [h, "/run/media", "/media", "/mnt"]
    skip = {".cache", ".local", ".config", ".steam", ".var", "proc", "sys", "$RECYCLE.BIN", "System Volume Information", "Windows", "Program Files", "Program Files (x86)", "steamapps"}
    gnorm = os.path.normcase(os.path.normpath(game)) if game else None
    seen = set()
    for root in roots:
        if not os.path.isdir(root) or root in seen: continue
        seen.add(root); base = root.rstrip(os.sep).count(os.sep)
        for d, dirs, _ in os.walk(root):
            if d.count(os.sep) - base >= 4: dirs[:] = []; continue
            dirs[:] = [x for x in dirs if x not in skip and not x.startswith(".")]
            if {"FONT", "JPN", "ms0"} <= set(dirs):
                if gnorm and os.path.normcase(os.path.normpath(d)) == gnorm: continue
                src, _ = resolve_pack(d)
                if src: return src
    return None


def find_ffmpeg_auto():
    ff = shutil.which("ffmpeg"); fp = shutil.which("ffprobe")
    return ff if (ff and fp) else ""


# ---------------------------------------------------------------- command line
def cli(args):
    payload = load_payload()
    def log(s): print(s, flush=True)
    last = [-1]
    def progress(v):
        pct = int(v * 100)
        if pct != last[0]: last[0] = pct; sys.stdout.write("\r進度 %3d%%" % pct); sys.stdout.flush()
    print(APP, VERSION)
    if not args.accept:
        print("\n免責聲明：")
        for i, t in enumerate(DISCLAIMER, 1): print("%d. %s" % (i, t))
        if IS_LINUX: print("%d. %s" % (len(DISCLAIMER) + 1, DISCLAIMER_STEAMOS))
        if input("\n輸入 yes 表示同意：").strip().lower() != "yes": print("未同意，結束。"); return 1
    game = resolve_game(args.game) if args.game else find_game()
    if not game:
        g = input("找不到遊戲，請輸入 MGS_PW 資料夾路徑：").strip().strip('"'); game = resolve_game(g)
        if not game: print("不是有效的遊戲資料夾（需含 mgspw）。"); return 1
    print("遊戲資料夾：", game)
    st = installed_state(game); act = args.action
    if not act:
        if st != "none":
            print("已安裝過（狀態：%s）。1 更新／修復  2 只移除繁中化包  3 移除繁中化包與日文包  4 取消" % st); c = input("> ").strip()
            act = {"1": "install", "2": "remove", "3": "remove-all"}.get(c)
        else: act = "install"
        if not act: return 0
    if act == "status": print("狀態：", st, read_manifest(game) and read_manifest(game)["version"] or ""); return 0
    try:
        if act == "remove": remove(game, log)
        elif act == "remove-all": remove(game, log); remove_jppack(game, log)
        else:
            jst, jmiss = jp_status(game); src = None
            if jst == "missing":
                if not args.jppack and args.auto:
                    print("代勞模式：正在尋找你的日文包資料夾（Downloads、桌面、USB／SD 卡…），請稍候…")
                    args.jppack = find_pack_auto(game) or ""
                    if args.jppack: print("找到日文包：", args.jppack)
                if not args.jppack: print("遊戲資料夾裡沒有日文語言包（缺少 %d 個檔案）%s。請以 --jppack 指定自己的日文包資料夾；本程式不提供日文包來源。" % (len(jmiss), "，自動尋找也沒找到" if args.auto else "")); return 1
                src, jprobs = resolve_pack(args.jppack)
                if not src: print("日文包資料夾驗證失敗：\n" + "\n".join(jprobs[:8])); return 1
            probs = check_game(game, payload, log, pack_given=bool(src))
            if probs: print("\n".join(probs)); return 1
            ok, need, free = free_space_ok(game, payload, extra=(sum(e["size"] for e in jp_list()) if src else 0))
            if not ok: print("磁碟空間不足：需要約 %d MB，可用 %d MB。" % (need >> 20, free >> 20)); return 1
            if src: install_jppack(game, src, log, progress); print()
            install(game, payload, log, progress); print()
            if args.auto and not args.ffmpeg:
                ff = find_ffmpeg_auto()
                if ff and not args.accept and input("找到 ffmpeg。要同時中文化 5 支文字卡影片嗎？（約需數分鐘）輸入 y 表示要，其餘跳過：").strip().lower() == "y": args.ffmpeg = ff
                elif not ff: print("沒有找到 ffmpeg，影片維持日文。")
            if args.ffmpeg:
                try: zhtw_movies.install_movies(game, args.ffmpeg, log, progress); print()
                except Exception as e: print("影片繁中化已略過（保持日文）：", e)
            print(FINISH_TEXT % VERSION)
    except Exception as e:
        print("\n錯誤：", e); return 1
    return 0


# ---------------------------------------------------------------- GUI
def gui(args):
    import threading, tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    payload = load_payload()
    root = tk.Tk(); root.title(APP + "　" + VERSION); root.geometry("760x520"); root.resizable(False, False)
    st = {"game": None, "action": tk.StringVar(value="install")}
    frames = {}; order = []
    holder = ttk.Frame(root, padding=14); holder.pack(fill="both", expand=True)
    bar = ttk.Frame(root, padding=(14, 0, 14, 12)); bar.pack(fill="x")
    btn_back = ttk.Button(bar, text="上一步"); btn_next = ttk.Button(bar, text="下一步"); btn_cancel = ttk.Button(bar, text="取消", command=root.destroy)
    btn_cancel.pack(side="right"); btn_next.pack(side="right", padx=6); btn_back.pack(side="right")

    def title(f, t): ttk.Label(f, text=t, font=("", 14, "bold")).pack(anchor="w", pady=(0, 10))

    # page: disclaimer
    f1 = ttk.Frame(holder); frames["disc"] = f1; title(f1, "免責聲明")
    txt = tk.Text(f1, height=17, wrap="word"); txt.pack(fill="both", expand=True)
    lines = ["%d. %s" % (i, t) for i, t in enumerate(DISCLAIMER, 1)] + (["%d. %s" % (len(DISCLAIMER) + 1, DISCLAIMER_STEAMOS)] if IS_LINUX else [])
    txt.insert("1.0", "\n\n".join(lines)); txt.config(state="disabled")
    agree = tk.BooleanVar(value=False)
    auto = tk.BooleanVar(value=bool(IS_LINUX or getattr(args, "auto", False)))
    ttk.Checkbutton(f1, text="我已閱讀並同意以上聲明", variable=agree, command=lambda: refresh()).pack(anchor="w", pady=(8, 2))
    ttk.Checkbutton(f1, text="代勞模式（建議勾選）：自動找遊戲資料夾、日文包與 ffmpeg，找得到的步驟就不再詢問", variable=auto).pack(anchor="w", pady=2)

    # page: maintenance menu
    f2 = ttk.Frame(holder); frames["menu"] = f2; title(f2, "已偵測到安裝過繁中化包")
    lbl_state = ttk.Label(f2, text=""); lbl_state.pack(anchor="w", pady=(0, 10))
    for val, t in (("install", "更新／修復（重新套用繁中化檔）"), ("remove", "只移除繁中化包（還原原本的檔案）"),
                   ("remove-all", "移除繁中化包與日文包（日文包只移除由本程式複製的檔案）")):
        ttk.Radiobutton(f2, text=t, value=val, variable=st["action"]).pack(anchor="w", pady=4)

    # page: game folder
    f3 = ttk.Frame(holder); frames["folder"] = f3; title(f3, "選擇遊戲資料夾")
    ttk.Label(f3, text="請選擇 Steam 的 MGS_PW 資料夾（或其中的 mgspw）：").pack(anchor="w")
    rowf = ttk.Frame(f3); rowf.pack(fill="x", pady=8)
    pathvar = tk.StringVar(value=find_game() or default_game_hint())
    ttk.Entry(rowf, textvariable=pathvar).pack(side="left", fill="x", expand=True)
    def browse():
        d = filedialog.askdirectory(initialdir=os.path.dirname(pathvar.get()) or None)
        if d: pathvar.set(d)
    ttk.Button(rowf, text="瀏覽…", command=browse).pack(side="left", padx=6)
    lbl_folder = ttk.Label(f3, text="", foreground="#a00", wraplength=700, justify="left"); lbl_folder.pack(anchor="w", pady=6)

    # page: Japanese language pack (a step of its own: choose the pack first, the movies come next)
    fj = ttk.Frame(holder); frames["jp"] = fj; title(fj, "步驟：日文語言包")
    lbl_jp_head = ttk.Label(fj, text="", justify="left", wraplength=700); lbl_jp_head.pack(anchor="w")
    ttk.Label(fj, text="繁中化包以日文版為基礎，需要日文語言包。本程式不提供日文包；已安裝的會自動略過，沒有的話請指定你自己已取得的日文包資料夾（內含 FONT、JPN、ms0 三個資料夾），程式只會複製缺少的檔案，不會覆蓋同大小的現有檔案。",
              justify="left", wraplength=700, foreground="gray").pack(anchor="w", pady=(6, 0))
    jpvar = tk.StringVar(); jprow = ttk.Frame(fj); jprow.pack(fill="x", pady=10)
    jp_entry = ttk.Entry(jprow, textvariable=jpvar); jp_entry.pack(side="left", fill="x", expand=True)
    def jbrowse():
        d = filedialog.askdirectory()
        if d: jpvar.set(d)
    jp_btn = ttk.Button(jprow, text="瀏覽…", command=jbrowse); jp_btn.pack(side="left", padx=6)
    lbl_jp = ttk.Label(fj, text="", foreground="#a00", wraplength=700, justify="left"); lbl_jp.pack(anchor="w", pady=6)
    ttk.Label(fj, text="沒有日文包？請自行取得後再執行本安裝程式；按「取消」離開。", foreground="gray").pack(anchor="w")

    # page: optional movies
    fv = ttk.Frame(holder); frames["video"] = fv; title(fv, "步驟：影片繁中化（選用）")
    want_video = tk.StringVar(value="skip"); ffvar = tk.StringVar()
    ttk.Label(fv, text="遊戲裡有 5 支只有文字的影片：康德引言卡（開頭的《永久和平論》引言）、工作人員名單、捲動名單（片尾）、兩部年表（前情提要），共 10 個檔案（720p 與 1080p）。繁中化會把中文字幕燒進影片裡，約需數分鐘；不繁中化則這 5 支影片維持日文，其他部分不受影響。",
              justify="left", wraplength=700).pack(anchor="w")
    ttk.Radiobutton(fv, text="略過，影片維持日文（建議）", value="skip", variable=want_video, command=lambda: refresh()).pack(anchor="w", pady=(12, 2))
    ttk.Radiobutton(fv, text="同時繁中化影片（需要自備 ffmpeg）", value="do", variable=want_video, command=lambda: refresh()).pack(anchor="w")
    ttk.Label(fv, text="ffmpeg 位置（需含 libx264 與 libass；本程式不下載、不內附任何軟體）：").pack(anchor="w", pady=(12, 2))
    ffrow = ttk.Frame(fv); ffrow.pack(fill="x")
    ff_entry = ttk.Entry(ffrow, textvariable=ffvar); ff_entry.pack(side="left", fill="x", expand=True)
    def ffbrowse():
        d = filedialog.askopenfilename(title="選擇 ffmpeg 執行檔")
        if d: ffvar.set(d)
    ff_btn = ttk.Button(ffrow, text="瀏覽…", command=ffbrowse); ff_btn.pack(side="left", padx=6)
    lbl_video = ttk.Label(fv, text="", foreground="#a00", wraplength=700, justify="left"); lbl_video.pack(anchor="w", pady=8)

    # page: install
    f4 = ttk.Frame(holder); frames["run"] = f4; title(f4, "安裝中")
    pb = ttk.Progressbar(f4, maximum=1000); pb.pack(fill="x", pady=6)
    logbox = tk.Text(f4, height=14, wrap="word", state="disabled"); logbox.pack(fill="both", expand=True)

    # page: finish
    f5 = ttk.Frame(holder); frames["end"] = f5; title(f5, "完成")
    endtxt = tk.Text(f5, height=16, wrap="word"); endtxt.pack(fill="both", expand=True)

    order[:] = ["disc", "menu", "folder", "run", "end"]
    cur = {"page": "disc", "busy": False}

    def show(p):
        for k, f in frames.items(): f.pack_forget()
        frames[p].pack(fill="both", expand=True); cur["page"] = p; refresh()

    def refresh():
        p = cur["page"]
        btn_back.config(state="normal" if p in ("menu", "folder", "jp", "video") and not cur["busy"] else "disabled")
        btn_next.config(state="disabled", text="下一步")
        if p == "disc": btn_next.config(state="normal" if agree.get() else "disabled")
        elif p == "menu": btn_next.config(state="normal")
        elif p == "folder": btn_next.config(state="normal", text="下一步" if st["action"].get() == "install" else "移除")
        elif p == "jp": btn_next.config(state="normal", text="下一步")
        elif p == "video":
            doing = want_video.get() == "do"
            btn_next.config(state="normal", text="安裝" if doing else "略過影片並安裝")
            ff_entry.config(state="normal" if doing else "disabled"); ff_btn.config(state="normal" if doing else "disabled")
        elif p == "end": btn_next.config(state="normal", text="關閉")
        btn_cancel.config(state="disabled" if cur["busy"] else "normal")

    def logf(s):
        def w(): logbox.config(state="normal"); logbox.insert("end", s + "\n"); logbox.see("end"); logbox.config(state="disabled")
        root.after(0, w)
    def progf(v): root.after(0, lambda: pb.config(value=int(v * 1000)))

    def go_next():
        p = cur["page"]
        if p == "disc": show("folder_or_menu")
        elif p == "menu": goto_folder()
        elif p == "folder": start()
        elif p == "jp": jp_next()
        elif p == "video": start_run()
        elif p == "end": root.destroy()

    def go_back():
        p = cur["page"]
        if p == "folder": show("menu" if st.get("had") else "disc")
        elif p == "menu": show("disc")
        elif p == "jp": show("folder")
        elif p == "video": show("jp")

    real_show = show
    def show(p):                      # noqa: F811  (wrap to resolve the virtual page)
        if p == "folder_or_menu":
            g = resolve_game(pathvar.get()); st["had"] = bool(g and installed_state(g) != "none")
            if st["had"]:
                lbl_state.config(text="目前狀態：%s　版本：%s" % ({"installed": "已安裝", "partial": "部分檔案不完整"}[installed_state(g)], (read_manifest(g) or {}).get("version", "?")))
                real_show("menu")
            else: st["action"].set("install"); goto_folder()
        elif p == "video":
            if auto.get() and not ffvar.get():
                ff = find_ffmpeg_auto()
                if ff: ffvar.set(ff); lbl_video.config(text="代勞模式：已自動找到 ffmpeg，要繁中化影片請選「同時繁中化影片」。", foreground="#060")
            real_show(p)
        else: real_show(p)

    def goto_folder():
        """代勞模式: when the game folder is found by itself, skip the folder page; fall back to the page if anything is wrong."""
        if auto.get() and resolve_game(pathvar.get()):
            start()
            if cur["page"] in ("disc", "menu"): real_show("folder")
        else: real_show("folder")

    def start():
        g = resolve_game(pathvar.get())
        if not g: lbl_folder.config(text="這不是有效的遊戲資料夾（資料夾名稱必須是 mgspw，或其上層的 MGS_PW）。"); return
        lbl_folder.config(text=""); st["game"] = g
        if st["action"].get() == "install": show_jp(g); return
        cur["busy"] = True; show("run")
        threading.Thread(target=worker, daemon=True).start()

    def start_run():
        st["ffmpeg"] = None
        if want_video.get() == "do":
            try:
                if not zhtw_movies: raise RuntimeError("此版本安裝程式沒有影片功能。")
                ff, _ = zhtw_movies.tools_from(ffvar.get()); zhtw_movies.check_ffmpeg(ff); st["ffmpeg"] = ff
            except Exception as e: lbl_video.config(text=str(e)); return
        cur["busy"] = True; show("run")
        threading.Thread(target=worker, daemon=True).start()

    def show_jp(g):
        st["jst"], _ = jp_status(g); st["pack"] = None; lbl_jp.config(text="")
        if st["jst"] == "installed":
            lbl_jp_head.config(text="✓ 已偵測到遊戲資料夾裡有日文語言包，不需要再指定。按「下一步」繼續。", foreground="#060")
            jp_entry.config(state="disabled"); jp_btn.config(state="disabled")
        else:
            jp_entry.config(state="normal"); jp_btn.config(state="normal")
            lbl_jp_head.config(text="遊戲資料夾裡還沒有日文語言包。請指定日文包資料夾，再按「下一步」。", foreground="#a00")
            if auto.get() and not jpvar.get():
                lbl_jp_head.config(text="代勞模式：正在尋找你的日文包資料夾（下載、桌面、USB／SD 卡…），請稍候…", foreground="gray")
                root.config(cursor="watch"); real_show("jp"); root.update()
                found = find_pack_auto(g); root.config(cursor="")
                if found:
                    jpvar.set(found); lbl_jp_head.config(text="代勞模式：已自動找到日文包資料夾，請確認後按「下一步」。", foreground="#060")
                else:
                    lbl_jp_head.config(text="遊戲資料夾裡還沒有日文語言包。", foreground="#a00")
                    lbl_jp.config(text="代勞模式：在下載資料夾、桌面、USB／SD 卡等位置都沒有找到日文包。請按「瀏覽…」手動指定。")
        show("jp")

    def jp_next():
        g = st["game"]
        if st.get("jst") == "installed":
            st["pack"] = None
            probs = check_game(g, payload, logf)
            if probs: lbl_jp.config(text="\n".join(probs[:4])); return
            ok, need, free = free_space_ok(g, payload)
        else:
            src, probs = resolve_pack(jpvar.get().strip().strip(chr(34)))
            if not src: lbl_jp.config(text="日文包資料夾驗證失敗：" + chr(10) + chr(10).join(probs[:5])); return
            ok, need, free = free_space_ok(g, payload, extra=sum(e["size"] for e in jp_list()))
            st["pack"] = src
        if not ok: st["pack"] = None; lbl_jp.config(text="磁碟空間不足：需要約 %d MB，可用 %d MB。" % (need >> 20, free >> 20)); return
        lbl_jp.config(text=""); lbl_video.config(text=""); show("video")

    def worker():
        err = None
        try:
            act = st["action"].get()
            if act == "remove": remove(st["game"], logf)
            elif act == "remove-all": remove(st["game"], logf); remove_jppack(st["game"], logf)
            else:
                if st.get("pack"): install_jppack(st["game"], st["pack"], logf, progf)
                install(st["game"], payload, logf, progf)
                if st.get("ffmpeg"):
                    try: zhtw_movies.install_movies(st["game"], st["ffmpeg"], logf, progf)
                    except Exception as e: st["video_err"] = str(e); logf("影片繁中化已略過（保持日文）：" + str(e))
        except Exception as e: err = str(e)
        def fin():
            cur["busy"] = False; endtxt.config(state="normal"); endtxt.delete("1.0", "end")
            if err: endtxt.insert("1.0", "發生錯誤：\n\n" + err + "\n\n沒有留下半完成的檔案（暫存檔已清除）。若問題持續，請至 GitHub Issues 回報並附上版本號 " + VERSION + "。")
            elif st["action"].get() == "remove": endtxt.insert("1.0", "繁中化包已移除，原本的檔案已還原。")
            elif st["action"].get() == "remove-all": endtxt.insert("1.0", "繁中化包與日文包已移除（日文包只移除由本程式複製的檔案）。")
            else:
                endtxt.insert("1.0", FINISH_TEXT % VERSION)
                if st.get("video_err"): endtxt.insert("end", chr(10) + chr(10) + "影片繁中化未完成（已保持日文影片）：" + chr(10) + st["video_err"])
            endtxt.config(state="disabled"); show("end")
        root.after(0, fin)

    btn_next.config(command=go_next); btn_back.config(command=go_back)
    show("disc")
    if args.selftest:
        for p in ("disc", "folder_or_menu", "menu", "folder", "jp", "video", "run", "end"): show(p); root.update()
        import tempfile
        auto.set(False); tmp = tempfile.mkdtemp(); g = os.path.join(tmp, "mgspw"); os.makedirs(g); st["game"] = g
        show_jp(g); root.update(); assert cur["page"] == "jp" and st["jst"] == "missing", "jp step must show when the pack is missing"
        want_video.set("do"); show("video"); root.update(); assert btn_next.cget("text") == "安裝", btn_next.cget("text")
        want_video.set("skip"); refresh(); root.update(); assert btn_next.cget("text") == "略過影片並安裝", btn_next.cget("text")
        assert str(ff_entry.cget("state")) == "disabled", "ffmpeg box must be disabled while skipping"
        shutil.rmtree(tmp, ignore_errors=True)
        root.destroy(); print("gui selftest ok"); return 0
    root.mainloop(); return 0


def _hide_console():
    """Frozen Windows build is a console program (so --cli works); hide its window when the wizard opens."""
    if sys.platform == "win32" and getattr(sys, "frozen", False):
        try:
            import ctypes
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd: ctypes.windll.user32.ShowWindow(hwnd, 0)
        except Exception: pass


def main():
    ap = argparse.ArgumentParser(description=APP)
    ap.add_argument("--cli", action="store_true"); ap.add_argument("--game"); ap.add_argument("--accept", action="store_true")
    ap.add_argument("--auto", action="store_true", help="代勞模式：自動找遊戲資料夾、日文包與 ffmpeg")
    ap.add_argument("--jppack"); ap.add_argument("--ffmpeg"); ap.add_argument("action", nargs="?", choices=["install", "remove", "remove-all", "status"]); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.cli or a.game or a.action:
        a.auto = a.auto or IS_LINUX; return cli(a)
    try: import tkinter  # noqa: F401
    except ImportError:
        print("找不到 tkinter（視窗元件），改用命令列模式。"); a.auto = a.auto or IS_LINUX; return cli(a)
    _hide_console()
    try: return gui(a)
    except Exception as e:
        try:
            import tkinter; from tkinter import messagebox
            r = tkinter.Tk(); r.withdraw(); messagebox.showerror(APP, "程式發生錯誤，請至 GitHub Issues 回報並附上版本號 %s：%s%s" % (VERSION, chr(10) * 2, e))
        except Exception: pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
