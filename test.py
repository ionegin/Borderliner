#!/usr/bin/env python3
print("🔥 TEST.PY STARTED - MINIMAL VERSION")

import sys
print(f"🔧 Python version: {sys.version}")

try:
    import os
    print("✅ os imported")
except Exception as e:
    print(f"❌ os import failed: {e}")

try:
    import asyncio
    print("✅ asyncio imported")
except Exception as e:
    print(f"❌ asyncio import failed: {e}")

try:
    from aiohttp import web
    print("✅ aiohttp imported")
except Exception as e:
    print(f"❌ aiohttp import failed: {e}")

print("🔥 TEST.PY FINISHED SUCCESSFULLY")
