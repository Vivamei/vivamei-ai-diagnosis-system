"""
services/llm.py

LLM calling service.
Supports mock, Qwen (DashScope), and Volcengine (Ark).

Two-stage workflow (original):
1. Style Top3 classification
2. Full 4S report generation with fixed Top1 style

Parallel workflow (new):
1. Parallel: Style Top3 + Stype + Subzone + Struct
2. Serial: Style detail (depends on Top1)
3. Merge all results
"""

import json
import time
import logging
import asyncio
from typing import Any, Dict, List, Optional

from openai import OpenAI, AsyncOpenAI

from core.config import Settings
from core.exceptions import ConfigurationError, LLMCallError
from services.llm_errors import retry_async, retry_sync
from services.dimension_retry import retry_missing_dimensions_once
from domain.prompts2step import REPORT_SYSTEM_PROMPT, build_report_user_prompt
from domain.stype_prompt import STYPE_SYSTEM_PROMPT, build_stype_user_prompt
from domain.subzone_prompt import SUBZONE_SYSTEM_PROMPT, build_subzone_user_prompt
from domain.struct_prompt import STRUCT_SYSTEM_PROMPT, build_struct_user_prompt
from domain.style_detail_prompt import STYLE_DETAIL_SYSTEM_PROMPT, build_style_detail_user_prompt
from utils.json import extract_json_from_text
from services.visual_age_pipeline import (
    finalize_report as finalize_visual_age_report,
    public_style_result,
    validate_face_assessment,
)

try:
    from domain.style_prompt import (
        STYLE_TOP3_SYSTEM_PROMPT,
        STYLE_TOP3_USER_PROMPT,
    )
except ImportError:
    from domain.style_prompt import (
        STYLE_SYSTEM_PROMPT as STYLE_TOP3_SYSTEM_PROMPT,
        STYLE_USER_PROMPT as STYLE_TOP3_USER_PROMPT,
    )


logger = logging.getLogger(__name__)


VALID_STYLE_LABELS = [
    "甜美少女型",
    "魅力时尚型",
    "盐系简洁型",
    "温婉柔美型",
    "自然优雅型",
    "知性沉着型",
    "浪漫性感型",
    "华丽高雅型",
    "飒爽前卫型",
]


DEFAULT_STYLE_TOP3 = [
    {
        "label": "自然优雅型",
        "confidence": 0.60,
        "reason": "Style 首判未能稳定输出，使用自然协调作为兜底候选。",
        "matched_features": ["整体协调", "自然舒展"],
    },
    {
        "label": "温婉柔美型",
        "confidence": 0.55,
        "reason": "存在柔和亲和的视觉倾向，作为备选候选。",
        "matched_features": ["柔和", "亲和"],
    },
    {
        "label": "甜美少女型",
        "confidence": 0.50,
        "reason": "存在一定亲和轻盈感，作为第三候选。",
        "matched_features": ["亲和", "轻盈"],
    },
]


def _invalid_response_error(stage: str, content: str, exc: Exception) -> LLMCallError:
    """Log bounded diagnostics and return a safe client-facing parse error."""
    logger.warning(
        "%s JSON parse failed: %s; raw=%r",
        stage,
        exc,
        content[:500],
    )
    return LLMCallError(
        "大模型返回格式异常，请稍后重试。",
        code="LLM_INVALID_RESPONSE",
        status_code=502,
        retryable=True,
    )


