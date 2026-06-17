from uuid import UUID

from ninja import Router

from app.api.deps import JWTAuth
from app.core.database import AsyncSessionLocal
from app.schemas.chat import SimpleSuccessResponse
from app.schemas.user import SaveFcmTokenRequest, PushTestRequest, PushTestResponse
from app.services.user import UserService


user_router = Router(tags=["Users"], auth=JWTAuth())


@user_router.post("/fcm-token", response=SimpleSuccessResponse)
async def save_fcm_token(request, payload: SaveFcmTokenRequest):
    user_id = UUID(request.auth.get("sub"))
    async with AsyncSessionLocal() as db:
        service = UserService(db)
        await service.save_fcm_token(user_id=user_id, token=payload.token, platform=payload.platform)
        return SimpleSuccessResponse()


@user_router.post("/push-test", response=PushTestResponse)
async def push_test(request, payload: PushTestRequest):
    user_id = UUID(request.auth.get("sub"))
    async with AsyncSessionLocal() as db:
        service = UserService(db)
        result = await service.send_push_test(
            sender_id=user_id,
            receiver_id=payload.receiver_id,
            title=payload.title,
            body=payload.body,
            data=payload.data,
        )
        return PushTestResponse(**result)
