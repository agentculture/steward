"""steward — aligns and maintains resident agents across Culture projects."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _v

try:
    __version__ = _v("steward-cli")
except PackageNotFoundError:
    __version__ = "0.0.0+local"

__all__ = ["__version__"]
