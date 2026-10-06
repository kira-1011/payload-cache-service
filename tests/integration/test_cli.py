import io
import json
from pathlib import Path
from unittest.mock import MagicMock

import httpx2
import pytest
from fastapi.testclient import TestClient

from cache_cli.main import run_service
from cache_cli.settings import parse_settings

SPEC_JSON = json.dumps(
    {
        "list_1": ["first string", "second string", "third string"],
        "list_2": ["other string", "another string", "last string"],
    }
)
SPEC_OUTPUT = "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING, THIRD STRING, LAST STRING"


def test_repeated_round_trips_reuse_the_payload(
    client: TestClient, transform_spy: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = run_service(parse_settings(["-j", SPEC_JSON, "-r", "3"]), client)

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert exit_code == 0
    assert len(lines) == 3
    assert len({line["id"] for line in lines}) == 1
    assert all(line["output"] == SPEC_OUTPUT for line in lines)
    assert transform_spy.call_count == 6  # first round trip only


def test_input_file_and_output_file(client: TestClient, tmp_path: Path) -> None:
    input_file = tmp_path / "payload.json"
    input_file.write_text(SPEC_JSON, encoding="utf-8")
    output_file = tmp_path / "results.jsonl"

    exit_code = run_service(
        parse_settings(["-i", str(input_file), "-o", str(output_file)]), client
    )

    assert exit_code == 0
    assert json.loads(output_file.read_text(encoding="utf-8"))["output"] == SPEC_OUTPUT


def test_input_from_stdin(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("sys.stdin", stdin_bytes(SPEC_JSON.encode()))

    exit_code = run_service(parse_settings(["-i", "-"]), client)

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out)["output"] == SPEC_OUTPUT


def test_server_error_exits_with_1(
    client: TestClient, capsys: pytest.CaptureFixture[str]
) -> None:
    # Valid shape for the CLI, but the service rejects unequal lengths.
    body = '{"list_1": ["a", "b"], "list_2": ["c"]}'

    exit_code = run_service(parse_settings(["-j", body]), client)

    assert exit_code == 1
    assert "server returned 422" in capsys.readouterr().err


def test_unreachable_service_exits_with_1(capsys: pytest.CaptureFixture[str]) -> None:
    def refuse(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("connection refused", request=request)

    with httpx2.Client(
        base_url="http://localhost:8000", transport=httpx2.MockTransport(refuse)
    ) as down:
        exit_code = run_service(parse_settings(["-j", SPEC_JSON]), down)

    assert exit_code == 1
    assert "could not reach" in capsys.readouterr().err


def test_input_with_byte_order_mark_is_accepted(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Windows PowerShell writes files and pipes stdin as UTF-8 with a BOM.
    input_file = tmp_path / "payload.json"
    input_file.write_text(SPEC_JSON, encoding="utf-8-sig")
    monkeypatch.setattr("sys.stdin", stdin_bytes(SPEC_JSON.encode("utf-8-sig")))

    assert run_service(parse_settings(["-i", str(input_file)]), client) == 0
    assert run_service(parse_settings(["-i", "-"]), client) == 0
    outputs = [
        json.loads(line)["output"] for line in capsys.readouterr().out.splitlines()
    ]
    assert outputs == [SPEC_OUTPUT, SPEC_OUTPUT]


def test_stdin_is_decoded_as_utf8(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Windows decodes piped stdin with its code page (cp1252) unless told otherwise.
    body = json.dumps({"list_1": ["café"], "list_2": ["straße"]}, ensure_ascii=False)
    monkeypatch.setattr("sys.stdin", stdin_bytes(body.encode()))

    assert run_service(parse_settings(["-i", "-"]), client) == 0
    assert json.loads(capsys.readouterr().out)["output"] == "CAFÉ, STRASSE"


def test_input_that_is_not_utf8_exits_with_1(
    client: TestClient, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    input_file = tmp_path / "payload.json"
    input_file.write_bytes(b'{"list_1": ["\xff"], "list_2": ["b"]}')

    assert run_service(parse_settings(["-i", str(input_file)]), client) == 1
    assert "not valid UTF-8" in capsys.readouterr().err


def stdin_bytes(data: bytes) -> io.TextIOWrapper:
    """Return a stand-in for sys.stdin whose .buffer yields these raw bytes."""
    return io.TextIOWrapper(io.BytesIO(data))
