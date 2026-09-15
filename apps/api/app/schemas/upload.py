from pydantic import BaseModel


class UploadTokenResponse(BaseModel):
    ossEndpoint: str
    accessKeyId: str
    accessKeySecret: str
    securityToken: str
    expiration: str
    objectKey: str
    maxBytes: int


class PhotoRegisterRequest(BaseModel):
    ossKey: str
    width: int | None = None
    height: int | None = None
    bytes: int | None = None
    mime: str | None = None


class PhotoRegisterResponse(BaseModel):
    photoId: int
    moderationStatus: str
