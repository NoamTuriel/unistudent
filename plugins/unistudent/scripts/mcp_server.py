#!/usr/bin/env python3
"""MCP server entry point: python3 <plugin>/scripts/mcp_server.py (stdio)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from unistudent.mcp import main  # noqa: E402

if __name__ == "__main__":
    main()
