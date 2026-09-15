import json
import os
import sys
from datetime import timedelta, timezone
from pathlib import Path
from typing import TextIO
from loguru import logger

# 北京时间 UTC+8（无夏令时），日志时间戳统一按此输出，不随部署机时区漂移
_BEIJING_TZ = timezone(timedelta(hours=8))


def _formatter(record):
    extra = {k: v for k, v in record["extra"].items() if k != "_serialized"}
    payload = {
        "ts": record["time"].astimezone(_BEIJING_TZ).isoformat(),
        "level": record["level"].name,
        "logger": record["name"],
        "message": record["message"],
        **extra,
    }
    if record["exception"]:
        payload["exception"] = repr(record["exception"].value)
    # loguru 把 format 可调用的返回值当作模板再 .format_map，会把 JSON 里的 {} 当占位符
    # 二次解析（KeyError '"ts"'）。故把序列化结果塞进 record，返回纯占位模板，值不会被再解析。
    record["extra"]["_serialized"] = json.dumps(payload, ensure_ascii=False)
    return "{extra[_serialized]}\n"


def configure_logging(
    sink: TextIO | None = None,
    level: str = "INFO",
    log_file: str | os.PathLike[str] | None = None,
) -> None:
    """配置日志。

    控制台始终输出结构化 JSON（实时查看）。同时可选写一份到文件，
    方便控制台窗口关闭后回溯排查。文件默认落在 LOG_FILE 环境变量指向的
    路径，未设置则写 <api>/logs/api.log；传 sink 时（如测试）跳过文件 sink。
    """
    logger.remove()
    stream = sink if sink is not None else sys.stdout
    # Windows 控制台/重定向默认 cp1252/GBK，日志里的中文（AppError message、preflight
    # 说明等）会让 loguru 的 sink 抛 UnicodeEncodeError，刷屏且丢日志。文件 sink 已指定
    # utf-8，这里把控制台也拉齐。
    if getattr(stream, "encoding", "") and stream.encoding.lower() not in ("utf-8", "utf8"):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    logger.add(stream, level=level, format=_formatter)

    # 显式传 sink（测试注入 StringIO）时不落文件，避免污染。
    if sink is not None:
        return

    target = log_file or os.getenv("LOG_FILE")
    if target is None:
        # app/core/logging.py -> 上溯到 apps/api 目录
        target = Path(__file__).resolve().parents[2] / "logs" / "api.log"
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        target,
        level=level,
        format=_formatter,
        rotation="20 MB",      # 单文件超过 20MB 轮转
        retention="14 days",   # 保留最近 14 天
        compression="zip",     # 旧日志压缩
        enqueue=True,          # 多进程/异步下写盘安全
        encoding="utf-8",
    )