class LLMService:
    """Multi-provider LLM service for 4S report generation."""

    def __init__(self, settings: Settings):
        self.settings = settings


    def _validate_face_assessment(self, assessment: Any) -> Optional[Dict[str, Any]]:
        return validate_face_assessment(assessment)


    def _public_style_result(self, style_result: Any) -> Dict[str, Any]:
        return public_style_result(style_result)


    def _finalize_report(
        self,
        report: Dict[str, Any],
        final_style: str,
        assessment: Optional[Dict[str, Any]],
    ):
        return finalize_visual_age_report(report, final_style, assessment)

    def generate_report(self, image_url: str) -> Dict[str, Any]:
        """Generate a 4S aesthetic report from an image URL (sync version)."""
        if self.settings.is_mock:
            return self._generate_mock(image_url)

        if self.settings.is_qwen:
            return self._call_two_stage_provider(
                base_url=self.settings.qwen_base_url,
                api_key=self.settings.dashscope_api_key,
                model=self.settings.qwen_model,
                image_url=image_url,
            )

        if self.settings.is_volcengine:
            return self._call_two_stage_provider(
                base_url=self.settings.ark_base_url,
                api_key=self.settings.ark_api_key,
                model=self.settings.ark_model,
                image_url=image_url,
            )

        raise ConfigurationError(f"未知 LLM_PROVIDER：{self.settings.llm_provider}")

    async def generate_report_async(self, image_url: str) -> Dict[str, Any]:
        """Generate a 4S aesthetic report from an image URL (async version)."""
        if self.settings.is_mock:
            return self._generate_mock(image_url)

        if self.settings.is_qwen:
            return await self._call_parallel_provider(
                base_url=self.settings.qwen_base_url,
                api_key=self.settings.dashscope_api_key,
                model=self.settings.qwen_model,
                image_url=image_url,
            )

        if self.settings.is_volcengine:
            return await self._call_parallel_provider(
                base_url=self.settings.ark_base_url,
                api_key=self.settings.ark_api_key,
                model=self.settings.ark_model,
                image_url=image_url,
            )

        raise ConfigurationError(f"未知 LLM_PROVIDER：{self.settings.llm_provider}")

    def _call_two_stage_provider(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        image_url: str,
        timeout: float = 90.0,
    ) -> Dict[str, Any]:
        """Original two-stage synchronous provider call."""
        if not api_key:
            raise ConfigurationError("缺少 API Key，请检查 .env。")
        if not model:
            raise ConfigurationError("缺少模型名称，请检查 .env。")

        client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        start = time.time()

        style_response = self._create_completion(
            client=client,
            model=model,
            image_url=image_url,
            system_prompt=STYLE_TOP3_SYSTEM_PROMPT,
            user_prompt=STYLE_TOP3_USER_PROMPT,
            max_tokens=1200,
            temperature=0.15,
        )

        style_content = style_response.choices[0].message.content or ""

        try:
            style_result = extract_json_from_text(style_content)
        except ValueError as exc:
            raise _invalid_response_error("Style Top3", style_content, exc) from exc

        face_assessment = self._validate_face_assessment(
            style_result.get("face_assessment")
        )
        style_top3 = self._extract_style_top3(style_result)
        final_style = style_top3[0]["label"]

        logger.info("Style Top3: %s", style_top3)
        logger.info("Final style for report: %s", final_style)

        report_user_prompt = build_report_user_prompt(
            final_style=final_style,
            style_top3=style_top3,
        )

        report_response = self._create_completion(
            client=client,
            model=model,
            image_url=image_url,
            system_prompt=REPORT_SYSTEM_PROMPT,
            user_prompt=report_user_prompt,
            max_tokens=1800,
            temperature=0.25,
        )

        duration_ms = int((time.time() - start) * 1000)
        report_content = report_response.choices[0].message.content or ""

        try:
            report = extract_json_from_text(report_content)
        except ValueError as exc:
            raise _invalid_response_error("完整报告", report_content, exc) from exc

        report, score_warnings, _calibration_audit = self._finalize_report(
            report,
            final_style,
            face_assessment,
        )

        if score_warnings:
            logger.warning("4S report score warnings: %s", score_warnings)

        usage = {
            "style_usage": style_response.usage.model_dump() if style_response.usage else None,
            "report_usage": report_response.usage.model_dump() if report_response.usage else None,
        }

        return {
            "report": report,
            "style_first_pass": {
                **self._public_style_result(style_result),
                "normalized_style_top3": style_top3,
                "final_style": final_style,
            },
            "raw_content": report_content,
            "raw_style_content": json.dumps(
                self._public_style_result(style_result),
                ensure_ascii=False,
            ),
            "duration_ms": duration_ms,
            "usage": usage,
            "score_warnings": score_warnings,
        }

    async def _call_parallel_provider(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        image_url: str,
        timeout: float = 90.0,
    ) -> Dict[str, Any]:
        """
        Parallel provider call (optimized workflow).

        Stage 1:
            - Style Top3 classification

        Stage 2 (parallel, after Style Top1 is fixed):
            - Style detail
            - Stype analysis
            - Subzone analysis
            - Struct analysis

        Stage 3:
            - Merge all results
        """
        if not api_key:
            raise ConfigurationError("缺少 API Key，请检查 .env。")
        if not model:
            raise ConfigurationError("缺少模型名称，请检查 .env。")

        client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        start = time.time()

        # ========= Stage 1: determine Style first =========
        style_response = await self._async_create_completion(
            client=client,
            model=model,
            image_url=image_url,
            system_prompt=STYLE_TOP3_SYSTEM_PROMPT,
            user_prompt=STYLE_TOP3_USER_PROMPT,
            max_tokens=1200,
            temperature=0.15,
        )

        style_content = style_response.choices[0].message.content or ""
        try:
            style_result = extract_json_from_text(style_content)
        except ValueError as exc:
            raise _invalid_response_error("Style Top3", style_content, exc) from exc

        face_assessment = self._validate_face_assessment(
            style_result.get("face_assessment")
        )
        style_top3 = self._extract_style_top3(style_result)
        final_style = style_top3[0]["label"]
        logger.info("Style Top3: %s", style_top3)
        logger.info("Final style for report: %s", final_style)

        # ========= Stage 2: all analyses receive final Style =========
        tasks = [
            self._async_create_completion(
                client=client,
                model=model,
                image_url=image_url,
                system_prompt=STYLE_DETAIL_SYSTEM_PROMPT,
                user_prompt=build_style_detail_user_prompt(
                    fixed_style=final_style,
                    style_top3=style_top3,
                ),
                max_tokens=600,
                temperature=0.20,
            ),
            self._async_create_completion(
                client=client,
                model=model,
                image_url=image_url,
                system_prompt=STYPE_SYSTEM_PROMPT,
                user_prompt=build_stype_user_prompt(final_style),
                max_tokens=500,
                temperature=0.20,
            ),
            self._async_create_completion(
                client=client,
                model=model,
                image_url=image_url,
                system_prompt=SUBZONE_SYSTEM_PROMPT,
                user_prompt=build_subzone_user_prompt(final_style),
                max_tokens=800,
                temperature=0.20,
            ),
            self._async_create_completion(
                client=client,
                model=model,
                image_url=image_url,
                system_prompt=STRUCT_SYSTEM_PROMPT,
                user_prompt=build_struct_user_prompt(final_style),
                max_tokens=600,
                temperature=0.20,
            ),
        ]
        (
            style_detail_response,
            stype_response,
            subzone_response,
            struct_response,
        ) = await asyncio.gather(*tasks)

        duration_ms = int((time.time() - start) * 1000)

        # ========= Stage 3: Merge results =========
        report = self._merge_4s_results(
            style_result=style_result,
            style_top3=style_top3,
            final_style=final_style,
            style_detail_response=style_detail_response,
            stype_response=stype_response,
            subzone_response=subzone_response,
            struct_response=struct_response,
        )

        # Strict validation, then retry only missing dimensions once.
        try:
            report, score_warnings, _calibration_audit = self._finalize_report(
                report,
                final_style,
                face_assessment,
            )
        except LLMCallError as exc:
            missing_dimensions = exc.details.get("missing_dimensions", [])
            if exc.code != "LLM_INVALID_RESPONSE" or not missing_dimensions:
                raise
            logger.warning("Retrying missing 4S dimensions once: %s", missing_dimensions)
            response_map = await retry_missing_dimensions_once(
                self._async_create_completion,
                missing_dimensions,
                client=client,
                model=model,
                image_url=image_url,
                final_style=final_style,
                style_top3=style_top3,
                responses={
                    "style": style_detail_response,
                    "stype": stype_response,
                    "subzone": subzone_response,
                    "struct": struct_response,
                },
            )
            style_detail_response = response_map["style"]
            stype_response = response_map["stype"]
            subzone_response = response_map["subzone"]
            struct_response = response_map["struct"]
            report = self._merge_4s_results(
                style_result=style_result,
                style_top3=style_top3,
                final_style=final_style,
                style_detail_response=style_detail_response,
                stype_response=stype_response,
                subzone_response=subzone_response,
                struct_response=struct_response,
            )
            report, score_warnings, _calibration_audit = self._finalize_report(
                report,
                final_style,
                face_assessment,
            )

        if score_warnings:
            logger.warning("4S report score warnings: %s", score_warnings)

        # Collect usage info
        usage = {
            "style_top3_usage": style_response.usage.model_dump() if style_response.usage else None,
            "stype_usage": stype_response.usage.model_dump() if stype_response.usage else None,
            "subzone_usage": subzone_response.usage.model_dump() if subzone_response.usage else None,
            "struct_usage": struct_response.usage.model_dump() if struct_response.usage else None,
            "style_detail_usage": style_detail_response.usage.model_dump() if style_detail_response.usage else None,
        }

        return {
            "report": report,
            "style_first_pass": {
                **self._public_style_result(style_result),
                "normalized_style_top3": style_top3,
                "final_style": final_style,
            },
            "raw_content": json.dumps(report, ensure_ascii=False),
            "raw_style_content": json.dumps(
                self._public_style_result(style_result),
                ensure_ascii=False,
            ),
            "duration_ms": duration_ms,
            "usage": usage,
            "score_warnings": score_warnings,
            "parallel_mode": True,
        }

    def _merge_4s_results(
        self,
        *,
        style_result: Dict[str, Any],
        style_top3: List[Dict[str, Any]],
        final_style: str,
        style_detail_response,
        stype_response,
        subzone_response,
        struct_response,
    ) -> Dict[str, Any]:
        """Merge parallel analysis results into a complete 4S report."""

        def extract_response_content(response) -> str:
            return response.choices[0].message.content or ""

        # Parse individual results
        stype_content = extract_response_content(stype_response)
        subzone_content = extract_response_content(subzone_response)
        struct_content = extract_response_content(struct_response)
        style_detail_content = extract_response_content(style_detail_response)

        try:
            stype_result = extract_json_from_text(stype_content)
        except ValueError as exc:
            raise _invalid_response_error("Stype", stype_content, exc) from exc

        try:
            subzone_result = extract_json_from_text(subzone_content)
        except ValueError as exc:
            raise _invalid_response_error("Subzone", subzone_content, exc) from exc

        try:
            struct_result = extract_json_from_text(struct_content)
        except ValueError as exc:
            raise _invalid_response_error("Struct", struct_content, exc) from exc

        try:
            style_detail_result = extract_json_from_text(style_detail_content)
        except ValueError as exc:
            raise _invalid_response_error("Style detail", style_detail_content, exc) from exc

        # Build merged report
        report = {
            "report_type": "4S 美学报告",
            "stype": stype_result.get("stype", {}),
            "style": style_detail_result.get("style", {}),
            "subzone": subzone_result.get("subzone", {}),
            "struct": struct_result.get("struct", {}),
        }

        # Ensure style fields are correct
        if isinstance(report.get("style"), dict):
            report["style"]["label"] = final_style
            report["style"]["dimension_name"] = "分型 Style"
            report["style"].pop("candidates", None)
            report["style"].pop("top3", None)
            report["style"].pop("style_top3", None)

        # Ensure stype dimension_name
        if isinstance(report.get("stype"), dict):
            report["stype"]["dimension_name"] = "分相 Stype"

        # Ensure subzone dimension_name
        if isinstance(report.get("subzone"), dict):
            report["subzone"]["dimension_name"] = "分区 Subzone"

        # Ensure struct dimension_name
        if isinstance(report.get("struct"), dict):
            report["struct"]["dimension_name"] = "分层 Struct"

        # Calculate radar scores from individual dimension scores
        report["radar_scores"] = {
            "stype": report.get("stype", {}).get("score", 0),
            "style": report.get("style", {}).get("score", 0),
            "subzone": report.get("subzone", {}).get("score", 0),
            "struct": report.get("struct", {}).get("score", 0),
        }

        # Generate project directions based on low-score zones
        project_directions = self._generate_project_directions(report)
        report["project_directions"] = project_directions

        # Generate aesthetic optimization directions
        aesthetic_optimization = self._generate_aesthetic_optimization(report)
        report["aesthetic_optimization"] = aesthetic_optimization

        # Add disclaimer
        report["disclaimer"] = "本报告由 AI 生成，仅作为美学体验参考，不作为专业医疗意见、处置依据或效果承诺。"

        return report

    def _extract_style_top3(self, style_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract and normalize Style Top3 from stage-1 result."""
        if not isinstance(style_result, dict):
            return DEFAULT_STYLE_TOP3

        raw_top3 = style_result.get("style_top3")

        if not isinstance(raw_top3, list):
            raw_top3 = style_result.get("top3")

        if isinstance(raw_top3, dict):
            raw_top3 = [raw_top3]

        if not isinstance(raw_top3, list):
            top1 = style_result.get("top1")
            if isinstance(top1, dict):
                raw_top3 = [top1]
            else:
                raw_top3 = []

        normalized: List[Dict[str, Any]] = []
        used_labels = set()

        for item in raw_top3:
            if not isinstance(item, dict):
                continue

            label = str(item.get("label", "")).strip()

            if label not in VALID_STYLE_LABELS:
                continue

            if label in used_labels:
                continue

            confidence = self._safe_confidence(item.get("confidence"), default=0.60)
            reason = str(item.get("reason") or item.get("evidence") or "").strip()

            matched_features = item.get("matched_features", [])
            if not isinstance(matched_features, list):
                matched_features = []

            normalized.append(
                {
                    "label": label,
                    "confidence": confidence,
                    "reason": reason or f"整体视觉特征较接近{label}。",
                    "matched_features": matched_features,
                }
            )
            used_labels.add(label)

        for item in DEFAULT_STYLE_TOP3:
            if len(normalized) >= 3:
                break
            if item["label"] not in used_labels:
                normalized.append(item)
                used_labels.add(item["label"])

        return normalized[:3]

    @staticmethod
    def _safe_confidence(value: Any, default: float = 0.60) -> float:
        """Normalize confidence to 0.0-1.0."""
        try:
            v = float(value)
        except Exception:
            return default

        if v > 1:
            v = v / 100.0

        return max(0.0, min(1.0, round(v, 2)))

    def _generate_project_directions(self, report: Dict[str, Any]) -> List[str]:
        """Generate project directions based on low-score zones and style type."""
        available_directions = [
            "肤质管理", "轮廓精致", "年轻态维护", "眉眼精致",
            "面部协调", "气质妆造", "发型优化", "容量饱满度",
            "结构支撑", "分区协调"
        ]

        style_label = report.get("style", {}).get("label", "")
        subzone = report.get("subzone", {})
        struct = report.get("struct", {})

        selected = []

        style_recommendations = {
            "甜美少女型": ["眉眼精致", "容量饱满度", "年轻态维护", "面部协调"],
            "魅力时尚型": ["轮廓精致", "面部协调", "气质妆造", "分区协调"],
            "盐系简洁型": ["轮廓精致", "肤质管理", "面部协调"],
            "温婉柔美型": ["容量饱满度", "面部协调", "肤质管理", "年轻态维护"],
            "自然优雅型": ["面部协调", "分区协调", "肤质管理"],
            "知性沉着型": ["轮廓精致", "面部协调", "气质妆造"],
            "浪漫性感型": ["面部协调", "轮廓精致", "气质妆造", "肤质管理"],
            "华丽高雅型": ["眉眼精致", "轮廓精致", "结构支撑", "面部协调"],
            "飒爽前卫型": ["轮廓精致", "结构支撑", "面部协调"],
        }

        if style_label in style_recommendations:
            selected.extend(style_recommendations[style_label][:2])

        zones = subzone.get("zones", [])
        low_score_zones = [z for z in zones if isinstance(z, dict) and z.get("score", 100) < 80]
        for zone in low_score_zones[:2]:
            zone_name = zone.get("zone", "")
            if zone_name == "额部":
                selected.append("发型优化")
            elif zone_name == "眉眼":
                selected.append("眉眼精致")
            elif zone_name == "中面部":
                selected.append("容量饱满度")
            elif zone_name == "鼻部":
                selected.append("轮廓精致")
            elif zone_name == "唇部":
                selected.append("气质妆造")
            elif zone_name == "下颌轮廓":
                selected.append("轮廓精致")

        layers = struct.get("layers", [])
        for layer in layers:
            if isinstance(layer, dict) and layer.get("score", 100) < 78:
                layer_name = layer.get("layer", "")
                if layer_name == "皮肤层":
                    selected.append("肤质管理")
                elif layer_name == "皮下组织层":
                    selected.append("容量饱满度")
                elif layer_name == "筋膜支撑层":
                    selected.append("结构支撑")
                elif layer_name == "骨骼轮廓层":
                    selected.append("轮廓精致")

        unique_selected = []
        seen = set()
        for d in selected:
            if d not in seen and d in available_directions:
                seen.add(d)
                unique_selected.append(d)

        return unique_selected[:4]

    def _generate_aesthetic_optimization(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Generate aesthetic optimization directions based on report data."""
        style_label = report.get("style", {}).get("label", "")
        subzone = report.get("subzone", {})
        struct = report.get("struct", {})

        directions = []

        zones = subzone.get("zones", [])
        low_score_zones = sorted(
            [z for z in zones if isinstance(z, dict) and z.get("score", 100) < 80],
            key=lambda x: x.get("score", 100)
        )[:2]

        for zone in low_score_zones:
            zone_name = zone.get("zone", "")
            optimization = zone.get("optimization", "")
            if optimization:
                directions.append(optimization)

        layers = struct.get("layers", [])
        low_score_layers = sorted(
            [l for l in layers if isinstance(l, dict) and l.get("score", 100) < 78],
            key=lambda x: x.get("score", 100)
        )[:2]

        for layer in low_score_layers:
            optimization = layer.get("optimization", "")
            if optimization:
                directions.append(optimization)

        style_direction_map = {
            "甜美少女型": "关注眉眼精致与容量饱满度的协调，强化元气亲和气质",
            "魅力时尚型": "关注轮廓精致与分区协调，提升都市摩登感",
            "盐系简洁型": "关注轮廓精致与肤质管理，保持清爽克制的少年感",
            "温婉柔美型": "关注容量饱满度与面部协调，维持温柔端庄气质",
            "自然优雅型": "关注面部协调与分区平衡，保持均衡舒展的自然感",
            "知性沉着型": "关注轮廓精致与气质妆造，强化理性沉静的知性气质",
            "浪漫性感型": "关注面部协调与气质妆造，突出成熟妩媚的女人味",
            "华丽高雅型": "关注眉眼精致与结构支撑，强化明艳大气的存在感",
            "飒爽前卫型": "关注轮廓精致与结构支撑，突出帅气犀利的骨感气质",
        }

        style_direction = style_direction_map.get(style_label, "")
        if style_direction:
            directions.insert(0, style_direction)

        summary_parts = []
        if style_label:
            summary_parts.append(f"围绕{style_label}气质")
        if low_score_zones:
            zone_names = [z.get("zone", "") for z in low_score_zones]
            summary_parts.append(f"重点关注{''.join(zone_names)}的协调")
        if low_score_layers:
            layer_names = [l.get("layer", "") for l in low_score_layers]
            summary_parts.append(f"兼顾{''.join(layer_names)}的状态维护")

        summary = "，".join(summary_parts) + "。" if summary_parts else ""

        return {
            "summary": summary,
            "directions": directions[:4],
        }

    def _generate_mock(self, image_url: str) -> Dict[str, Any]:
        """Generate a mock 4S report for local testing."""
        start = time.time()

        style_top3 = [
            {
                "label": "甜美少女型",
                "confidence": 0.82,
                "reason": "卧蚕、苹果肌和圆润唇共同形成亲和元气感。",
                "matched_features": ["卧蚕", "苹果肌", "圆润唇", "亲和元气"],
            },
            {
                "label": "温婉柔美型",
                "confidence": 0.68,
                "reason": "中面部柔和饱满，整体有温柔亲和感。",
                "matched_features": ["苹果肌", "柔和", "亲和"],
            },
            {
                "label": "自然优雅型",
                "confidence": 0.61,
                "reason": "脸型线条较流畅，五官比例较协调。",
                "matched_features": ["脸型流畅", "比例协调"],
            },
        ]

        final_style = style_top3[0]["label"]

        report = {
            "report_type": "4S 美学报告",
            "stype": {
                "dimension_name": "分相 Stype",
                "label": "复合型",
                "score": 82,
                "confidence": 0.78,
                "description": "整体呈现骨相与肉相共同作用的复合特征，轮廓自然，中面部柔和。",
                "evidence": [
                    "轮廓线条较自然",
                    "中面部柔和度较明显",
                    "皮肤质感影响整体状态",
                ],
            },
            "style": {
                "dimension_name": "分型 Style",
                "label": final_style,
                "score": 84,
                "confidence": 0.82,
                "description": "整体更接近甜美少女型，卧蚕、苹果肌与圆润唇共同形成亲和元气感。",
                "first_feature_evidence": [
                    "第一特征依据1：卧蚕轻微可见，苹果肌饱满，唇部圆润。",
                    "第一特征依据2：虽有柔和混合感，但整体更偏甜美亲和。",
                ],
                "keywords": ["甜美", "亲和", "元气"],
            },
            "subzone": {
                "dimension_name": "分区 Subzone",
                "score": 80,
                "summary": "面部分区整体协调，眉眼和中面部是主要视觉重点。",
                "zones": [
                    {
                        "zone": "额部",
                        "score": 78,
                        "status": "额部较平整",
                        "strength": "过渡自然",
                        "optimization": "关注发型衔接",
                    },
                    {
                        "zone": "眉眼",
                        "score": 84,
                        "status": "眉眼表达柔和",
                        "strength": "亲和力较强",
                        "optimization": "关注眼周清透",
                    },
                    {
                        "zone": "中面部",
                        "score": 83,
                        "status": "中面部较饱满",
                        "strength": "柔和度较好",
                        "optimization": "关注自然过渡",
                    },
                    {
                        "zone": "鼻部",
                        "score": 79,
                        "status": "鼻部比例协调",
                        "strength": "中轴自然",
                        "optimization": "关注整体平衡",
                    },
                    {
                        "zone": "唇部",
                        "score": 82,
                        "status": "唇部圆润自然",
                        "strength": "增强亲和气质",
                        "optimization": "关注妆造匹配",
                    },
                    {
                        "zone": "下颌轮廓",
                        "score": 76,
                        "status": "下颌线条自然",
                        "strength": "保留柔和观感",
                        "optimization": "关注轮廓清晰",
                    },
                ],
            },
            "struct": {
                "dimension_name": "分层 Struct",
                "score": 78,
                "summary": "结构层次整体自然，可关注肤质清透感和轮廓协调度。",
                "layers": [
                    {
                        "layer": "皮肤层",
                        "score": 78,
                        "status": "肤质影响清透感",
                        "optimization": "关注光泽均匀",
                    },
                    {
                        "layer": "皮下组织层",
                        "score": 80,
                        "status": "容量感较柔和",
                        "optimization": "关注自然饱满",
                    },
                    {
                        "layer": "筋膜支撑层",
                        "score": 76,
                        "status": "支撑感较自然",
                        "optimization": "关注紧致状态",
                    },
                    {
                        "layer": "骨骼轮廓层",
                        "score": 79,
                        "status": "轮廓基础协调",
                        "optimization": "关注比例统一",
                    },
                ],
            },
            "radar_scores": {
                "stype": 82,
                "style": 84,
                "subzone": 80,
                "struct": 78,
            },
            "aesthetic_optimization": {
                "summary": "建议围绕甜美亲和和自然协调进行优化，突出眉眼清透和中面部柔和感。",
                "directions": [
                    "关注肤质清透和气色统一",
                    "强化眉眼亲和表达",
                    "保持轮廓自然协调",
                ],
            },
            "project_directions": ["肤质管理", "眉眼精致", "分区协调"],
            "lead_cta": {
                "title": "领取你的专属4S美学方案",
                "text": "填写信息后，专业顾问将结合你的4S报告，为你提供一对一美学建议。",
                "button": "立即领取福利",
            },
            "disclaimer": "本报告由 AI 生成，仅作为美学体验参考，不作为专业医疗意见、处置依据或效果承诺。",
        }

        report, score_warnings, _calibration_audit = self._finalize_report(
            report,
            final_style,
            None,
        )

        return {
            "report": report,
            "style_first_pass": {
                "style_top3": style_top3,
                "final_style": final_style,
            },
            "raw_content": json.dumps(report, ensure_ascii=False),
            "raw_style_content": json.dumps(
                {"style_top3": style_top3},
                ensure_ascii=False,
            ),
            "duration_ms": int((time.time() - start) * 1000),
            "usage": None,
            "score_warnings": score_warnings,
        }

    def _create_completion(
        self,
        client: OpenAI,
        model: str,
        image_url: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1800,
        temperature: float = 0.25,
    ):
        """Create chat completion with fallback for enable_thinking (sync)."""
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {"type": "text", "text": user_prompt},
                ],
            },
        ]

        def call_once():
            try:
                return client.chat.completions.create(
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    extra_body={"enable_thinking": False},
                    messages=messages,
                )
            except Exception as exc:
                if "enable_thinking" not in str(exc) and "extra_body" not in str(exc):
                    raise
                return client.chat.completions.create(
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    messages=messages,
                )

        return retry_sync(call_once)

    async def _async_create_completion(
        self,
        client: AsyncOpenAI,
        model: str,
        image_url: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1800,
        temperature: float = 0.25,
    ):
        """Create chat completion with safe fallback and bounded async retry."""
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {"type": "text", "text": user_prompt},
                ],
            },
        ]

        async def call_once():
            try:
                return await client.chat.completions.create(
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    extra_body={"enable_thinking": False},
                    messages=messages,
                )
            except Exception as exc:
                if "enable_thinking" not in str(exc) and "extra_body" not in str(exc):
                    raise
                return await client.chat.completions.create(
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    messages=messages,
                )

        return await retry_async(call_once)
