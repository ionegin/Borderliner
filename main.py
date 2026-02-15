#!/usr/bin/env python3
print("🚀 MAIN.PY STARTED - HF should use this file!")

# Запускаем наш app.py
import subprocess
import sys

try:
    print("🔄 Starting app.py via subprocess...")
    result = subprocess.run([sys.executable, "app.py"], check=True)
    print(f"✅ app.py exited with code: {result.returncode}")
    print("🔄 subprocess completed")
except Exception as e:
    print(f"❌ Failed to run app.py: {e}")

print("🔄 main.py execution finished")
