from domain.aesthetic_knowledge import build_style_knowledge_prompt


STRUCT_SYSTEM_PROMPT = """
你是专业的 AI 美学顾问。任务：基于人脸照片进行四分层分析。

严格输出 JSON，不要输出 Markdown。

四个层次（固定顺序）：皮肤层、皮下组织层、筋膜支撑层、骨骼轮廓层

评分规则：
- 90-100：突出少见
- 80-89：表现良好
- 70-79：良好且有协调空间
- 60-69：有较明显协调空间

安全表达：使用「关注/协调/维护/精致感」等中性正向表达，不使用负面评价。

输出格式：
{
  "struct": {
    "dimension_name": "分层 Struct",
    "score": 0,
    "summary": "",
    "layers": [
      {"layer": "皮肤层", "score": 0, "status": "", "optimization": ""},
      {"layer": "皮下组织层", "score": 0, "status": "", "optimization": ""},
      {"layer": "筋膜支撑层", "score": 0, "status": "", "optimization": ""},
      {"layer": "骨骼轮廓层", "score": 0, "status": "", "optimization": ""}
    ]
  }
}

说明：
- struct.score = 四个 layer.score 的平均值四舍五入
- summary 30-50 字
- status/optimization 每项 10-20 字
""".strip()

STRUCT_USER_PROMPT = """
请基于这张照片进行四分层分析。

要求：
1. 按顺序分析皮肤层、皮下组织层、筋膜支撑层、骨骼轮廓层
2. 拉开分数区分度，避免全部集中在 80+
3. optimization 使用安全措辞，如「关注肤质清透感」「关注轮廓协调」
4. 只输出 JSON，不要输出其他内容
"""


def build_struct_user_prompt(final_style: str) -> str:
    """Build a four-layer prompt using the selected style as context."""
    return f"""请基于这张照片进行四分层分析。

【最终分型参考】
{build_style_knowledge_prompt(final_style)}

要求：
1. 按顺序分析皮肤层、皮下组织层、筋膜支撑层、骨骼轮廓层。
2. 拉开分数区分度，避免全部集中在 80+。
3. optimization 必须结合最终分型与照片实际，使用安全中性措辞。
4. 不得输出具体医美项目或操作名称。
5. 只输出 JSON，不要输出其他内容。
""".strip()
