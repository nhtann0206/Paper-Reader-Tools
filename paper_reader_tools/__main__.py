"""
Command-line entry point for Paper Reader Tools.
"""
import sys
import os
from .cli import run_cli

def main():
    """Main entry point when executed as a module."""
    run_cli()

if __name__ == "__main__":
    main()
