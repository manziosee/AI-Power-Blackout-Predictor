from pydantic import BaseModel


class PushSubscriptionCreate(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


class PushSubscriptionOut(BaseModel):
    id: str
    endpoint: str

    model_config = {"from_attributes": True}
