import os
def test_all_examples():
    REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
    example_dir = os.path.join(REPO_ROOT, 'example')
    os.system(f"python {os.path.join(example_dir, 'example.py')}")