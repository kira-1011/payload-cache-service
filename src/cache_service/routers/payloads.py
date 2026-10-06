from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response, status

from cache_service.dependencies import SessionDep
from cache_service.schemas import PayloadCreate, PayloadCreateResponse, PayloadResponse
from cache_service.services import payloads

router = APIRouter(prefix="/payload", tags=["payloads"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_200_OK: {"description": "Payload already existed for this input"}
    },
)
def create_payload(
    body: PayloadCreate, session: SessionDep, request: Request, response: Response
) -> PayloadCreateResponse:
    payload, created = payloads.get_or_create_payload(session, body.list_1, body.list_2)
    if not created:
        response.status_code = status.HTTP_200_OK
        return PayloadCreateResponse(id=payload.id, message="Payload already exists")

    response.headers["Location"] = str(
        request.url_for("get_payload", payload_id=payload.id)
    )
    return PayloadCreateResponse(id=payload.id, message="Payload created")


@router.get("/{payload_id}")
def get_payload(payload_id: UUID, session: SessionDep) -> PayloadResponse:
    payload = payloads.get_payload(session, payload_id)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payload not found"
        )
    return PayloadResponse(output=payload.output)
