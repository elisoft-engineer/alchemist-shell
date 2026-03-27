import importlib
import pkgutil
import sys
import inspect
from pathlib import Path
from typing import Any, Dict, Type

def discover_models(start_dir: str = ".") -> Dict[str, Type[Any]]:
    """
    Dynamically discovers SQLAlchemy models in the project root.
    """
    path: Path = Path(start_dir).resolve()
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
    
    found_models: Dict[str, Type[Any]] = {}
    ignored_patterns: list[str] = ["venv", "tests", "__pycache__", "alembic"]

    for _, module_name, _ in pkgutil.walk_packages([str(path)]):
        if any(p in module_name for p in ignored_patterns):
            continue
            
        try:
            module = importlib.import_module(module_name)
            for _, obj in inspect.getmembers(module):
                # Identify models by the __tablename__ convention
                if inspect.isclass(obj) and hasattr(obj, "__tablename__"):
                    if obj.__module__.startswith("sqlalchemy"):
                        continue
                    found_models[obj.__name__] = obj
        except (ImportError, AttributeError):
            continue
            
    return found_models