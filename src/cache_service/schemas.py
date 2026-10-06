from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

# Upper bounds on input size
MAX_ITEMS = 1_000
MAX_STRING_LENGTH = 1_000

BoundedString = Annotated[str, Field(max_length=MAX_STRING_LENGTH)]
StringList = Annotated[list[BoundedString], Field(min_length=1, max_length=MAX_ITEMS)]


class PayloadCreate(BaseModel):
    list_1: StringList
    list_2: StringList

    @model_validator(mode="after")
    def check_equal_lengths(self) -> Self:
        if len(self.list_1) != len(self.list_2):
            raise ValueError("list_1 and list_2 must have the same length")
        return self


class PayloadCreateResponse(BaseModel):
    id: UUID
    message: str


class PayloadResponse(BaseModel):
    output: str
