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

## ⚙️ CLI Options Explained

### 🧩 `--packages` / `-p`
Manually specify one or more packages to check instead of scanning everything installed.

```bash
pyupgradecheck 3.14 --packages requests pandas httpx
# or short form:
pyupgradecheck 3.14 -p requests pandas httpx
```

Useful when you just want to sanity-check a few libs before doing a full environment sweep.

### 📦 `--requirements` / `-r`

Check packages listed in a `requirements.txt` file.

```bash
pyupgradecheck 3.14 --requirements requirements.txt
# or short form:
pyupgradecheck 3.14 -r requirements.txt
```

Great for CI pipelines or testing a project's dependency file without needing a full virtualenv.

### 💾 `--json`

Emit results in JSON instead of human-readable text.

```bash
pyupgradecheck 3.14 --json > compat-report.json
```

Perfect for CI/CD jobs or when you want to post-process results with another tool.

### 🧠 `--strict`

Be extra cautious — only marks a package as **supported** if *both* PyPI metadata
(`requires_python`) **and** package classifiers agree on the target Python version.

```bash
pyupgradecheck 3.14 --strict
```

This reduces false positives from packages that *claim* support but might not actually work yet.
If either data source disagrees or is missing, the status will be `"unknown"`.

### ⚗️ Combo Examples

```bash
# Check just a few packages, strict mode, JSON output
pyupgradecheck 3.14 -p fastapi uvicorn pydantic --strict --json

# Check all from requirements.txt, strict mode
pyupgradecheck 3.14 -r requirements.txt --strict
```

## 💬 CLI Help

```bash
pyupgradecheck --help
```

## 🤔 Why pyupgradecheck?

Because upgrading Python shouldn't be a trust fall.  
Quickly see which of your installed packages can handle your target Python version — before you break your dev environment or CI build.

## ⚠️ Disclaimer

`pyupgradecheck` checks **declared compatibility**, not guaranteed runtime behavior.

It uses metadata from PyPI (`requires_python`) and package classifiers
to estimate whether a library supports your target Python version.

That means:

- Some packages may *say* they support Python 3.13+, but still fail at runtime.
- C-extension builds, dependency pins, or missing wheels might break your install.
- Metadata may lag behind reality (maintainers forget to update it).

Always test your environment in a virtualenv before upgrading production systems.
This tool gives you a **heads-up**, not a promise. 😅

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

<!--
pip install -e ".[dev]"
pytest tests/test_basic.py -v
python -m pytest tests/test_basic.py -v --tb=line -k "requirements"
-->
