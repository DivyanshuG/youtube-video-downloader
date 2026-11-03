# PyInstaller spec for the macOS app bundle (YouTube Video Downloader.app). Windows uses Sonica.spec.
from pathlib import Path
import os
import re
from PyInstaller.utils.hooks import collect_all, copy_metadata

src = Path(SPECPATH)
version = re.search(r"VERSION\s*=\s*'([^']+)'", (src / 'branding.py').read_text(encoding='utf-8')).group(1)
bin_dir = Path(os.environ.get('SONIKA_BIN_DIR', src / 'build-bin'))
icon = os.environ.get('SONIKA_ICON')

datas = [(str(src / 'README.md'), '.'), (str(src / 'assets'), 'assets')] + copy_metadata('mcp')
# Helper tools (ffmpeg, ffprobe, node, cloudflared) are copied as plain files so PyInstaller leaves them untouched.
if bin_dir.is_dir():
    datas += [(str(tool), 'bin') for tool in sorted(bin_dir.iterdir()) if tool.is_file()]
binaries, hiddenimports = [], []
for module in ('yt_dlp', 'yt_dlp_ejs'):
    found = collect_all(module)
    datas += found[0]; binaries += found[1]; hiddenimports += found[2]

a = Analysis([str(src / 'app.py')], pathex=[str(src)], binaries=binaries, datas=datas, hiddenimports=hiddenimports,
             hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=['pytest'], noarchive=False, optimize=0)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Sonika', debug=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False, argv_emulation=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='Sonika')
app = BUNDLE(coll, name='YouTube Video Downloader.app', icon=icon, bundle_identifier='com.mehulsoni.sonika',
             version=version,
             info_plist={'CFBundleName': 'YouTube Video Downloader', 'CFBundleDisplayName': 'YouTube Video Downloader',
                         'CFBundleShortVersionString': version, 'NSHighResolutionCapable': True,
                         'LSMinimumSystemVersion': '11.0'})
