#!/usr/bin/env python3
"""Script to fix remaining type annotation issues in test_middleware.py"""

import re

def fix_middleware_types():
    file_path = "tests/test_middleware.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix all async def mock_call_next functions that don't have type annotations
    patterns = [
        (r'async def mock_call_next\(request\):', 'async def mock_call_next(request: Request) -> Response:'),
        (r'async def mock_call_next_error\(request\):', 'async def mock_call_next_error(request: Request) -> Response:'),
        (r'async def mock_call_next_slow\(request\):', 'async def mock_call_next_slow(request: Request) -> Response:'),
        (r'async def mock_call_next_error\(request, code=status_code\):', 'async def mock_call_next_error(request: Request, code=status_code) -> Response:'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Fixed type annotations in test_middleware.py")

if __name__ == "__main__":
    fix_middleware_types()
