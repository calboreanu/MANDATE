"""
Schema loading utilities.

Schemas are packaged with the mandate module and loaded via importlib.resources
for reliable access regardless of installation method (editable, wheel, sdist).
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict

if sys.version_info >= (3, 11):
    from importlib.resources import files
else:
    from importlib_resources import files  # type: ignore


def load_schema(name: str) -> Dict[str, Any]:
    """
    Load a JSON schema by name from the packaged schemas directory.
    
    Args:
        name: Schema filename (e.g., "mandate-as-code.schema.json")
        
    Returns:
        Parsed JSON schema as a dictionary
        
    Raises:
        FileNotFoundError: If schema doesn't exist
    """
    try:
        schema_text = (files("mandate") / "schemas" / name).read_text(encoding="utf-8")
        return json.loads(schema_text)
    except FileNotFoundError:
        raise FileNotFoundError(f"Schema not found: {name}")
    except Exception as e:
        raise FileNotFoundError(f"Failed to load schema {name}: {e}")


def list_schemas() -> list[str]:
    """List available schema files."""
    try:
        schemas_dir = files("mandate") / "schemas"
        return [f.name for f in schemas_dir.iterdir() if f.name.endswith(".json")]
    except Exception:
        return []
