import subprocess


def test_help():
    assert subprocess.call(['python', '-m', 'pyimorg', '--help']) == 0
    assert subprocess.call(['pyimorg', '--help']) == 0
