import subprocess
import sys
import os

os.chdir(r'd:\Coding\Finflow v2\finflow_v2')
result = subprocess.run([sys.executable, 'seed.py'], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)
print("Return code:", result.returncode)
