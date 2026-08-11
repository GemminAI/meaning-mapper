from __future__ import annotations

import socket
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

from meaning_mapper.cle.client import CLEClient

CLE_REPO = Path("/Users/tomonam3/GemminAI/categorical-lift-engine")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="session")
def live_cle() -> Iterator[str]:
    """Spins up the REAL CLE FastAPI app (`cle.api.app:app`) as a
    subprocess via uvicorn -- same pattern cognitive-port-selector's own
    `live_cle` fixture uses this session. Real HTTP, not a mock, for the
    integration test proving this adapter actually works end to end."""

    if not CLE_REPO.is_dir():
        pytest.skip(
            f"categorical-lift-engine repo not found at {CLE_REPO}; cannot run live-CLE tests"
        )

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    process = subprocess.Popen(
        [
            str(CLE_REPO / ".venv" / "bin" / "python3"),
            "-m",
            "uvicorn",
            "cle.api.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=str(CLE_REPO),
        env={"PATH": "/usr/bin:/bin:/usr/local/bin"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        deadline = time.monotonic() + 20.0
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                response = httpx.get(f"{base_url}/health", timeout=1.0)
                if response.status_code == 200:
                    break
            except httpx.HTTPError as exc:
                last_error = exc
            time.sleep(0.3)
        else:
            process.terminate()
            output = process.stdout.read().decode() if process.stdout else ""
            raise RuntimeError(f"CLE did not become healthy in time: {last_error}\n{output}")

        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            process.kill()


@pytest.fixture
def cle_client(live_cle: str) -> Iterator[CLEClient]:
    with CLEClient(live_cle) as client:
        yield client
