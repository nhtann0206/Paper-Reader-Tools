"""
Enhanced CLI for Paper Reader Tools with FastAPI and Streamlit support.
"""
import os
import sys
import socket
import argparse
import subprocess
from typing import Optional

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Paper Reader Tools - Advanced CLI"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Run core logic tests")
    
    # API server command
    api_parser = subparsers.add_parser("api", help="Start the FastAPI server")
    api_parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    api_parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    api_parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    
    # Web (Streamlit) command
    web_parser = subparsers.add_parser("web", help="Start the Streamlit web interface")
    web_parser.add_argument('--port', type=int, default=8501, help='Port to bind to')
    
    # Process command
    process_parser = subparsers.add_parser("process", help="Process a paper")
    process_parser.add_argument('-f', '--file', help='Path to PDF file')
    process_parser.add_argument('-u', '--url', help='URL to PDF file')
    process_parser.add_argument('-o', '--output-dir', default='output', help='Directory to save output')
    process_parser.add_argument('-p', '--max-pages', type=int, default=None, help='Maximum pages to process')
    process_parser.add_argument('-t', '--type', choices=['summary', 'insights'], default='summary',
                             help='Type of analysis to perform')
    
    # Docker commands
    docker_parser = subparsers.add_parser("docker", help="Docker-related commands")
    docker_subparsers = docker_parser.add_subparsers(dest="docker_command", help="Docker command to run")
    
    # Build Docker images
    docker_build_parser = docker_subparsers.add_parser("build", help="Build Docker images")
    
    # Start Docker containers
    docker_start_parser = docker_subparsers.add_parser("start", help="Start Docker containers")
    docker_start_parser.add_argument('--dev', action='store_true', 
                                   help='Start in development mode with auto-reload')
    
    # Stop Docker containers
    docker_stop_parser = docker_subparsers.add_parser("stop", help="Stop Docker containers")
    
    # Clean Docker resources
    docker_clean_parser = docker_subparsers.add_parser("clean", help="Clean Docker resources")
    
    return parser.parse_args()

