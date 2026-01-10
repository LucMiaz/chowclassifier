# Building and Installing ChowClassifier with Conda

This guide explains how to build and install the chowclassifier package using conda/mamba.

## Prerequisites

Install conda-build:
```bash
conda install conda-build
# or
mamba install conda-build
```

## Building the Package

### Option 1: Build from local source

From the root directory of the project:

```bash
conda build recipe/
# or
mamba build recipe/
```

### Option 2: Build and install in one step

```bash
conda develop .
# or install in editable mode with pip in the conda environment
pip install -e .
```

## Installing the Built Package

After building, install the package:

```bash
conda install --use-local chowclassifier
# or
mamba install --use-local chowclassifier
```

## Creating a Conda Environment with ChowClassifier

You can also create a new environment and install the package:

```bash
# Create environment from environment.yml
conda env create -f environment.yml
conda activate chow

# Install the package
pip install -e .
```

Or create from scratch:

```bash
conda create -n chow python=3.10
conda activate chow
pip install -e .
```

## Uploading to Anaconda Cloud (Optional)

To share the package on Anaconda Cloud:

1. Create an account at https://anaconda.org
2. Install anaconda-client:
   ```bash
   conda install anaconda-client
   ```
3. Login:
   ```bash
   anaconda login
   ```
4. Upload:
   ```bash
   anaconda upload /path/to/built/package.tar.bz2
   ```

The built package location will be shown after `conda build` completes.

## Testing the Installation

After installation, test that it works:

```bash
python -c "import chowclassifier; print(chowclassifier.__version__)"
chowclassifier --help
```

## Troubleshooting

### Build fails with missing dependencies
Make sure all build dependencies are installed in your base/build environment.

### Module not found after installation
Ensure you've activated the correct conda environment where the package was installed.

### Version conflicts
If you encounter version conflicts, try creating a fresh environment:
```bash
conda create -n chow_test python=3.10
conda activate chow_test
conda install --use-local chowclassifier
```
