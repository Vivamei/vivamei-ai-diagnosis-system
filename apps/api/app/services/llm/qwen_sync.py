import asyncio
import time
from typing import Any, AsyncIterator

import httpx
from loguru import logger

from app.core.config import settings
from app.services.llm.base import LLMEvent, LLMProvider, LLMRequest

# 分层 code → 前端 LAYER_COLOR / 报告渲染用固定顺序
_LAYER_CODES = ["skin", "subcutis", "fascia", "bone"]

# 分相三相：贵方 style_reference.composition 的键 → 前端 STYPE_STAGES 的键
# （贵方叫 soft_tissue，前端一直叫 flesh，此处只做映射不改前端命名）
_STYPE_COMPOSITION_CODES = {"skin": "skin", "soft_tissue": "flesh", "bone": "bone"}

_PHASE_LABELS = {
    "stype": "分相分析中",
    "style": "分型分析中",
    "subzone": "分区分析中",
    "struct": "分层分析中",
}


class QwenSyncLLMProvider(LLMProvider):
    """同步 LLM 服务客户端（贵方 /analyze-url 契约）。

    贵方一次性返回整份报告 JSON（见 docs/LLM_API_ALIGNMENT.md 与
    results_qwen3_vl_plus.json）。为兼容既有 SSE 流水线，这里把整份 JSON
    「伪流式」拆成 phase/delta/phase_done/radar/done 事件，使 run_analysis /
    Analyzing.tsx 无需改动即可复用；同时把贵方独有的富字段
    （aesthetic_optimization / project_directions / mapped_project_directions /
    lead_cta / disclaimer / image_quality）打包进 done 事件的 payload.extra，
    由 run_analysis 落到 Report.extra，报告页直接展示。
    """

    name = "qwen-sync"

    def __init__(
        self,
        base_url: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        pace: float = 0.2,
        poll: bool = True,
    ):
        self._base = base_url or settings.llm_sync_base_url
        # trust_env=False：LLM 是直连 IP，不走机器上的 HTTP(S)/SOCKS 代理（Clash 等），
        # 否则会触发 "Using SOCKS proxy, but 'socksio' not installed" 或绕道代理变慢/失败。
        self._client = httpx.AsyncClient(
            transport=transport,
            timeout=settings.llm_timeout_seconds,
            trust_env=False,
            # 单例客户端/worker。每个在途分析在 submit→轮询 SUCCESS 期间全程占 1 条连接
            # （最长 llm_timeout_seconds），突发高并发时连接池上限由配置控制，防打满默认 100。
            limits=httpx.Limits(
                max_connections=settings.llm_http_max_connections,
                max_keepalive_connections=settings.llm_http_max_keepalive,
            ),
        )
        # phase 之间的动画节奏（纯前端观感，数据早已就绪）
        self._pace = pace
        # True=queue 模式（提交后轮询 /api/analysis-jobs/{job_id}）；
        # False=sync 模式（贵方一次性返回整份报告，不轮询）。
        self._poll = poll

    async def analyze_stream(self, req: LLMRequest) -> AsyncIterator[LLMEvent]:
        # 配了 OSS 走 analyze-url（贵方拉图）；否则走 analyze-file（multipart 直传字节）。
        if req.image_bytes:
            fetch = self._post_analyze_file(req)
        else:
            fetch = self._post_analyze_url(req)

        _t0 = time.perf_counter()
        try:
            data = await fetch
        except httpx.HTTPError as e:
            logger.warning(
                "[LLM qwen-sync] 贵方接口调用失败，耗时 {:.1f}s，错误：{}",
                time.perf_counter() - _t0,
                str(e)[:200],
            )
            # 真实错误（含下游 URL/内网 IP）只进日志，用户侧给友好文案，避免泄露内网地址。
            yield LLMEvent(
                type="error",
                error={
                    "code": "LLM_SYNC_HTTP",
                    "message": "分析服务暂时不可用，请稍后重试",
                    "retryable": True,
                },
            )
            return
        logger.info(
            "[LLM qwen-sync] 贵方接口返回，耗时 {:.1f}s（此即报告页“准备中”的主要等待）",
            time.perf_counter() - _t0,
        )
        if data is None:
            yield LLMEvent(
                type="error",
                error={"code": "LLM_SYNC_HTTP", "message": "request failed", "retryable": True},
            )
            return

        if not data.get("success"):
            saf = data.get("safety") or {}
            msg = str(saf.get("hit_words_after") or data.get("error") or "")[:200]
            logger.warning("[LLM qwen-sync] returned success=false: {}", msg)
            yield LLMEvent(
                type="error",
                error={
                    "code": "LLM_SYNC_FAILED",
                    "message": msg,
                    "retryable": False,
                },
            )
            return

        report: dict[str, Any] = data.get("report") or {}

        for phase in ("style", "stype", "subzone", "struct"):
            yield LLMEvent(
                type="phase", phase=phase, payload={"label": _PHASE_LABELS[phase]}
            )
            payload = self._normalize_phase(phase, report.get(phase) or {})
            text = (
                payload.get("summary")
                or payload.get("description")
                or payload.get("narrative")
                or ""
            )
            if text:
                yield LLMEvent(type="delta", phase=phase, text=text)
            yield LLMEvent(type="phase_done", phase=phase, payload=payload)
            if self._pace > 0:
                await asyncio.sleep(self._pace)

        radar = report.get("radar_scores") or self._radar_from_chart(
            report.get("radar_chart") or data.get("radar_chart")
        )
        yield LLMEvent(type="radar", radar=radar)

        # radar_scores 的口径由贵方 radar_chart.semantics 决定：
        # "aging_exposure" = 衰老暴露度（= 100 - 该维度得分，越低越好），与旧版「得分越高越好」相反。
        # 前端据此切换图例文案与刻度上限；缺省时按旧口径渲染。
        chart = report.get("radar_chart") or data.get("radar_chart") or {}
        aesthetic = report.get("aesthetic_optimization") or {}
        yield LLMEvent(
            type="done",
            payload={
                "optimization": aesthetic.get("summary", ""),
                "extra": {
                    "aesthetic_optimization": aesthetic or None,
                    "project_directions": report.get("project_directions"),
                    "mapped_project_directions": data.get("mapped_project_directions"),
                    "lead_cta": report.get("lead_cta"),
                    "disclaimer": report.get("disclaimer"),
                    "image_quality": data.get("image_quality"),
                    "radar_semantics": chart.get("semantics"),
                    "radar_max": chart.get("max"),
                    "state_values": self._state_values(chart),
                },
            },
        )

    async def _post_analyze_url(self, req: LLMRequest) -> dict[str, Any] | None:
        url = f"{self._base}/api/analyze-url"
        logger.info(
            "[LLM qwen-sync] 提交 POST {} image_url={} user_id={}",
            url,
            req.image_url,
            req.user_id,
        )
        resp = await self._client.post(
            url,
            json={"image_url": req.image_url, "user_id": str(req.user_id or "")},
            headers={"Accept": "application/json"},
        )
        submit = self._parse_resp(url, resp)
        # sync 模式：贵方直接返回整份报告，submit 即结果；queue 模式：轮询 job。
        return submit if not self._poll else await self._poll_job(submit)

    async def _post_analyze_file(self, req: LLMRequest) -> dict[str, Any] | None:
        url = f"{self._base}/api/analyze-file"
        logger.info(
            "[LLM qwen-sync] 提交 POST {} file={} bytes user_id={}",
            url,
            len(req.image_bytes or b""),
            req.user_id,
        )
        resp = await self._client.post(
            url,
            files={
                "file": (
                    "upload.jpg",
                    req.image_bytes,
                    req.image_mime or "image/jpeg",
                )
            },
            data={"user_id": str(req.user_id or "")},
            headers={"Accept": "application/json"},
        )
        submit = self._parse_resp(url, resp)
        return submit if not self._poll else await self._poll_job(submit)

    async def _poll_job(self, submit: dict[str, Any]) -> dict[str, Any] | None:
        """提交+轮询：贵方 /api/analyze-url|analyze-file 只提交任务返回 job_id，
        本方按 poll_url 轮询 /api/analysis-jobs/{job_id}，直到 SUCCESS/FAILURE，
        然后把 job.result（形状同旧同步返回：success/report/radar_chart/...）返回，
        供 analyze_stream 复用原有解析逻辑。"""
        job_id = submit.get("job_id")
        poll_url = submit.get("poll_url") or (
            f"/api/analysis-jobs/{job_id}" if job_id else None
        )
        if not poll_url:
            logger.warning("[LLM qwen-sync] 提交返回缺少 job_id/poll_url：{}", submit)
            return None
        url = f"{self._base}{poll_url}"
        interval = max(0.2, settings.llm_poll_interval_seconds)
        # 总时长受 httpx 单请求超时保护（llm_timeout_seconds），这里再兜一个轮询次数上限。
        max_attempts = max(1, int(settings.llm_timeout_seconds / interval))
        _t0 = time.perf_counter()
        for attempt in range(max_attempts):
            resp = await self._client.get(url, headers={"Accept": "application/json"})
            job = self._parse_resp(url, resp, verbose=False)
            status = str(job.get("status") or "").upper()
            if status in ("SUCCESS", "SUCCEEDED", "DONE", "COMPLETED"):
                logger.info(
                    "[LLM qwen-sync] job={} 轮询完成 status={} 第{}次 耗时{:.1f}s",
                    job_id, status, attempt + 1, time.perf_counter() - _t0,
                )
                return job.get("result") or job
            if status in ("FAILURE", "FAILED", "ERROR", "REVOKED"):
                logger.warning(
                    "[LLM qwen-sync] job={} 轮询失败 status={} raw={}",
                    job_id, status, str(job)[:500],
                )
                # 把失败 result 透传给上层做 success=false 处理；没有 result 就合成一个。
                return job.get("result") or {"success": False, "error": job.get("message")}
            # QUEUED / STARTED / PROCESSING / PENDING / RETRY 等中间态：继续轮询
            await asyncio.sleep(interval)
        logger.warning(
            "[LLM qwen-sync] job={} 轮询超时（{}次 / {:.1f}s）", job_id, max_attempts,
            time.perf_counter() - _t0,
        )
        return {"success": False, "error": "分析超时，请稍后重试"}

    def _parse_resp(
        self, url: str, resp: httpx.Response, verbose: bool = True
    ) -> dict[str, Any]:
        # 提交响应全量打印便于对齐；轮询中间态量大，只在非 verbose 时打摘要。
        if verbose:
            logger.info(
                "[LLM qwen-sync] {} <- HTTP {} ({} bytes) raw={}",
                url, resp.status_code, len(resp.content), resp.text,
            )
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _normalize_phase(phase: str, src: dict[str, Any]) -> dict[str, Any]:
        """把贵方分维对象补齐为报告页期望的形状（code/label/description）。"""
        if phase == "subzone":
            zones = []
            for i, z in enumerate(src.get("zones") or []):
                zones.append(
                    {
                        "code": f"zone{i + 1}",
                        "label": z.get("zone", ""),
                        "zone": z.get("zone", ""),
                        "score": z.get("score"),
                        "status": z.get("status", ""),
                        "description": z.get("status", ""),
                        "strength": z.get("strength"),
                        "optimization": z.get("optimization"),
                    }
                )
            return {**src, "zones": zones}
        if phase == "struct":
            layers = []
            for i, layer in enumerate(src.get("layers") or []):
                code = _LAYER_CODES[i] if i < len(_LAYER_CODES) else f"layer{i + 1}"
                layers.append(
                    {
                        "code": code,
                        "label": layer.get("layer", ""),
                        "layer": layer.get("layer", ""),
                        "score": layer.get("score"),
                        "status": layer.get("status", ""),
                        "description": layer.get("status", ""),
                        "optimization": layer.get("optimization"),
                    }
                )
            return {**src, "layers": layers}
        if phase == "stype":
            # 贵方去掉了 primary/ratios，改用 style_reference.composition 给三相星级。
            # 折算成前端可直接渲染的 composition：{skin|flesh|bone: {label,stars,max_stars}}。
            comp_src = (src.get("style_reference") or {}).get("composition") or {}
            comp: dict[str, Any] = {}
            for vendor_key, code in _STYPE_COMPOSITION_CODES.items():
                item = comp_src.get(vendor_key) or {}
                if item.get("stars") is None:
                    continue
                comp[code] = {
                    "label": item.get("label", ""),
                    "stars": item.get("stars"),
                    "max_stars": item.get("max_stars") or 5,
                }
            return {**src, "composition": comp} if comp else src
        if phase == "style":
            # 贵方把 evidence 改名成 first_feature_evidence，补一份同名字段给报告页/明细页。
            fe = src.get("first_feature_evidence")
            if fe and not src.get("evidence"):
                return {**src, "evidence": fe}
            return src
        return src

    @staticmethod
    def _state_values(chart: dict[str, Any] | None) -> dict[str, int] | None:
        """radar_chart.state_values → {phase: 分数}，用于雷达图下方 4S 的数值。
        与 values（轴长，越小越年轻）不同口径：state_values 是状态分，越高越年轻。
        贵方已算好，本方不做任何换算；缺省时返回 None 由前端回落到 radarScores。"""
        if not chart:
            return None
        values = chart.get("state_values")
        if not values:
            return None
        keys = chart.get("keys") or ["stype", "style", "subzone", "struct"]
        out: dict[str, int] = {}
        for k, v in zip(keys, values):
            try:
                out[k] = int(v)
            except (TypeError, ValueError):
                continue
        return out or None

    @staticmethod
    def _radar_from_chart(chart: dict[str, Any] | None) -> dict[str, int]:
        if not chart:
            return {"stype": 0, "style": 0, "subzone": 0, "struct": 0}
        keys = chart.get("keys") or ["stype", "style", "subzone", "struct"]
        values = chart.get("values") or []
        out: dict[str, int] = {}
        for k, v in zip(keys, values):
            try:
                out[k] = int(v)
            except (TypeError, ValueError):
                out[k] = 0
        for k in ("stype", "style", "subzone", "struct"):
            out.setdefault(k, 0)
        return out
