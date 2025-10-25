from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx

try:
    from importlib import metadata as importlib_metadata
except Exception:
    import importlib_metadata

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

PYPI_JSON_URL = "https://pypi.org/pypi/{pkg}/json"


def get_installed_packages() -> Dict[str, str]:
    """Return mapping package_name -> version (from importlib.metadata)."""
    pkgs = {}
    for d in importlib_metadata.distributions():
        name = (
            d.metadata["Name"] if "Name" in d.metadata else d.metadata.get("name", None)
        )
        if not name:
            continue
        try:
            ver = d.version
        except Exception:
            ver = "unknown"
        pkgs[name] = ver
    return pkgs


def fetch_pypi_requires_python(pkg: str, timeout: int = 5) -> Optional[str]:
    """Query PyPI JSON for requires_python string, return None on error."""
    url = PYPI_JSON_URL.format(pkg=pkg)
    try:
        response = httpx.get(url, timeout=timeout, follow_redirects=True)
        response.raise_for_status()
        data = response.json()
        info = data.get("info", {})
        return info.get("requires_python")
    except httpx.HTTPStatusError:
        return None
    except Exception:
        return None


def parse_requires_python(spec: Optional[str]) -> Optional[SpecifierSet]:
    if not spec:
        return None
    try:
        return SpecifierSet(spec)
    except InvalidSpecifier:
        return None


def check_pkg_compatibility(
    pkg: str, installed_version: str, target_python: str
) -> Tuple[str, Optional[str]]:
    """
    Returns (status, details)
    status in {"supported", "incompatible", "unknown"}
    """
    # 1) try PyPI
    req = fetch_pypi_requires_python(pkg)
    spec = parse_requires_python(req)
    if spec is not None:
        # packaging accepts versions like '>=3.9'
        try:
            target_v = Version(target_python)
        except InvalidVersion:
            return ("unknown", f"invalid target python version: {target_python}")
        if target_v in spec:
            return ("supported", f"PyPI requires_python: {req}")
        else:
            return ("incompatible", f"PyPI requires_python: {req}")
    # 2) fallback: check local metadata classifiers
    try:
        dist = importlib_metadata.distribution(pkg)
        classifiers = dist.metadata.get_all("Classifier") or []
        # look for 'Programming Language :: Python :: 3.10' pattern
        py_classifiers = [
            c for c in classifiers if c.startswith("Programming Language :: Python ::")
        ]
        if py_classifiers:
            # crude parse: if any classifier matches the major.minor of target -> supported
            for c in py_classifiers:
                parts = c.split("::")
                ver = parts[-1].strip()
                if ver == target_python or ver.startswith(target_python.split(".")[0]):
                    return ("supported", f"classifier: {c}")
            return (
                "unknown",
                f"classifiers found but no exact match: {py_classifiers}",
            )
    except importlib_metadata.PackageNotFoundError:
        pass
    # 3) unknown
    return ("unknown", "no metadata found")


def parse_requirements_file(requirements_path: str) -> List[str]:
    """
    Parse a requirements.txt file and extract package names.
    Handles lines like:
    - requests>=2.0
    - flask==1.1.2
    - numpy<1.20
    - pandas
    - # comments
    - git+https://...

    Returns a list of package names (without version specifiers).
    """
    packages = []
    path = Path(requirements_path)

    if not path.exists():
        raise FileNotFoundError(f"Requirements file not found: {requirements_path}")

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Skip git/url dependencies
            if line.startswith(("git+", "http://", "https://", "-e")):
                continue

            # Extract package name (everything before version specifiers)
            # Match package name up to <, >, =, [, or whitespace
            match = re.match(r"^([a-zA-Z0-9_-]+)", line)
            if match:
                packages.append(match.group(1))

    return packages


def check_environment(
    target_python: str, packages: Optional[List[str]] = None
) -> Dict[str, Dict]:
    pkgs = get_installed_packages()
    if packages:
        pkgs = {k: pkgs.get(k, "unknown") for k in packages}
    report = {}
    for name, ver in pkgs.items():
        status, details = check_pkg_compatibility(name, ver, target_python)
        report[name] = {"version": ver, "status": status, "details": details}
    return report
