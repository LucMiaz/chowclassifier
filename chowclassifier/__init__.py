"""Chow classifier package for time-series trend classification."""

# __init__.py

# Version of the chowclassifier package
__version__ = "2.0.0"
from chowclassifier.chow import Chow
from chowclassifier.chewdata import ChewData
# chowclassifier.bayes (BayesChow) is optional and imported on demand: it needs PyMC
# (pip install chowclassifier[bayes])
