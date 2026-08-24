from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class HealthLevel(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class ComponentStatus:
    component_id: str
    label: str
    level: HealthLevel
    detail: str = ""
    age_seconds: float | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.component_id,
            "label": self.label,
            "level": self.level.value,
            "detail": self.detail,
            "age_seconds": self.age_seconds,
        }


@dataclass
class SystemStatus:
    components: list[ComponentStatus] = field(default_factory=list)
    checked_at: float = 0.0

    @property
    def overall(self) -> HealthLevel:
        levels = {c.level for c in self.components}
        if HealthLevel.DOWN in levels:
            return HealthLevel.DOWN
        if HealthLevel.DEGRADED in levels:
            return HealthLevel.DEGRADED
        if HealthLevel.UNKNOWN in levels and HealthLevel.OK not in levels:
            return HealthLevel.UNKNOWN
        return HealthLevel.OK

    def component(self, component_id: str) -> ComponentStatus | None:
        for item in self.components:
            if item.component_id == component_id:
                return item
        return None
