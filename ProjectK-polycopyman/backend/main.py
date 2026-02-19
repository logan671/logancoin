import uvicorn

from .app import app
from .config import API_HOST, API_PORT


def run() -> None:
    uvicorn.run(app, host=API_HOST, port=API_PORT)


if __name__ == "__main__":
    run()
