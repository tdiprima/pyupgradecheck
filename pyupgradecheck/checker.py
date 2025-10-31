from __future__ import annotations
import re
import time
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
        name = d.metadata.get("Name") or d.metadata.get("name")
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
        return data.get("info", {}).get("requires_python")
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
    pkg: str, installed_version: str, target_python: str, strict: bool = False
) -> Tuple[str, str, str]:
    """
    Returns (status, details, source)
    status in {"supported", "incompatible", "unknown"}

    NOTE: This only checks declared metadata, not verified runtime behavior.
    """
    # 1️⃣ Try PyPI metadata first
    req = fetch_pypi_requires_python(pkg)
    spec = parse_requires_python(req)
    pypi_status = None
    pypi_source = None

    if spec is not None:
        try:
            target_v = Version(target_python)
        except InvalidVersion:
            return ("unknown", f"invalid target python version: {target_python}", "none")

        if target_v in spec:
            pypi_status = "supported"
        else:
            pypi_status = "incompatible"
        pypi_source = f"PyPI requires_python: {req}"

        # Flag overly broad claims like '>=3.6'
        if ">=" in req and len(req) < 8:
            pypi_status = "unknown"
            pypi_source += " (declared too broadly)"

    # 2️⃣ Fallback: check local metadata classifiers
    classifier_status = None
    classifier_source = None
    try:
        dist = importlib_metadata.distribution(pkg)
        classifiers = dist.metadata.get_all("Classifier") or []
        py_classifiers = [
            c for c in classifiers if c.startswith("Programming Language :: Python ::")
        ]
        if py_classifiers:
            for c in py_classifiers:
                ver = c.split("::")[-1].strip()
                if ver == target_python or ver.startswith(target_python.split(".")[0]):
                    classifier_status = "supported"
                    classifier_source = f"classifier: {c}"
                    break
            if classifier_source is None:
                classifier_status = "unknown"
                classifier_source = f"classifiers found but no match: {py_classifiers}"
    except importlib_metadata.PackageNotFoundError:
        pass

    # 3️⃣ Combine results
    if strict:
        if pypi_status == "supported" and classifier_status == "supported":
            return ("supported", f"both PyPI + classifier match", "strict")
        elif pypi_status or classifier_status:
            return ("unknown", "partial metadata match under strict mode", "strict")
    else:
        if pypi_status:
            return (pypi_status, pypi_source, "PyPI")
        elif classifier_status:
            return (classifier_status, classifier_source, "classifier")

    return ("unknown", "no metadata found", "none")


def parse_requirements_file(requirements_path: str) -> List[str]:
    """Parse a requirements.txt and extract package names."""
    packages = []
    path = Path(requirements_path)
    if not path.exists():
        raise FileNotFoundError(f"Requirements file not found: {requirements_path}")

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith(("git+", "http", "-e")):
                continue
            match = re.match(r"^([a-zA-Z0-9_.-]+)", line)
            if match:
                packages.append(match.group(1))
    return packages


def check_environment(
    target_python: str,
    packages: Optional[List[str]] = None,
    strict: bool = False,
) -> Dict[str, Dict]:
    pkgs = get_installed_packages()
    if packages:
        pkgs = {k: pkgs.get(k, "unknown") for k in packages}
    report = {}
    for name, ver in pkgs.items():
        status, details, source = check_pkg_compatibility(name, ver, target_python, strict)
        report[name] = {"version": ver, "status": status, "details": details, "source": source}
    return report
