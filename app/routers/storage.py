from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user, StorageServiceDep
from app.schemas import (
    Msg,
    PresignGetRequest,
    PresignGetResponse,
    PresignPutRequest,
    PresignPutResponse,
)


router = APIRouter(
    prefix="/storage",
    tags=["Storage"],
)

@router.post("/presign-put", response_model=Msg[PresignPutResponse])
async def presign_put(
    body: PresignPutRequest,
    user_id: Annotated[UUID, Depends(get_current_user())],
    storage_service: StorageServiceDep,
) -> Msg[PresignPutResponse]:
    result = await storage_service.generate_presigned_put(user_id, body)
    return Msg(
        code=200,
        msg="Presigned URL generated",
        data=result,
    )


@router.post("/presign-get", response_model=Msg[PresignGetResponse])
async def presign_get(
    body: PresignGetRequest,
    user_id: Annotated[UUID, Depends(get_current_user())],
    storage_service: StorageServiceDep,
) -> Msg[PresignGetResponse]:
    result = await storage_service.generate_presigned_get(user_id, body)
    return Msg(
        code=200,
        msg="Presigned URL generated",
        data=result,
    )
