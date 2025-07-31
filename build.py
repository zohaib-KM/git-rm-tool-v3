#!/usr/bin/env python3

import subprocess
import os
import shutil
import sys

# Clean previous builds
print("Cleaning previous builds...")
for path in ['build', 'dist', 'git_rm_user.spec']:
    if os.path.exists(path):
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

# Build command
print("Building executable...")
cmd = [
    sys.executable,
    '-m',
    'PyInstaller',
    '--name=git-rm-user',
    '--onefile',
    '--clean',
    '--hidden-import=keyrings.alt.file',
    '--hidden-import=keyrings.alt.keyring',
    '--hidden-import=keyrings.alt',
    'git_rm_user.py'
]

# Run build
try:
    subprocess.run(cmd, check=True)
    print("\nBuild successful! Executable created at: dist/git-rm-user")
    print("\nTo install system-wide, run:")
    print("sudo cp dist/git-rm-user /usr/local/bin/")
except subprocess.CalledProcessError as e:
    print(f"Build failed: {e}")
    exit(1) 
