from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class PulseMetrics(BaseModel):
    total_circulars: int
    this_week: int
    superseded: int
    questions_asked: int
    questions_answered: int
    learnings_captured: int
    sparkline: list[int]


class HeatmapRow(BaseModel):
    name: str
    vals: list[int]


class HeatmapData(BaseModel):
    cols: list[str]
    rows: list[HeatmapRow]


class ActivityItem(BaseModel):
    when: str
    type: Literal["circ", "ask", "save", "learn", "debate"]
    text: str
    impact: Literal["high", "med", "low"] | None = None


class DashboardPulseResponse(BaseModel):
    success: bool = True
    pulse: PulseMetrics
    heatmap: HeatmapData
    activity: list[ActivityItem]
