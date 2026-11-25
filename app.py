"""Streamlit Community Cloud giriş noktası.

Asıl uygulama: src/portfolio_models/web/app.py. Depodaki src/ klasörü sys.path'in başına eklenir; böylece
Cloud'un kurduğu paket kopyası yerine her zaman depodaki güncel kod çalışır.
"""

import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
runpy.run_path(str(ROOT / "src" / "portfolio_models" / "web" / "app.py"), run_name="__main__")
