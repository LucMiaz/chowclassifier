# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
import sphinx_bootstrap_theme
# The repository root, so that 'import chowclassifier' works without installing.
sys.path.insert(0, os.path.abspath('..'))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'chowclassifier'
copyright = '2023-2026, Luc T Miaz'
author = 'Luc T Miaz'
# Read the version from the installed package metadata (RTD installs the
# package), so the docs cannot drift from pyproject.toml again.
try:
    from importlib.metadata import version as _pkg_version
    release = _pkg_version('chowclassifier')
except Exception:  # building from a checkout that was never installed
    release = 'unknown'
version = release

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.builders.linkcheck',
    'sphinx.ext.autosummary']

templates_path = ['_templates']
exclude_patterns = ['build', 'Thumbs.db', '.DS_Store']




# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
#html_theme =  "sphinx_documatt_theme"
html_theme = 'bootstrap'
html_theme_path = sphinx_bootstrap_theme.get_html_theme_path()

# html_sidebars = {
#     '**': ['globaltoc.html', 'sourcelink.html', 'searchbox.html'],
#             'modules/chow': ['index.html','modules.html','chow'],
# }
# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ['_static']
