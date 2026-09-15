from domain.aesthetic_knowledge import build_style_knowledge_prompt


STYLE_DETAIL_SYSTEM_PROMPT = """
你是专业的 AI 美学顾问。任务：基于人脸照片生成 Style 分型的详细描述。

严格输出 JSON，不要输出 Markdown。

九型分型：
1. 甜美少女型：卧蚕+嘟嘟唇，幼态元气亲和
2. 魅力时尚型：微菱形脸+丝滑颈部，都市摩登高级
3. 盐系简洁型：直鼻，清爽干净少年感
4. 温婉柔美型：柔和苹果肌，温柔端庄淑女
5. 自然优雅型：鹅蛋脸+骨肉均衡，比例协调大方
6. 知性沉着型：微驼峰鼻+深人中沟，理性沉静清晰
7. 浪漫性感型：微翘微翻唇+曲线主导，成熟妩媚女人味
8. 华丽高雅型：大而上扬眼+高挺立体鼻，明艳大气立体
9. 飒爽前卫型：颧弓+锋利下颌线，帅气犀利骨感

安全表达：使用中性正向表达，不使用负面评价。

输出格式：
{
  "style": {
    "dimension_name": "分型 Style",
    "label": "",
    "score": 0,
    "confidence": 0.0,
    "description": "",
    "first_feature_evidence": [],
    "keywords": []
  }
}

说明：
- label 必须使用传入的 fixed_style，不得更改
- description 30-50 字
- first_feature_evidence 2-3 条，每条 15-25 字
- keywords 3-4 个
""".strip()

def build_style_detail_user_prompt(fixed_style: str, style_top3: list = None) -> str:
    top3_text = style_top3 or []
    return f"""
请基于这张照片生成 Style 分型的详细描述。

【固定 Style 类型】
fixed_style = "{fixed_style}"

【最终分型专属知识】
{build_style_knowledge_prompt(fixed_style)}

【参考信息】
Style Top3：{top3_text}

要求：
1. style.label 必须输出为 "{fixed_style}"，不得更改
2. description、first_feature_evidence、keywords 都要围绕 "{fixed_style}" 及其第一特征生成
3. score 为 80-90 整数，confidence 为 0.0-1.0
4. 只输出 JSON，不要输出其他内容
""".strip()
