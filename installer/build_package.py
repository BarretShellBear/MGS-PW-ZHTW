"""Developer tool: assemble the two distributable packages (Windows and SteamOS are separate) and zip them.

Windows : MGSPW_zhTW_<ver>_Windows/  = MGSPW_zhTW_Setup.exe (PyInstaller, no Python needed) + payload/ + licenses/ + README.txt + CHANGELOG.txt
SteamOS : MGSPW_zhTW_<ver>_SteamOS/  = Python sources + vendor/ + payload/ + licenses/ + steamos_install.sh + SteamOS教學.md + README.txt + CHANGELOG.txt
No game file and no Japanese-pack data is included (the payload only holds the changed blocks of the translation).
The exe is built once into installer/build_exe/ (kept between runs); pass --rebuild-exe to build it again.
Output: installer/dist/MGSPW_zhTW_<ver>_Windows(.zip) and installer/dist/MGSPW_zhTW_<ver>_SteamOS(.zip)     Usage: python build_package.py [--rebuild-exe]
"""
import os, re, shutil, subprocess, sys, zipfile
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ver = re.search(r'VERSION = "([^"]+)"', open(os.path.join(HERE, "zhtw_installer.py"), encoding="utf-8").read()).group(1).replace(" ", "_")
DIST = os.path.join(HERE, "dist"); os.makedirs(DIST, exist_ok=True)
EXE_NAME = "MGSPW_zhTW_Setup"
EXE_DIR = os.path.join(HERE, "build_exe")


def build_exe():
    exe = os.path.join(EXE_DIR, EXE_NAME + ".exe")
    if os.path.isfile(exe) and "--rebuild-exe" not in sys.argv: return exe
    work = os.path.join(EXE_DIR, "work"); os.makedirs(work, exist_ok=True)
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile", "--name", EXE_NAME, "--paths", os.path.join(HERE, "vendor"),
           "--hidden-import", "pwcrypt", "--hidden-import", "pwpaths", "--hidden-import", "zhtw_movies", "--hidden-import", "numpy",
           "--distpath", EXE_DIR, "--workpath", work, "--specpath", work, os.path.join(HERE, "zhtw_installer.py")]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.isfile(exe): print(r.stdout[-1500:], r.stderr[-1500:]); sys.exit("PyInstaller failed")
    return exe


def md_to_txt(t):
    """Plain-text version of a markdown document (the packages carry .txt files, not .md)."""
    out = []; hdr = False
    for line in t.split(chr(10)):
        s = line.rstrip()
        if s.startswith("---") and s.strip("-") == "": continue                               # front matter / rules
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells): hdr = False; continue            # separator row
            if not hdr and len(cells) >= 2 and not out[-1:] == ["@@table"]:
                pass
            out.append("  - " + " ： ".join(cells) if len(cells) > 1 else "  - " + cells[0]); continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            title = m.group(2); out.append(""); out.append(("【%s】" % title) if len(m.group(1)) <= 2 else ("◆ " + title)); continue
        s = re.sub(r"^>\s?", "", s)
        s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda mm: mm.group(1) if not mm.group(2).startswith("http") else "%s（%s）" % (mm.group(1), mm.group(2)), s)
        s = s.replace("**", "").replace("`", "")
        s = re.sub(r"^- \[ \]", "[ ]", s)
        out.append(s)
    txt = chr(10).join(out).replace("SteamOS教學.md", "SteamOS教學.txt").replace("README.md", "README.txt")
    return re.sub(r"(" + chr(10) + r"){3,}", chr(10) * 2, txt).strip() + chr(10)


def readme_for(kind):
    t = open(os.path.join(HERE, "README.md"), encoding="utf-8").read()
    if kind == "windows":
        lines = [l for l in t.split("\n") if not l.startswith("SteamOS（Steam Deck）：") and not l.startswith("9. （SteamOS 版）")]
        t = "\n".join(lines)
        t = t.replace("Windows：執行安裝程式，依畫面步驟", "執行 `MGSPW_zhTW_Setup.exe`（不需要安裝 Python），依畫面步驟")
        t = t.replace("命令列：`python zhtw_installer.py --cli`（`--auto` 為代勞模式，Linux／SteamOS 預設開啟；", "命令列：`MGSPW_zhTW_Setup.exe --cli`（`--auto` 為代勞模式；")
        t = t.replace(" SteamOS 另請註明設備型號與 SteamOS 版本。", "")
    else:
        lines = [l for l in t.split("\n") if not l.startswith("Windows：執行安裝程式") and not l.startswith("命令列：")]
        t = "\n".join(lines)
        t = t.replace("## 安裝\n", "## 安裝\n命令列：`python3 zhtw_installer.py --cli`（SteamOS 預設開啟代勞模式；可加 `--game`、`--jppack`、`--ffmpeg`、`--accept`；動作為 `install`、`remove`、`remove-all`、`status`）。\n", 1)
    return t


def changelog_for(kind):
    t = open(os.path.join(HERE, "CHANGELOG.txt"), encoding="utf-8").read()
    if kind == "windows": t = "\n".join(l for l in t.split("\n") if "SteamOS" not in l)
    return t


def fresh(name):
    out = os.path.join(DIST, name)
    if os.path.isdir(out): shutil.rmtree(out)
    os.makedirs(out); return out


def zipdir(out):
    zp = out + ".zip"
    if os.path.isfile(zp): os.remove(zp)
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_STORED) as z:          # payload is already zlib-compressed
        for d, _, fs in os.walk(out):
            for n in fs: z.write(os.path.join(d, n), os.path.relpath(os.path.join(d, n), os.path.dirname(out)))
    print("zip   : %s (%.1f MB)" % (zp, os.path.getsize(zp) / 1e6))


def common(out, kind):
    shutil.copytree(os.path.join(HERE, "payload"), os.path.join(out, "payload"), ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(HERE, "licenses"), os.path.join(out, "licenses"))
    open(os.path.join(out, "README.txt"), "w", encoding="utf-8-sig", newline="").write(md_to_txt(readme_for(kind)))
    open(os.path.join(out, "CHANGELOG.txt"), "w", encoding="utf-8", newline="").write(changelog_for(kind))


# ---- Windows
exe = build_exe()
w = fresh("MGSPW_zhTW_%s_Windows" % ver); common(w, "windows"); shutil.copyfile(exe, os.path.join(w, EXE_NAME + ".exe"))
zipdir(w)
# ---- SteamOS
s = fresh("MGSPW_zhTW_%s_SteamOS" % ver); common(s, "steamos")
for f in ("zhtw_installer.py", "zhtw_movies.py", "steamos_install.sh"): shutil.copyfile(os.path.join(HERE, f), os.path.join(s, f))
open(os.path.join(s, "SteamOS教學.txt"), "w", encoding="utf-8-sig", newline="").write(md_to_txt(open(os.path.join(HERE, "SteamOS教學.md"), encoding="utf-8").read()))
shutil.copytree(os.path.join(HERE, "vendor"), os.path.join(s, "vendor"), ignore=shutil.ignore_patterns("__pycache__"))
zipdir(s)
for old in ("MGSPW_zhTW_%s" % ver, "MGSPW_zhTW_%s.zip" % ver):          # the old combined package
    p = os.path.join(DIST, old)
    if os.path.isdir(p): shutil.rmtree(p)
    elif os.path.isfile(p): os.remove(p)
