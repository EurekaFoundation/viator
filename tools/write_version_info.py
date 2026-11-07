"""Scrive packaging/windows/version_info.txt (dettagli del file .exe) con la versione attuale."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from viator import APP_NAME, APP_VERSION  # noqa: E402

parts = [int(p) for p in APP_VERSION.split(".")] + [0] * 4
v = tuple(parts[:4])
text = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={v}, prodvers={v}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('041004B0', [
      StringStruct('CompanyName', 'Eureka Foundation'),
      StringStruct('FileDescription', '{APP_NAME} - browser web libero'),
      StringStruct('FileVersion', '{APP_VERSION}'),
      StringStruct('InternalName', '{APP_NAME}'),
      StringStruct('LegalCopyright', 'GPL-3.0'),
      StringStruct('OriginalFilename', '{APP_NAME}.exe'),
      StringStruct('ProductName', '{APP_NAME}'),
      StringStruct('ProductVersion', '{APP_VERSION}')])]),
    VarFileInfo([VarStruct('Translation', [0x0410, 1200])])
  ]
)
"""
path = os.path.join(ROOT, "packaging", "windows", "version_info.txt")
with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("Scritto", path)
