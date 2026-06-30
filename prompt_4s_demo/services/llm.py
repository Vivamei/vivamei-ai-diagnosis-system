"""
services/llm.py

LLM calling service.
Supports mock, Qwen (DashScope), and Volcengine (Ark).
"""

import json
import time
from typing import Any

from openai import OpenAI

from core.config import Settings
from core.exceptions import ConfigurationError, LLMCallError
from domain.prompts import SYSTEM_PROMPT, USER_PROMPT
from domain.radar import normalize_4s_report
from utils.json import extract_json_from_text


class LLMService:
    """Multi-provider LLM service for 4S report generation."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def generate_report(self, image_url: str) -> dict[str, Any]:
        """Generate a 4S aesthetic report from an image URL."""
        if self.settings.is_mock:
            return self._generate_mock(image_url)
        if self.settings.is_qwen:
            return self._call_provider(
                base_url=self.settings.qwen_base_url,
                api_key=self.settings.dashscope_api_key,
                model=self.settings.qwen_model,
                image_url=image_url,
            )
        if self.settings.is_volcengine:
            return self._call_provider(
                base_url=self.settings.ark_base_url,
                api_key=self.settings.ark_api_key,
                model=self.settings.ark_model,
                image_url=image_url,
            )
        raise ConfigurationError(f"未知 LLM_PROVIDER：{self.settings.llm_provider}")

    def _generate_mock(self, image_url: str) -> dict[str, Any]:
        """Generate a mock 4S report for local testing."""
        start = time.time()
        report = {
            "report_type": "4S 美学报告",
            "stype": {
                "dimension_name": "分相 Stype",
                "label": "复合型",
                "score": 82,
                "confidence": 0.78,
                "description": "整体呈现骨相与肉相共同作用的复合特征，轮廓线条较自然，中面部有一定柔和感，皮肤质感对整体状态也有影响。",
                "evidence": ["轮廓线条较自然", "中面部柔和度较明显", "皮肤质感影响整体状态"],
            },
            "style": {
                "dimension_name": "分型 Style",
                "label": "温婉知性",
                "score": 86,
                "confidence": 0.85,
                "description": "整体气质偏柔和、亲和，眉眼表达自然，适合以温婉知性、干净耐看的方向强化个人风格。",
                "keywords": ["柔和", "亲和", "知性"],
            },
            "subzone": {
                "dimension_name": "分区 Subzone",
                "score": 80,
                "summary": "面部各分区整体协调度较好，眉眼和中面部是主要视觉重点，可继续关注轮廓线条与肤质清透感。",
                "zones": [
                    {"zone": "额部", "status": "额部整体较平整，视觉存在感适中。", "strength": "与整体脸型过渡自然。", "optimization": "可关注额部清爽度与发型衔接。"},
                    {"zone": "眉眼", "status": "眉眼表达较柔和，是气质呈现的重要区域。", "strength": "亲和力较强。", "optimization": "可关注眉眼清晰度与眼周状态。"},
                    {"zone": "中面部", "status": "中面部整体过渡较自然，影响年轻态观感。", "strength": "柔和度较好。", "optimization": "可关注饱满度与疲惫感管理。"},
                    {"zone": "鼻部", "status": "鼻部与整体比例较协调。", "strength": "中轴存在感自然。", "optimization": "可关注鼻部与中面部的整体平衡。"},
                    {"zone": "唇部", "status": "唇部影响气色和温柔感表达。", "strength": "增强亲和气质。", "optimization": "可关注唇色和妆造匹配。"},
                    {"zone": "下颌轮廓", "status": "下颌线条整体自然，不过分锐利。", "strength": "保留柔和观感。", "optimization": "可关注线条清晰度与侧脸协调。"},
                ],
            },
            "struct": {
                "dimension_name": "分层 Struct",
                "score": 78,
                "summary": "结构层次整体较自然，可从皮肤清透感、面部饱满度、紧致感和轮廓协调度综合优化。",
                "layers": [
                    {"layer": "皮肤层", "score": 78, "status": "皮肤层影响清透感与气色。", "optimization": "可关注肤色均匀度与光泽度。"},
                    {"layer": "皮下组织层", "score": 80, "status": "皮下组织层提供柔和饱满感。", "optimization": "可关注面中部自然饱满度。"},
                    {"layer": "筋膜支撑层", "score": 76, "status": "筋膜支撑层影响紧致感与线条走向。", "optimization": "可关注整体紧致感维护。"},
                    {"layer": "骨骼轮廓层", "score": 79, "status": "骨骼轮廓层影响脸部框架与辨识度。", "optimization": "可关注轮廓协调与比例统一。"},
                ],
            },
            "radar_scores": {"stype": 82, "style": 86, "subzone": 80, "struct": 78},
            "aesthetic_optimization": {
                "summary": "建议围绕自然协调和气质强化进行优化，优先关注肤质清透感、眉眼清晰度、中面部状态和轮廓线条的统一感。",
                "directions": [
                    "优先关注肤质管理，让整体气色更均匀清爽。",
                    "强化眉眼和发型妆造，使温婉知性气质更明确。",
                    "关注轮廓线条与中面部过渡，提升整体协调度。",
                ],
            },
            "project_directions": ["肤质管理", "眉眼精致", "分区协调", "轮廓精致"],
            "lead_cta": {
                "title": "领取你的专属4S美学方案",
                "text": "填写信息后，专业顾问将结合你的4S报告，为你提供一对一美学建议。",
                "button": "立即领取福利",
            },
            "disclaimer": "本报告由 AI 生成，仅作为美学体验参考，不作为专业医疗意见、处置依据或效果承诺。",
        }
        report = normalize_4s_report(report)
        return {
            "report": report,
            "raw_content": json.dumps(report, ensure_ascii=False),
            "duration_ms": int((time.time() - start) * 1000),
            "usage": None,
        }

    def _call_provider(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        image_url: str,
        timeout: float = 90.0,
    ) -> dict[str, Any]:
        """Call an OpenAI-compatible vision model."""
        if not api_key:
            raise ConfigurationError("缺少 API Key，请检查 .env。")
        if not model:
            raise ConfigurationError("缺少模型名称，请检查 .env。")

        client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        start = time.time()

        response = self._create_completion(client, model, image_url)
        duration_ms = int((time.time() - start) * 1000)
        content = response.choices[0].message.content

        try:
            report = extract_json_from_text(content)
        except ValueError as exc:
            raise LLMCallError(f"大模型输出 JSON 解析失败：{str(exc)}。原始输出：{content[:500]}")

        report = normalize_4s_report(report)

        return {
            "report": report,
            "raw_content": content,
            "duration_ms": duration_ms,
            "usage": response.usage.model_dump() if response.usage else None,
        }

    def _create_completion(self, client: OpenAI, model: str, image_url: str):
        """Create chat completion with fallback for enable_thinking."""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {"type": "text", "text": USER_PROMPT},
                ],
            },
        ]
        try:
            return client.chat.completions.create(
                model=model,
                temperature=0.35,
                max_tokens=1800,
                extra_body={"enable_thinking": False},
                messages=messages,
            )
        except Exception as exc:
            if "enable_thinking" in str(exc) or "extra_body" in str(exc):
                try:
                    return client.chat.completions.create(
                        model=model,
                        temperature=0.35,
                        max_tokens=1800,
                        messages=messages,
                    )
                except Exception as exc2:
                    raise LLMCallError(f"大模型调用失败：{str(exc2)}")
            raise LLMCallError(f"大模型调用失败：{str(exc)}")
