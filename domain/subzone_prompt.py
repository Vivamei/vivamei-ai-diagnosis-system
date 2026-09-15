from domain.aesthetic_knowledge import build_style_knowledge_prompt


SUBZONE_SYSTEM_PROMPT = """
你是专业的 AI 美学顾问。任务：基于人脸照片进行六分区分析。

严格输出 JSON，不要输出 Markdown。

六个分区（固定顺序）：额部、眉眼、中面部、鼻部、唇部、下颌轮廓

评分规则：
- 90-100：突出少见
- 80-89：表现良好
- 70-79：良好且有协调空间
- 60-69：有较明显协调空间

安全表达：使用「关注/协调/维护/精致感」等中性正向表达，不使用负面评价。

输出格式：
{
  "subzone": {
    "dimension_name": "分区 Subzone",
    "score": 0,
    "summary": "",
    "zones": [
      {"zone": "额部", "score": 0, "status": "", "strength": "", "optimization": ""},
      {"zone": "眉眼", "score": 0, "status": "", "strength": "", "optimization": ""},
      {"zone": "中面部", "score": 0, "status": "", "strength": "", "optimization": ""},
      {"zone": "鼻部", "score": 0, "status": "", "strength": "", "optimization": ""},
      {"zone": "唇部", "score": 0, "status": "", "strength": "", "optimization": ""},
      {"zone": "下颌轮廓", "score": 0, "status": "", "strength": "", "optimization": ""}
    ]
  }
}

说明：
- subzone.score = 六个 zone.score 的平均值四舍五入
- summary 30-50 字
- status/strength/optimization 每项 10-20 字
""".strip()

SUBZONE_USER_PROMPT = """
请基于这张照片进行六分区分析。

要求：
1. 按顺序分析额部、眉眼、中面部、鼻部、唇部、下颌轮廓
2. 拉开分数区分度，避免全部集中在 80+
3. optimization 使用安全措辞，如「关注轮廓协调」「关注饱满度」
4. 只输出 JSON，不要输出其他内容
"""


def build_subzone_user_prompt(final_style: str) -> str:
    """Build a six-zone prompt using the selected style's safe directions."""
    return f"""请基于这张照片进行六分区分析。

【最终分型参考】
{build_style_knowledge_prompt(final_style)}

要求：
1. 按顺序分析额部、眉眼、中面部、鼻部、唇部、下颌轮廓。
2. 拉开分数区分度，避免全部集中在 80+。
3. optimization 必须结合最终分型的对应分区方向与照片实际，使用安全中性措辞。
4. 不得输出具体医美项目或操作名称。
5. 只输出 JSON，不要输出其他内容。
""".strip()
