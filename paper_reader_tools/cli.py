"""
Command-line interface for Paper Reader Tools.
"""
import os
import sys
import argparse
import threading
import socket
from .web_app import start_webapp
from .main import run_cli as run_legacy_cli


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Paper Reader Tools")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Web server command
    web_parser = subparsers.add_parser("web", help="Start the web application")
    web_parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    web_parser.add_argument('--port', type=int, default=8080, help='Port to bind to (default: 8080)')
    web_parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    
    # Legacy CLI command
    cli_parser = subparsers.add_parser("process", help="Process a paper (legacy CLI)")
    cli_parser.add_argument('-f', '--file', help='Path to PDF file')
    cli_parser.add_argument('-u', '--url', help='URL to PDF file')
    cli_parser.add_argument('-o', '--output-dir', default='output', help='Directory to save output')
    cli_parser.add_argument('-p', '--max-pages', type=int, default=None, help='Maximum number of pages to process')
    cli_parser.add_argument('-t', '--type', choices=['summary', 'insights'], default='summary',
                           help='Type of analysis to perform')
    
    return parser.parse_args()


def check_port_available(host, port):
    """Check if the port is available on the host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except socket.error:
            return False


def run_cli():
    """Main entry point for command-line interface."""
    args = parse_args()
    
    # If no command specified, default to web
    if not args.command:
        host = '127.0.0.1'  # Change default to localhost instead of 0.0.0.0
        port = 8080         # Use 8080 as default port to avoid AirPlay conflict
        print(f"Starting web application on http://{host}:{port}...")
        try:
            start_webapp(host=host, port=port)
        except OSError as e:
            if "Address already in use" in str(e):
                print(f"\nError: Port {port} is already in use.")
                print("Please try a different port using:")
                print(f"    poetry run paper-reader web --port <port_number>\n")
            else:
                print(f"Error starting web server: {e}")
        return
    
    if args.command == "web":
        if not check_port_available(args.host, args.port):
            print(f"\nError: Port {args.port} is already in use on {args.host}.")
            print("Please try a different port or close the application using that port.\n")
            return
        
        print(f"Starting web application on http://{args.host}:{args.port}...")
        start_webapp(host=args.host, port=args.port, debug=args.debug)
    
    elif args.command == "process":
        # Run the legacy CLI
        sys.argv = [sys.argv[0]] + sys.argv[2:]  # Remove the 'process' argument
        run_legacy_cli()


if __name__ == "__main__":
    run_cli()
