#!/usr/bin/env python3

print("Testing individual module path import...")

import sys
import os

# Add the presidio_fastapi directory to the path
presidio_path = os.path.join(os.getcwd(), 'presidio_fastapi')
if presidio_path not in sys.path:
    sys.path.insert(0, presidio_path)

try:
    # Try importing directly from the app.telemetry path
    from app.telemetry import trace_method
    print("SUCCESS: Direct app.telemetry import worked")
except Exception as e:
    print(f"Direct import failed: {e}")

try:
    # Try importing the module itself
    import app.telemetry as tel
    attrs = [name for name in dir(tel) if not name.startswith('_')]
    print(f"Direct module attributes: {attrs}")
except Exception as e:
    print(f"Direct module inspection error: {e}")

try:
    # Try the original import approach
    sys.path.insert(0, os.getcwd())
    from presidio_fastapi.app.telemetry import trace_method
    print("SUCCESS: Package import worked")
except Exception as e:
    print(f"Package import failed: {e}")
