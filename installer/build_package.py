"""Developer tool: assemble the distributable folder (and a zip) from the installer sources.

Contents: zhtw_installer.py, zhtw_movies.py, vendor/ (pwcrypt, pwpaths), payload/ (patches, lists, subtitles), licenses/, README.md,
CHANGELOG.txt, steamos_install.sh.  No game file and no Japanese-pack data is included (the payload only holds the changed blocks of the
translation).  A Windows .exe needs PyInstaller (not downloaded without Barret's approval); until then the package runs with Python 3.
Output: installer/dist/MGSPW_zhTW_<version>/ and installer/dist/MGSPW_zhTW_<version>.zip     Usage: python build_package.py
"""
import os, re, shutil, sys, zipfile
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ver = re.search(r'VERSION = "([^"]+)"', open(os.path.join(HERE, "zhtw_installer.py"), encoding="utf-8").read()).group(1).replace(" ", "_")
out = os.path.join(HERE, "dist", "MGSPW_zhTW_" + ver)
if os.path.isdir(out): shutil.rmtree(out)
os.makedirs(out)
for f in ("zhtw_installer.py", "zhtw_movies.py", "README.md", "CHANGELOG.txt", "steamos_install.sh", "SteamOS教學.md"): shutil.copyfile(os.path.join(HERE, f), os.path.join(out, f))
for d in ("vendor", "payload", "licenses"): shutil.copytree(os.path.join(HERE, d), os.path.join(out, d), ignore=shutil.ignore_patterns("__pycache__"))
with open(os.path.join(out, "run_windows.bat"), "w", encoding="utf-8", newline="\r\n") as f:
    f.write("@echo off\r\ncd /d %~dp0\r\npy -3 zhtw_installer.py || python zhtw_installer.py\r\npause\r\n")
zp = out + ".zip"
with zipfile.ZipFile(zp, "w", zipfile.ZIP_STORED) as z:           # payload is already zlib-compressed
    for d, _, fs in os.walk(out):
        for n in fs: z.write(os.path.join(d, n), os.path.relpath(os.path.join(d, n), os.path.dirname(out)))
print("folder:", out); print("zip   : %s (%.1f MB)" % (zp, os.path.getsize(zp) / 1e6))
