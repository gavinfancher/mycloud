from __future__ import annotations

from pydantic import BaseModel, Field


class SetupRequest(BaseModel):
    ssh_public_key: str = Field(..., min_length=20)


class DeployVMRequest(BaseModel):
    name: str = Field(..., pattern=r"^[a-z][a-z0-9-]{1,30}$")
    cores: int = Field(1, ge=1, le=32)
    memory_gb: float = Field(1.0, ge=0.5, le=64)
    disk_gb: int = Field(10, ge=10, le=2000)
    image_id: str = "homecloud-base"
