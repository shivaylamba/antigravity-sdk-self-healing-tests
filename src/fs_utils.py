import os
import json
import pathlib
from typing import Any, Optional

def read_text_if_exists(path: str) -> Optional[str]:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    except Exception:
        pass
    return None

def read_json_if_exists(path: str) -> Optional[Any]:
    text = read_text_if_exists(path)
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None

def write_json(path: str, data: Any) -> None:
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

def path_exists(path: str) -> bool:
    return os.path.exists(path)

def resolve_from(cwd: str, path: str) -> str:
    return os.path.abspath(os.path.join(cwd, path))
