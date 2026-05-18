import importlib
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


def test_main_modules_are_importable():
    modules = [
        "sotto_soglia",
        "sotto_soglia.config",
        "sotto_soglia.models",
        "sotto_soglia.deck",
        "sotto_soglia.rules",
        "sotto_soglia.round",
        "sotto_soglia.game",
        "sotto_soglia.strategies",
        "sotto_soglia.simulation",
        "sotto_soglia.statistics",
        "sotto_soglia.exporters",
        "sotto_soglia.cli",
    ]

    for module_name in modules:
        assert importlib.import_module(module_name)
