__version__ = "0.1.6"

from .checker import (check_environment, check_pkg_compatibility,
                      get_installed_packages)

__all__ = [
    "check_environment",
    "check_pkg_compatibility",
    "get_installed_packages",
]
