"""Chow classifier package for time-series trend classification."""

# __init__.py

try:
    # Single source of truth: the version in pyproject.toml.
    from importlib.metadata import PackageNotFoundError as _PNF, version as _version
    __version__ = _version("chowclassifier")
except _PNF:  # imported from a source tree that was never installed
    __version__ = "unknown"

from chowclassifier.chow import Chow
from chowclassifier.chewdata import ChewData
# chowclassifier.bayes (BayesChow) is optional and imported on demand: it needs PyMC
# (pip install chowclassifier[bayes])
