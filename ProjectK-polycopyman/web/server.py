from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path


def run() -> None:
    web_dir = Path(__file__).resolve().parent
    handler = partial(SimpleHTTPRequestHandler, directory=str(web_dir))
    server = HTTPServer(("127.0.0.1", 8082), handler)
    print("web server running at http://127.0.0.1:8082")
    server.serve_forever()


if __name__ == "__main__":
    run()
