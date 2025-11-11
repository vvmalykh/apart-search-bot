#!/usr/bin/env python3
"""
Compatibility shim for backward compatibility.

This file exists to maintain backward compatibility with existing scripts
and Docker containers that call parser.py directly. All functionality has
been refactored into the src/ package and main.py.

For new code, use: python3 main.py
"""

import sys

# Import and run the main function from the new structure
from main import main

if __name__ == "__main__":
    sys.exit(main())
