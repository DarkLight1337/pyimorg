import subprocess


def test_help():
    assert subprocess.call(['python', '-m', 'pyimorg', 'diff', '--help']) == 0
