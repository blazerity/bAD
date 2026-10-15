from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from .agent_config import sanitize_conditions, sanitize_settings


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
    config_version: Optional[str] = Field(default=None, max_length=64)
    # Light agent health (optional; stored in device meta).
    last_inventory_ok: Optional[bool] = None
    last_inventory_error: Optional[str] = Field(default=None, max_length=256)
    agent_uptime_seconds: Optional[int] = Field(default=None, ge=0)
    system_drive_free_bytes: Optional[int] = Field(default=None, ge=0)


class InventoryRequest(BaseModel):
    schema_version: int
    device_id: str = Field(min_length=1, max_length=128)
    collected_at: Optional[str] = None
    agent_version: Optional[str] = None
    host: Optional[dict[str, Any]] = None
    hardware: Optional[dict[str, Any]] = None
    network: Optional[dict[str, Any]] = None
    users: Optional[dict[str, Any]] = None
    software: Optional[dict[str, Any]] = None
    collector_errors: list[Any] = Field(default_factory=list)

    model_config = {"extra": "allow"}


class PolicyCondition(BaseModel):
    field: str = Field(min_length=1, max_length=64)
    op: str = Field(min_length=1, max_length=32)
    value: str = Field(min_length=1, max_length=255)


class AgentPolicyBody(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    enabled: bool = True
    priority: int = Field(default=100, ge=0, le=1_000_000)
    conditions: list[PolicyCondition] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)

    @field_validator("settings")
    @classmethod
    def _settings_ok(cls, value: dict[str, Any]) -> dict[str, Any]:
        cleaned = sanitize_settings(value)
        if not cleaned:
            raise ValueError("settings must include at least one allowed key")
        return cleaned

    @field_validator("conditions")
    @classmethod
    def _conditions_ok(cls, value: list[PolicyCondition]) -> list[PolicyCondition]:
        raw = [c.model_dump() for c in value]
        cleaned = sanitize_conditions(raw)
        if len(cleaned) != len(raw):
            raise ValueError(
                "conditions must use field in hostname|domain|os_caption "
                "and op in equals|contains"
            )
        if not cleaned:
            raise ValueError("at least one condition is required")
        return [PolicyCondition(**c) for c in cleaned]


class DeviceConfigOverrideBody(BaseModel):
    settings: dict[str, Any] = Field(default_factory=dict)

    @field_validator("settings")
    @classmethod
    def _settings_ok(cls, value: dict[str, Any]) -> dict[str, Any]:
        cleaned = sanitize_settings(value)
        if not cleaned:
            raise ValueError("settings must include at least one allowed key")
        return cleaned


class DeviceTagsBody(BaseModel):
    tags: list[str] | str = Field(default_factory=list)
