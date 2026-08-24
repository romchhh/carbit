from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.services.monitoring.catalog import CRITICAL_COMPONENT_IDS


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
        critical = [c for c in self.components if c.component_id in CRITICAL_COMPONENT_IDS]
        parsers = [c for c in self.components if c.component_id.startswith("parser:")]
        other = [
            c
            for c in self.components
            if c.component_id not in CRITICAL_COMPONENT_IDS
            and not c.component_id.startswith("parser:")
        ]

        critical_levels = {c.level for c in critical}
        parser_levels = {c.level for c in parsers}
        other_levels = {c.level for c in other}

        if HealthLevel.DOWN in critical_levels:
            return HealthLevel.DOWN
        if HealthLevel.DEGRADED in critical_levels:
            return HealthLevel.DEGRADED
        if HealthLevel.DOWN in parser_levels or HealthLevel.DEGRADED in parser_levels:
            return HealthLevel.DEGRADED
        if HealthLevel.DOWN in other_levels:
            return HealthLevel.DOWN
        if HealthLevel.DEGRADED in other_levels:
            return HealthLevel.DEGRADED
        all_levels = {c.level for c in self.components}
        if HealthLevel.UNKNOWN in all_levels and HealthLevel.OK not in all_levels:
            return HealthLevel.UNKNOWN
        return HealthLevel.OK

    def component(self, component_id: str) -> ComponentStatus | None:
        for item in self.components:
            if item.component_id == component_id:
                return item
        return None
