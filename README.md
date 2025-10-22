# 🐍 pyupgradecheck

Quickly see which of your installed packages are ready for your next Python version.

### Example

```sh
# Test it with a small number of packages
pyupgradecheck 3.13 --packages packaging httpx halo
```

```sh
# JSON output
... --json
```

```bash
# Test with all packages
pyupgradecheck 3.13
requests 2.32.3: supported (PyPI requires_python: >=3.7)
some-old-lib 1.2.0: incompatible (PyPI requires_python: <3.10)
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
