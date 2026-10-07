import argparse
from importlib.metadata import version
from typing import Any, Self

from pydantic import (
    AliasChoices,
    BaseModel,
    Field,
    HttpUrl,
    PrivateAttr,
    ValidationError,
    model_validator,
)
from pydantic_settings import (
    BaseSettings,
    CliApp,
    CliSettingsSource,
    PydanticBaseSettingsSource,
)


class PayloadInput(BaseModel):
    """Request body for POST /payload; the service enforces the full rules."""

    list_1: list[str]
    list_2: list[str]


class CliSettings(BaseSettings, cli_hide_none_type=True):
    """Exercise the payload cache service: create a payload, read it back, print it."""

    # One-letter aliases become short options (-h, -r, ...), per pydantic-settings.
    host: HttpUrl = Field(
        HttpUrl("http://localhost:8000"),
        validation_alias=AliasChoices("h", "host"),
        description="URL of the payload cache service",
    )
    repeat: int = Field(
        1,
        ge=1,
        validation_alias=AliasChoices("r", "repeat"),
        description="number of round trips",
    )
    input: str | None = Field(
        None,
        validation_alias=AliasChoices("i", "input"),
        description="file with the JSON payload, or - for stdin",
    )
    json_body: str | None = Field(
        None,
        validation_alias=AliasChoices("j", "json"),
        description="the JSON payload itself",
    )
    output: str = Field(
        "-",
        validation_alias=AliasChoices("o", "output"),
        description="file to write results to, or - for stdout",
    )

    # Parsed once by check_payload_source, so the CLI never parses --json twice.
    _json_payload: PayloadInput | None = PrivateAttr(default=None)

    @property
    def json_payload(self) -> PayloadInput | None:
        """Return the --json payload parsed during validation, or None with --input."""
        return self._json_payload

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Command-line arguments only: stray env vars such as HOST must not change the options.
        return (init_settings,)

    @model_validator(mode="after")
    def check_payload_source(self) -> Self:
        if (self.input is None) == (self.json_body is None):
            raise ValueError("pass exactly one of --input or --json")
        if self.json_body is not None:
            try:
                self._json_payload = PayloadInput.model_validate_json(self.json_body)
            except ValidationError as error:
                reason = error.errors()[0]["msg"]
                raise ValueError(f"--json is not a valid payload ({reason})") from error
        return self


# Placeholders from the task spec's usage line, instead of the Python types.
METAVARS = {
    "--host": "URL",
    "--repeat": "N",
    "--input": "FILE|-",
    "--json": "JSON",
    "--output": "FILE|-",
}


def add_cli_argument(
    parser: argparse.ArgumentParser, *names: str, **kwargs: Any
) -> argparse.Action:
    """Add an option with the spec's placeholder and without a "(default: null)" note."""
    kwargs["metavar"] = METAVARS.get(names[-1], kwargs.get("metavar"))
    if kwargs.get("help"):
        kwargs["help"] = kwargs["help"].removesuffix(" (default: null)")
    return parser.add_argument(*names, **kwargs)


def banner() -> str:
    """Return the boxed name and version shown at the top of --help."""
    width = 42
    lines = [
        f"CACHE CLI v{version('payload-cache-service')}",
        "payload cache service utility",
    ]
    border = "+" + "-" * width + "+"
    return "\n".join([border, *(f"|{line.center(width)}|" for line in lines), border])


def parse_settings(args: list[str] | None = None) -> CliSettings:
    """Parse command-line arguments (sys.argv by default) into validated settings."""
    # argparse reserves -h for help, but the spec assigns -h to --host; help stays on --help.
    # The banner lives in --help only: normal runs print JSON lines that tools parse.
    parser = argparse.ArgumentParser(
        prog="cache-cli",
        description=f"{banner()}\n\n{CliSettings.__doc__}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )
    parser.add_argument("--help", action="help", help="show this help message and exit")
    source = CliSettingsSource(
        CliSettings, root_parser=parser, add_argument_method=add_cli_argument
    )
    return CliApp.run(CliSettings, cli_args=args, cli_settings_source=source)
