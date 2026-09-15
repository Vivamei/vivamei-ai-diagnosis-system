from domain.aesthetic_knowledge import AGING_PHASES, build_style_knowledge_prompt


STYPE_SYSTEM_PROMPT = """
你是专业的 AI 美学顾问。任务：基于人脸照片判断分相 Stype。

严格输出 JSON，不要输出 Markdown。

分相类型（四选一）：
- 骨相主导：骨骼轮廓清晰，线条硬朗，骨感明显
- 肉相主导：软组织饱满，线条柔和，圆润感强  
- 皮相主导：皮肤质感优秀，光泽均匀，肤质细腻
- 复合型：骨相、肉相、皮相特征混合，无明显主导

安全表达：只能基于可见视觉线索描述，不推断健康状况，不用负面评价。

输出格式：
{
  "stype": {
    "dimension_name": "分相 Stype",
    "label": "",
    "score": 0,
    "confidence": 0.0,
    "description": "",
    "evidence": [],
    "aging_signals": {
      "skin": [],
      "soft_tissue": [],
      "bone": []
    }
  }
}
""".strip()

STYPE_USER_PROMPT = """
请基于这张照片判断分相 Stype。

要求：
1. 从「骨相主导 / 肉相主导 / 皮相主导 / 复合型」中选一
2. score 为 0-100 整数，confidence 为 0.0-1.0
3. description 30-50 字，evidence 2-3 条，每条 10-20 字
4. 只输出 JSON，不要输出其他内容
"""


def build_stype_user_prompt(final_style: str) -> str:
    """Build a Stype prompt aware of the already selected Style."""
    phase_lines = []
    for phase in AGING_PHASES.values():
        phase_lines.append(
            f"- {phase['label']}：特征为{'、'.join(phase['keywords'])}；"
            f"观察{'、'.join(phase['visual_signals'])}"
        )
    return f"""请基于照片判断分相 Stype，并识别三相可见信号。

【最终分型参考】
{build_style_knowledge_prompt(final_style)}

【三相视觉定义】
{chr(10).join(phase_lines)}

要求：
1. stype.label 仍从「骨相主导 / 肉相主导 / 皮相主导 / 复合型」中选择，表示照片当前可见状态。
2. score 为 0-100 整数，confidence 为 0.0-1.0。
3. description 30-50 字，evidence 2-3 条，每条 10-20 字。
4. aging_signals 按 skin/soft_tissue/bone 输出照片中可见证据；未明确观察到则输出空数组。
5. 分型星级是该气质类型的审美参考，不等同于照片当前状态，不得据此虚构证据。
6. 只输出 JSON，不要输出其他内容。
""".strip()
