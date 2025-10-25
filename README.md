# 🐍 pyupgradecheck

[![PyPI](https://img.shields.io/pypi/v/pyupgradecheck.svg)](https://pypi.org/project/pyupgradecheck/)
[![CI](https://github.com/tdiprima/pyupgradecheck/workflows/CI/badge.svg)](https://github.com/tdiprima/pyupgradecheck/actions)

<img src="https://raw.githubusercontent.com/tdiprima/pyupgradecheck/refs/heads/main/logo.png" width="700">

> 💡 **Check your Python packages before you upgrade.**
> Find out which of your dependencies are ready for your next Python version — and which ones might ruin your day.

## 🚀 Installation

```bash
pip install pyupgradecheck
```

## ⚡️ Quickstart

```bash
# Test all installed packages
pyupgradecheck 3.14
```

**Example Output:**

```
requests 2.32.3: supported (PyPI requires_python: >=3.7)
some-old-lib 1.2.0: incompatible (PyPI requires_python: <3.10)
```

## 🧰 CLI Examples

```bash
# Check specific packages
pyupgradecheck 3.14 --packages packaging httpx halo
# or short form:
pyupgradecheck 3.14 --p packaging httpx halo
```

```bash
# Check a requirements.txt file
pyupgradecheck 3.14 --requirements requirements.txt
# or short form:
pyupgradecheck 3.14 -r requirements.txt
```

```bash
# Perfect for CI
pyupgradecheck 3.14 --json > compat-report.json
```

## 💬 CLI Help

```bash
pyupgradecheck --help
```

## 🤔 Why pyupgradecheck?

Because upgrading Python shouldn't be a trust fall.  
Quickly see which of your installed packages can handle your target Python version — before you break your dev environment or CI build.

## ❤️ Contributing

Pull requests welcome 💖  
Run tests with:

```bash
pytest
```

## 🧩 Perfect for

* 🧪 CI/CD pipelines
* 🐍 Devs upgrading their local environments
* 🧠 Maintainers checking project compatibility

<br>
