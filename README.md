# 🐍 pyupgradecheck

[![PyPI](https://img.shields.io/pypi/v/pyupgradecheck.svg)](https://pypi.org/project/pyupgradecheck/)
[![CI](https://github.com/tdiprima/pyupgradecheck/workflows/CI/badge.svg)](https://github.com/tdiprima/pyupgradecheck/actions)

<img src="https://raw.githubusercontent.com/tdiprima/pyupgradecheck/refs/heads/main/logo.png" width="700">

Quickly see which of your installed packages are ready for your next Python version.

### Example

```bash
# Test with all packages
pyupgradecheck 3.13

# Example Output:
# requests 2.32.3: supported (PyPI requires_python: >=3.7)
# some-old-lib 1.2.0: incompatible (PyPI requires_python: <3.10)
```

```sh
# Test it with a small number of packages
pyupgradecheck 3.13 --packages packaging httpx halo
```

```sh
# Run this before your next CI upgrade
pyupgradecheck 3.14 --json > compat-report.json
```

### Install

```bash
pip install pyupgradecheck
```

### Use programmatically

```python
from pyupgradecheck import check_environment
print(check_environment("3.13"))
```

### CLI help

```bash
pyupgradecheck --help
```

### Contributing
PRs welcome 💖 — run tests with:

```bash
pytest
```
