import pytest
from pydantic import ValidationError

from cache_cli.main import main
from cache_cli.settings import parse_settings

BODY = '{"list_1": ["a"], "list_2": ["b"]}'


def test_short_flags_set_options() -> None:
    settings = parse_settings(
        ["-h", "http://example.com:9000", "-r", "3", "-j", BODY, "-o", "out"]
    )

    assert str(settings.host) == "http://example.com:9000/"
    assert settings.repeat == 3
    assert settings.json_body == BODY
    assert settings.output == "out"


def test_long_flags_set_options() -> None:
    settings = parse_settings(
        ["--host", "http://example.com", "--repeat", "2", "--input", "-"]
    )

    assert str(settings.host) == "http://example.com/"
    assert settings.repeat == 2
    assert settings.input == "-"


def test_defaults() -> None:
    settings = parse_settings(["-j", BODY])

    assert str(settings.host) == "http://localhost:8000/"
    assert settings.repeat == 1
    assert settings.output == "-"


def test_help_is_on_long_flag_only(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        parse_settings(["--help"])

    assert exit_info.value.code == 0
    assert "-h, --host" in capsys.readouterr().out


def test_help_uses_the_spec_placeholders(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        parse_settings(["--help"])

    help_text = capsys.readouterr().out
    for option in [
        "--host URL",
        "--repeat N",
        "--input FILE|-",
        "--json JSON",
        "--output FILE|-",
    ]:
        assert option in help_text
    assert "HttpUrl" not in help_text
    assert "(default: null)" not in help_text


def test_environment_variables_are_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOST", "http://from-env:1")

    assert str(parse_settings(["-j", BODY]).host) == "http://localhost:8000/"


@pytest.mark.parametrize(
    "args",
    [
        [],  # neither --input nor --json
        ["-i", "payload.json", "-j", BODY],  # both
        ["-j", BODY, "-r", "0"],  # repeat below 1
        ["-j", BODY, "-h", "not-a-url"],  # invalid host
        ["-j", "{"],  # invalid JSON
        ["-j", '{"list_1": ["a"]}'],  # missing list_2
    ],
)
def test_invalid_arguments_are_rejected(args: list[str]) -> None:
    with pytest.raises(ValidationError):
        parse_settings(args)


def test_main_reports_invalid_arguments_with_exit_code_2(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["-j", BODY, "-r", "0"])

    assert exit_info.value.code == 2
    assert "invalid arguments: -r:" in capsys.readouterr().err


def test_help_starts_with_an_aligned_banner(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        parse_settings(["--help"])

    box = [
        line
        for line in capsys.readouterr().out.splitlines()
        if line.startswith(("+", "|"))
    ]
    assert len(box) == 4
    assert "CACHE CLI v" in box[1]
    assert len({len(line) for line in box}) == 1  # every row is the same width
