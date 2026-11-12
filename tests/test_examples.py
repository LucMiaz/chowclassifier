"""The example script must run to completion."""
import os
import shutil
import subprocess
import sys


def test_all_examples(tmp_path):
    # Run a copy: example.py reads data/ and writes fig/ relative to its folder,
    # and the figures in the repository should not be overwritten by tests.
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    example_dir = tmp_path / "example"
    shutil.copytree(os.path.join(repo_root, "example"), example_dir,
                    ignore=shutil.ignore_patterns("fig", ".ipynb_checkpoints"))
    (example_dir / "fig").mkdir()
    env = {**os.environ, "MPLBACKEND": "Agg"}
    # (os.system's exit status used to be ignored, so this test could not fail)
    proc = subprocess.run([sys.executable, "example.py"], cwd=example_dir, env=env,
                          capture_output=True, text=True, timeout=900, check=False)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert any(p.suffix == ".png" for p in (example_dir / "fig").iterdir())
