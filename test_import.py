#!/usr/bin/env python3

print("Testing telemetry import...")

try:
    from presidio_fastapi.app.telemetry import trace_method
    print("SUCCESS: trace_method imported")
except ImportError as e:
    print(f"IMPORT ERROR: {e}")
except Exception as e:
    print(f"OTHER ERROR: {e}")

try:
    import presidio_fastapi.app.telemetry as tel
    attrs = [name for name in dir(tel) if not name.startswith('_')]
    print(f"Available attributes: {attrs}")
except Exception as e:
    print(f"Module inspection error: {e}")
