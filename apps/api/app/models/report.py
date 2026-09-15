import enum
from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReportModerationStatus(str, enum.Enum):
    pending = "pending"
    passed = "passed"
    rejected = "rejected"


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("analysis_tasks.id"), nullable=False, unique=True
    )
    schema_version: Mapped[str] = mapped_column(String(8), nullable=False, default="v1")
    stype: Mapped[dict] = mapped_column(JSON, nullable=False)
    style: Mapped[dict] = mapped_column(JSON, nullable=False)
    subzone: Mapped[dict] = mapped_column(JSON, nullable=False)
    # DB 列名加下划线避免 SQL 保留字；对外 LLMEvent.phase 与 JSON key 仍用裸 "struct"
    struct_: Mapped[dict] = mapped_column("struct_", JSON, nullable=False)
    radar_scores: Mapped[dict] = mapped_column(JSON, nullable=False)
    optimization: Mapped[str] = mapped_column(Text, nullable=False)
    # 贵方同步契约独有的富字段（aesthetic_optimization / project_directions /
    # mapped_project_directions / lead_cta / disclaimer / image_quality）。
    # SSE 流式 provider 不产出这些字段时为 {}。
    extra: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    full_text: Mapped[str] = mapped_column(Text, nullable=False)
    moderation_status: Mapped[ReportModerationStatus] = mapped_column(
        Enum(ReportModerationStatus), nullable=False, default=ReportModerationStatus.pending
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
