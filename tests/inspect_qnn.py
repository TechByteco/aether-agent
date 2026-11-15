import sys, os
from pathlib import Path

site_packages = Path(sys.executable).parent.parent / "Lib" / "site-packages"
qnn_dirs = list(site_packages.glob("*qnn*"))
print("QNN dirs:", [d.name for d in qnn_dirs])
for d in qnn_dirs:
    if d.is_dir():
        dlls = list(d.rglob("*.dll"))
        print(f"  DLLs in {d.name}: {[dll.name for dll in dlls[:10]]}")
