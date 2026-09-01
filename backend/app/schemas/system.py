from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str


class VersionResponse(BaseModel):
    app_name: str
    version: str
    environment: str
    api_prefix: str
