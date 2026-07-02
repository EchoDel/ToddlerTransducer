import argparse
import sys

from .app import puck_designer_app


def main():
    parser = argparse.ArgumentParser(
        description="Puck Designer - 3D model customizer for Toddler Transducer pucks"
    )
    parser.add_argument("--port", "-p", type=int, default=8081,
                        help="Port to run the server on (default: 8081)")
    parser.add_argument("--host", type=str, default="0.0.0.0",
                        help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--debug", "-d", action="store_true",
                        help="Run in debug mode")

    args = parser.parse_args()

    print(f"Puck Designer running at http://{args.host}:{args.port}")
    sys.stdout.flush()

    puck_designer_app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
