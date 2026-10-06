import json
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TextIO

import httpx2
from pydantic import ValidationError

from cache_cli.settings import CliSettings, PayloadInput, parse_settings


def load_payload(settings: CliSettings) -> PayloadInput:
    """Return the payload from --json, or from the --input file (- reads stdin)."""
    if settings.json_body is not None:
        return PayloadInput.model_validate_json(settings.json_body)
    # JSON is UTF-8 (RFC 8259), so decode it explicitly rather than with the locale's code
    # page (cp1252 on Windows). utf-8-sig also drops the BOM Windows PowerShell adds.
    if settings.input == "-":
        text = sys.stdin.buffer.read().decode("utf-8-sig")
    else:
        with open(str(settings.input), encoding="utf-8-sig") as file:
            text = file.read()
    return PayloadInput.model_validate_json(text)


@contextmanager
def open_output(path: str) -> Iterator[TextIO]:
    """Yield stdout for -, otherwise the file at path opened for writing."""
    if path == "-":
        yield sys.stdout
        return
    with open(path, "w", encoding="utf-8") as file:
        yield file


def create_and_get_payload(
    client: httpx2.Client, payload: PayloadInput
) -> dict[str, str]:
    """POST the payload, GET it back by the returned id, and return the id and output."""
    created = client.post("/payload", json=payload.model_dump())
    created.raise_for_status()
    payload_id = created.json()["id"]

    fetched = client.get(f"/payload/{payload_id}")
    fetched.raise_for_status()
    return {"id": payload_id, "output": fetched.json()["output"]}


def run_service(settings: CliSettings, client: httpx2.Client) -> int:
    """Run --repeat round trips, write one JSON line each, and return the exit code."""
    try:
        payload = load_payload(settings)
        with open_output(settings.output) as output:
            for _ in range(settings.repeat):
                output.write(json.dumps(create_and_get_payload(client, payload)) + "\n")
    except httpx2.HTTPStatusError as error:
        response = error.response
        return report_error(f"server returned {response.status_code}: {response.text}")
    except httpx2.RequestError as error:
        return report_error(f"could not reach {settings.host}: {error}")
    except OSError as error:
        return report_error(str(error))
    except UnicodeDecodeError:
        return report_error("input is not valid UTF-8")
    except ValidationError as error:
        return report_error(
            f"input is not a valid payload: {format_validation_error(error)}"
        )
    return 0


def format_validation_error(error: ValidationError, *, as_flags: bool = False) -> str:
    """Return the validation errors as one short line, e.g. "-r: Input should be ..."."""
    messages = []
    for item in error.errors():
        message = item["msg"].removeprefix("Value error, ")
        if item["loc"]:
            name = ".".join(map(str, item["loc"]))
            # Argument errors are located by the alias the user typed, e.g. "r" for -r.
            if as_flags:
                name = f"-{name}" if len(name) == 1 else f"--{name}"
            message = f"{name}: {message}"
        messages.append(message)
    return "; ".join(messages)


def report_error(message: str) -> int:
    """Print an error to stderr and return the failure exit code."""
    print(f"cache-cli: {message}", file=sys.stderr)
    return 1


def main(args: list[str] | None = None) -> None:
    """Parse the arguments (sys.argv by default), run the round trips, and exit."""
    try:
        settings = parse_settings(args)
    except ValidationError as error:
        message = format_validation_error(error, as_flags=True)
        print(f"cache-cli: invalid arguments: {message}", file=sys.stderr)
        sys.exit(2)

    with httpx2.Client(base_url=str(settings.host), timeout=10) as client:
        sys.exit(run_service(settings, client))
