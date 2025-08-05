#!/usr/bin/env python3
import os
import shutil
import sys

print("Starting cleanup...")

# Change to project directory
os.chdir(r"C:\Users\picasso\PycharmProjects\6-nemo-ai")

# Remove the root prompts directory
try:
    if os.path.exists("prompts"):
        shutil.rmtree("prompts")
        print("✓ Removed root prompts/ directory")
    else:
        print("- Root prompts/ directory not found")
except Exception as e:
    print(f"✗ Failed to remove prompts/: {e}")

# Remove app/prompts/old
try:
    if os.path.exists("app/prompts/old"):
        shutil.rmtree("app/prompts/old")
        print("✓ Removed app/prompts/old/ directory")
    else:
        print("- app/prompts/old/ directory not found")
except Exception as e:
    print(f"✗ Failed to remove app/prompts/old/: {e}")

# Remove app/prompts/shared  
try:
    if os.path.exists("app/prompts/shared"):
        shutil.rmtree("app/prompts/shared")
        print("✓ Removed app/prompts/shared/ directory")
    else:
        print("- app/prompts/shared/ directory not found")
except Exception as e:
    print(f"✗ Failed to remove app/prompts/shared/: {e}")

# Clean up temp files
temp_files = ["cleanup_dirs.py", "test_prompt_loading.py", "verify_setup.py", "test_prompt_fix.py"]
for f in temp_files:
    try:
        if os.path.exists(f):
            os.remove(f)
            print(f"✓ Removed temp file: {f}")
    except Exception as e:
        print(f"✗ Failed to remove {f}: {e}")

print("\n=== Final Directory Structure ===")
if os.path.exists("app/prompts"):
    print("app/prompts contents:")
    for item in os.listdir("app/prompts"):
        path = os.path.join("app/prompts", item)
        if os.path.isdir(path):
            print(f"  [DIR] {item}")
        else:
            print(f"  [FILE] {item}")

print("\nCleanup complete!")