def check_port_available(host: str, port: int) -> bool:
    """Check if the port is available on the host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except socket.error:
            return False

def run_test():
    """Run core logic tests."""
    print("Running core logic tests...")
    subprocess.run([sys.executable, "test_core_logic.py"])

def run_api_server(host: str, port: int, debug: bool):
    """Start the FastAPI server."""
    if not check_port_available(host, port):
        print(f"Error: Port {port} is already in use on {host}.")
        print("Please try a different port or close the application using that port.")
        sys.exit(1)
    
    print(f"Starting API server on http://{host}:{port}")
    os.environ["HOST"] = host
    os.environ["PORT"] = str(port)
    os.environ["DEBUG"] = "1" if debug else "0"
    
    try:
        if debug:
            subprocess.run([
                sys.executable, "-m", "uvicorn", 
                "paper_reader_tools.api.server:app", 
                "--host", host, 
                "--port", str(port),
                "--reload"
            ])
        else:
            subprocess.run([
                sys.executable, "-m", "uvicorn", 
                "paper_reader_tools.api.server:app", 
                "--host", host, 
                "--port", str(port)
            ])
    except KeyboardInterrupt:
        print("\nShutting down API server...")

def run_streamlit(port: int):
    """Start the Streamlit web interface."""
    if not check_port_available("localhost", port):
        print(f"Error: Port {port} is already in use.")
        print("Please try a different port or close the application using that port.")
        sys.exit(1)
    
    # Set API URL environment variable
    os.environ["API_URL"] = "http://localhost:8080"
    
    print(f"Starting Streamlit web interface on http://localhost:{port}")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", 
        "paper_reader_tools/streamlit_app.py",
        "--server.port", str(port)
    ])

def run_process_paper(args):
    """Process a paper using the core functionality."""
    from paper_reader_tools.services.extractor import extract_pdf_text
    from paper_reader_tools.services.ai_client import GeminiClient
    from paper_reader_tools.services.pdf_generator import PDFGenerator
    from paper_reader_tools.services.utils import download_pdf
    from paper_reader_tools.repository.paper_repository import Paper, PaperRepository
    import asyncio

    async def process_paper():
        temp_file = None
        try:
            # Handle file or URL input
            if args.url:
                print(f"Downloading PDF from URL: {args.url}")
                pdf_path = await download_pdf(args.url)
                temp_file = pdf_path
            elif args.file:
                pdf_path = args.file
            else:
                print("Error: Either --file or --url must be specified")
                return

            # Ensure output directory exists
            os.makedirs(args.output_dir, exist_ok=True)

            # Extract text from PDF
            print(f"Extracting text from PDF: {pdf_path}")
            sections = await extract_pdf_text(pdf_path, args.max_pages)
            print(f"Found {len(sections)} sections")

            # Initialize Gemini client
            client = GeminiClient()

            # Get metadata using LLM
            first_page_text = next(iter(sections.values())) if sections else ""
            metadata = await client.extract_metadata(first_page_text)
            print(f"Extracted metadata: Title={metadata.get('title', 'No title')}")

            # If the source is a URL, set it as the URL
            if args.url:
                metadata["url"] = args.url

            # Combine all text for analysis
            all_text = "\n\n".join(sections.values())

            # Process with Gemini
            print(f"Generating {args.type} using Gemini...")
            response = await client.summarize_text(all_text, args.type)
            summary = client.extract_from_response(response)
            print(f"Generated content length: {len(summary)} characters")

            # Generate PDF
            pdf_generator = PDFGenerator(args.output_dir)
            output_path = await pdf_generator.generate_pdf(summary, metadata)
            print(f"Generated output at: {output_path}")

            # Suggest tags
            tags = await client.suggest_paper_tags(
                metadata.get("title", ""), 
                sections.get("Abstract", sections.get("ABSTRACT", ""))
            )
            print(f"Generated tags: {tags}")

            # Save to database
            repo = PaperRepository()
            paper = Paper(
                title=metadata.get("title", "Untitled Paper"),
                authors=metadata.get("authors", ""),
                publication=metadata.get("publication", ""),
                publication_date=metadata.get("date", ""),
                url=args.url or "",
                file_path=args.file or "",
                summary=summary,
                content=all_text[:10000],  # Store first 10K chars only
                tags=tags,
                sections=sections,
                output_path=os.path.basename(output_path)
            )
            paper_id = repo.save_paper(paper)
            print(f"Paper saved to database with ID: {paper_id}")

            return output_path
        
        finally:
            # Clean up temporary file if created
            if temp_file and os.path.exists(temp_file):
                os.unlink(temp_file)

    output_path = asyncio.run(process_paper())
    
    if output_path:
        print(f"\nSuccess! Output saved to: {output_path}")
    else:
        print("\nError: Failed to process paper")

def run_docker_build(args):
    """Build Docker images."""
    print("Building Docker images...")
    try:
        subprocess.run(["docker-compose", "build"])
    except Exception as e:
        print(f"Error building Docker images: {str(e)}")
        sys.exit(1)

def run_docker_start(args):
    """Start Docker containers."""
    print("Starting Docker containers...")
    try:
        # Check if development flag was passed
        if args.dev:
            print("Starting in DEVELOPMENT mode with auto-reload...")
            subprocess.run(["docker-compose", "-f", "docker-compose.dev.yml", "up", "-d"])
        else:
            subprocess.run(["docker-compose", "up", "-d"])
        print("\nServices are running:")
        print("- API:   http://localhost:8080")
        print("- Web UI: http://localhost:8501")
    except Exception as e:
        print(f"Error starting Docker containers: {str(e)}")
        sys.exit(1)

def run_docker_stop(args):
    """Stop Docker containers."""
    print("Stopping Docker containers...")
    try:
        subprocess.run(["docker-compose", "down"])
    except Exception as e:
        print(f"Error stopping Docker containers: {str(e)}")
        sys.exit(1)

def run_docker_clean(args):
    """Clean Docker resources."""
    print("Cleaning Docker resources...")
    try:
        # First stop any running containers
        subprocess.run(["docker-compose", "down"])
        # Remove project-related images
        subprocess.run(["docker", "image", "rm", "-f", "paper-reader-tools-api", "paper-reader-tools-web"])
        # Prune unused images
        subprocess.run(["docker", "image", "prune", "-f"])
        print("Docker resources cleaned successfully.")
    except Exception as e:
        print(f"Error cleaning Docker resources: {str(e)}")
        sys.exit(1)

def main():
    """Main entry point for the enhanced CLI."""
    args = parse_args()
    
    # Run the command
    if args.command == "test":
        run_test()
    elif args.command == "api":
        run_api_server(args.host, args.port, args.debug)
    elif args.command == "web":
        run_streamlit(args.port)
    elif args.command == "process":
        run_process_paper(args)
    elif args.command == "docker":
        if args.docker_command == "build":
            run_docker_build(args)
        elif args.docker_command == "start":
            run_docker_start(args)
        elif args.docker_command == "stop":
            run_docker_stop(args)
        elif args.docker_command == "clean":
            run_docker_clean(args)
        else:
            print("Error: Please specify a Docker command.")
            sys.exit(1)
    else:
        # Default to showing help
        print("Paper Reader Tools - Enhanced CLI\n")
        print("Please specify a command:")
        print("  test    - Run core logic tests")
        print("  api     - Start the FastAPI server")
        print("  web     - Start the Streamlit web interface")
        print("  process - Process a paper")
        print("  docker  - Docker-related commands")
        print("\nFor more details, run: python cli_enhanced.py --help")

if __name__ == "__main__":
    main()
