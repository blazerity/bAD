from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class EnrollRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=128)
    hostname: Optional[str] = Field(default=None, max_length=255)
    agent_version: Optional[str] = Field(default=None, max_length=64)


class EnrollResponse(BaseModel):
    api_key: str
    device_id: str


class HeartbeatRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=128)
    agent_version: Optional[str] = Field(default=None, max_length=64)
    last_inventory_at: Optional[str] = None


class InventoryRequest(BaseModel):
    schema_version: int
    device_id: str = Field(min_length=1, max_length=128)
    collected_at: Optional[str] = None
    agent_version: Optional[str] = None
    host: Optional[dict[str, Any]] = None
    hardware: Optional[dict[str, Any]] = None
    network: Optional[dict[str, Any]] = None
    users: Optional[dict[str, Any]] = None
    collector_errors: list[Any] = Field(default_factory=list)

    model_config = {"extra": "allow"}
