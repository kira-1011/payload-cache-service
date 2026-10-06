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
    monkeypatch.setattr("sys.stdin", io.StringIO(SPEC_JSON))

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
