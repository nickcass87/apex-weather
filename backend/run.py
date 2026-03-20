"""Launch script that ensures local vendor packages are importable."""
from __future__ import annotations

import os
import sys

# Add vendor directory to Python path
vendor_dir = os.path.join(os.path.dirname(__file__), "vendor")
if os.path.isdir(vendor_dir):
    sys.path.insert(0, vendor_dir)

# Also ensure the backend directory itself is on the path
sys.path.insert(0, os.path.dirname(__file__))

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        loop="asyncio",
        http="h11",
    )
