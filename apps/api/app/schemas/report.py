from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ReportResponse(BaseModel):
    taskId: str
    schemaVersion: str
    stype: dict[str, Any]
    style: dict[str, Any]
    subzone: dict[str, Any]
    struct: dict[str, Any]
    radarScores: dict[str, int]
    # radarScores 的口径："aging_exposure" 表示衰老暴露度（越低越好），
    # 缺省/None 表示旧口径得分（越高越好）。radar_max 为刻度上限。
    radar_semantics: str | None = None
    radar_max: int | None = None
    # 雷达图下方 4S 展示的状态分（越高越年轻），与 radarScores（轴长，越小越年轻）
    # 是两套口径，均由贵方直接给出，本方不换算。缺省时前端回落到 radarScores。
    state_values: dict[str, int] | None = None
    optimization: str
    # 贵方同步契约富字段（snake_case，前端 Report.tsx 直接按此读取）；
    # SSE 流式 provider 无这些字段时为 None，前端各自兜底。
    aesthetic_optimization: dict[str, Any] | None = None
    project_directions: list[Any] | None = None
    mapped_project_directions: list[Any] | None = None
    lead_cta: dict[str, Any] | None = None
    disclaimer: str | None = None
    image_quality: Any | None = None
    createdAt: datetime
