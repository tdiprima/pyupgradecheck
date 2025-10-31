# test_requirements.txt

This comprehensive test file demonstrates all the different requirement formats that `pyupgradecheck` can parse.

## Features Tested

### Basic Package Formats
- Simple package names: `requests`, `flask`, `numpy`
- Exact version pins: `pandas==2.0.0`
- Minimum versions: `httpx>=0.24.0`
- Version ranges: `scipy>=1.10.0,<2.0.0`
- Compatible release: `django~=4.2.0`
- Less than constraints: `pillow<10.0.0`
- Not equal constraints: `six!=1.11.0,>=1.10.0`

### Advanced Features
- **Extras**: `requests[security]>=2.25.0` → extracts `requests`
- **Environment markers**: `importlib-metadata>=4.0.0; python_version < "3.8"`
- **Comments**: Full-line and inline comments are properly ignored
- **Whitespace**: Handles leading/trailing whitespace
- **Case variations**: `Django`, `PILLOW`, `NumPy`

### Properly Skipped Formats
- **Git URLs**: `git+https://github.com/user/repo.git`
- **HTTP/HTTPS URLs**: `https://example.com/package.whl`
- **Editable installs**: `-e .` or `-e git+...`
- **VCS with eggs**: `git+https://...#egg=Package`
- **Comments**: Lines starting with `#`

## Usage

Test with the parser:
```bash
python -c "
from pyupgradecheck.checker import parse_requirements_file
packages = parse_requirements_file('test_requirements.txt')
print(f'Found {len(packages)} packages')
"
```

Run the test suite:
```bash
pytest tests/test_basic.py::TestParseRequirementsFile::test_comprehensive_requirements_file -v
```

## Validation

The parser successfully extracts 41 valid package names from this file while:
- Skipping all git+, http://, and https:// URLs
- Skipping all -e editable installs
- Ignoring all comments
- Handling all version specifier formats
- Extracting base package names from extras notation
