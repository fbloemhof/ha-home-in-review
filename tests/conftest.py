"""Load the integration's pure modules (no Home Assistant needed) as package ``hir``."""
import importlib
import sys
import types
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent / "custom_components" / "home_in_review"
pkg = types.ModuleType("hir")
pkg.__path__ = [str(PKG)]
sys.modules.setdefault("hir", pkg)
for name in ("const", "i18n", "weather", "collector", "render"):
    importlib.import_module(f"hir.{name}")
