import subprocess


def test_help():
    assert subprocess.call(['python', '-m', 'pyimorg', 'groupby', '--help']) == 0
    assert subprocess.call(['pyimorg', 'groupby', '--help']) == 0
