#!/usr/bin/env python3
"""
Synchronize dependencies from pyproject.toml to requirements.txt
This ensures both files stay in sync and prevents safety hook conflicts.
"""

import tomllib
from pathlib import Path


def sync_dependencies():
    """Read pyproject.toml and generate requirements.txt from it."""

    # Read pyproject.toml
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        print("Error: pyproject.toml not found")
        return False

    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)

    # Extract dependencies
    dependencies = pyproject.get("project", {}).get("dependencies", [])
    dev_dependencies = (
        pyproject.get("project", {}).get("optional-dependencies", {}).get("dev", [])
    )

    # Write requirements.txt
    with open("requirements.txt", "w") as f:
        f.write("# Core dependencies (auto-generated from pyproject.toml)\n")
        f.write("# DO NOT EDIT MANUALLY - use: python scripts/sync-dependencies.py\n")
        for dep in dependencies:
            f.write(f"{dep}\n")

        if dev_dependencies:
            f.write("\n# Development dependencies\n")
            for dep in dev_dependencies:
                f.write(f"{dep}\n")

    print(
        f"✅ Synchronized {len(dependencies)} core + {len(dev_dependencies)} dev dependencies"
    )
    print("   from pyproject.toml to requirements.txt")

    # Also create a requirements-dev.txt for clarity
    with open("requirements-dev.txt", "w") as f:
        f.write("# Development dependencies (auto-generated from pyproject.toml)\n")
        f.write("-r requirements.txt\n")  # Include base requirements
        for dep in dev_dependencies:
            f.write(f"{dep}\n")

    return True


if __name__ == "__main__":
    sync_dependencies()
