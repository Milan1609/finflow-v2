#!/usr/bin/env python
import sys
import os

# Add the app directory to path
sys.path.insert(0, r'D:\Coding\Finflow v2\finflow_v2')
os.chdir(r'D:\Coding\Finflow v2\finflow_v2')

try:
    print("Importing seed module...")
    import seed
    print("SUCCESS: Seed data loaded!")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
