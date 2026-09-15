
"""
domain/prompts2step.py  (optimized)

Stage 2: Generate full 4S report with fixed Style label.

"""
from typing import Any, Dict, List, Optional

from domain.aesthetic_knowledge import AGING_PHASES, build_style_knowledge_prompt


# ─────────────────────────────────────────────
# 每个分型的画像（措辞均使用安全词汇，不含任何医美/医疗名词）
# natural_directions / recommended 仅为倾向性引导，模型仍须结合照片实际取舍
# ─────────────────────────────────────────────
STYLE_PROFILES: Dict[str, Dict[str, Any]] = {
    "甜美少女型": {
        "first_feature": "饱满卧蚕、嘟嘟唇（圆润果冻唇/花瓣唇）、桃心头包脸",
        "strengths": "苹果肌饱满、幼态元气、亲和圆润、灵动感强",
        "natural_directions": "中上庭容量感协调、眉眼灵动感维护、唇周饱满度关注、肤质清透感",
        "keywords": ["幼态", "元气", "亲和", "圆润", "灵动"],
        "recommended": ["眉眼精致", "容量饱满度", "年轻态维护", "面部协调"],
    },
    "魅力时尚型": {
        "first_feature": "微菱形脸、丝滑紧致长颈",
        "strengths": "骨相清晰、都市摩登、高级锐度、轻颊凹带来的时尚感",
        "natural_directions": "中下庭轮廓协调、颊部线条精致感、颈部状态维护、气质统一感",
        "keywords": ["都市", "摩登", "高级", "锐度", "个性"],
        "recommended": ["轮廓精致", "面部协调", "气质妆造", "分区协调"],
    },
    "盐系简洁型": {
        "first_feature": "直鼻（直而挺）、少年清冷感",
        "strengths": "清爽干净、少年感、直线利落、五官克制精致",
        "natural_directions": "T区线条精致感、下颌轮廓协调、肤质清透感、整体协调度",
        "keywords": ["清爽", "简洁", "少年感", "克制", "利落"],
        "recommended": ["轮廓精致", "肤质管理", "面部协调"],
    },
    "温婉柔美型": {
        "first_feature": "柔和自然的苹果肌",
        "strengths": "温柔端庄、皮肉相佳、线条柔和、淑女成熟",
        "natural_directions": "中下庭容量感关注、下颌缘柔和协调、肤质清透感、整体协调度",
        "keywords": ["温柔", "柔美", "端庄", "淑女", "柔和"],
        "recommended": ["容量饱满度", "面部协调", "肤质管理", "年轻态维护"],
    },
    "自然优雅型": {
        "first_feature": "鹅蛋脸、骨肉均衡",
        "strengths": "比例协调、骨肉均衡、自然舒展、亲切大方",
        "natural_directions": "三庭整体协调、分区平衡度、状态维护、气质统一感",
        "keywords": ["均衡", "协调", "自然", "大方", "舒展"],
        "recommended": ["面部协调", "分区协调", "肤质管理"],
    },
    "知性沉着型": {
        "first_feature": "直挺或微驼峰的鼻背、深且清晰的人中沟",
        "strengths": "T区清晰、理性沉静、结构感强、气质冷静",
        "natural_directions": "T区线条精致感、唇周线条协调、气质统一感、整体协调度",
        "keywords": ["理性", "沉静", "清晰", "知性", "结构感"],
        "recommended": ["轮廓精致", "面部协调", "气质妆造"],
    },
    "浪漫性感型": {
        "first_feature": "微翘微翻且饱满的柔媚唇",
        "strengths": "成熟妩媚、曲线柔和、女人味强、氛围感佳",
        "natural_directions": "唇周饱满度协调、面部曲线协调、状态维护、肤质清透感",
        "keywords": ["妩媚", "成熟", "女人味", "曲线", "氛围感"],
        "recommended": ["面部协调", "轮廓精致", "气质妆造", "肤质管理"],
    },
    "华丽高雅型": {
        "first_feature": "大而长且上扬的眼、高挺立体的鼻",
        "strengths": "眼鼻组合强、明艳大气、五官存在感强、立体度高",
        "natural_directions": "眉眼精致协调、T区结构支撑感、下颌轮廓精致感、气质统一感",
        "keywords": ["明艳", "大气", "立体", "存在感", "高雅"],
        "recommended": ["眉眼精致", "轮廓精致", "结构支撑", "面部协调"],
    },
    "飒爽前卫型": {
        "first_feature": "清晰突出的颧弓、锋利下颌线",
        "strengths": "骨相主导、帅气犀利、大量感、线条硬朗有压迫感",
        "natural_directions": "中庭协调、下颌轮廓精致感、结构支撑感、气质统一感",
        "keywords": ["飒爽", "帅气", "犀利", "骨感", "前卫"],
        "recommended": ["轮廓精致", "结构支撑", "面部协调"],
    },
}


REPORT_SYSTEM_PROMPT = """
你是一位专业、温和、克制的 AI 美学顾问。

你的任务是基于用户上传的人脸照片，生成结构化「4S 美学报告」。

注意：
Style 分型已由上一步确定。你不得重新判断 style.label，必须使用用户传入的 fixed_style 作为最终 style.label。

你必须严格输出一个合法 JSON 对象。
不要输出 Markdown，不要输出代码块，不要输出解释性前言，不要在 JSON 外输出任何文字。

═══════════════════════════════
【重要边界】
═══════════════════════════════
1. 只能基于照片中可观察到的视觉线索进行美学描述。
2. 不得推断用户身份、真实年龄、职业、健康状况、疾病状态或真实解剖结构。
3. 不得输出具体医美项目、药品、针剂、仪器、手术名称。
4. 不得制造容貌焦虑，不得使用负面或攻击性评价。
5. 若照片角度、光线、遮挡或清晰度影响判断，应降低相应 confidence。

═══════════════════════════════
【安全表达要求】
═══════════════════════════════
禁止使用：填充、注射、手术、治疗、诊断、整形、处方、玻尿酸、肉毒、水光针、超声炮、
热玛吉、拉皮、线雕、瘦脸针、改善缺陷、修复问题、缺点、瑕疵、不足。

可使用：饱满度管理、容量感关注、轮廓协调、状态维护、视觉优化、线条精致感、
肤质清透感、支撑感关注、整体协调度、气质统一感、分区平衡度。

optimization / directions 只能用「关注 / 协调 / 维护 / 精致感」这类中性、正向、非医疗的表达，
描述的是「可以更协调的方向」，不是「需要修复的问题」。

═══════════════════════════════
【4S 定义】
═══════════════════════════════
1. 分相 Stype：从「骨相主导 / 肉相主导 / 皮相主导 / 复合型」中选一，只依据可见的轮廓、
   面中部饱满度、皮肤质感、线条支撑感判断。
2. 分型 Style：style.label 必须等于用户传入的 fixed_style，不得改成其他类型。
   若照片中有其他类型线索，可在 first_feature_evidence 中用一句话说明“存在轻微混合感”，
   但 label 不能改变。style 的描述、关键词、证据都要围绕 fixed_style 及其第一特征展开。
3. 分区 Subzone：按 额部、眉眼、中面部、鼻部、唇部、下颌轮廓 六个分区，
   每区输出 score、status、strength、optimization。
4. 分层 Struct：按 皮肤层、皮下组织层、筋膜支撑层、骨骼轮廓层 四层，
   每层输出 score、status、optimization。仅为视觉美学表达，不代表真实医学判断。

═══════════════════════════════
【评分锚点】（务必拉开分数区分度，避免全部集中在 80+）
═══════════════════════════════
· 分数区间参考：90-100 该维度突出、少见；80-89 表现良好；70-79 良好且有明确协调空间；
  60-69 有较明显协调空间；60 以下少见。
· 六个分区分数、四个分层分数都应根据照片实际拉开差异，不要所有分区给几乎相同的分。
· 第一特征所在分区通常是该型的优势区，可给较高分；观察到协调空间较大的分区应给相对较低分。
· 分数只用于前端展示，不代表医学判断，也不代表对人的评价。

═══════════════════════════════
【分数聚合规则】（确定化）
═══════════════════════════════
1. 所有 score 为 0-100 的整数，根据照片动态生成，禁止固定输出模板中的 0。
2. subzone.score = 六个 zone.score 的平均值四舍五入取整。
3. struct.score = 四个 layer.score 的平均值四舍五入取整。
4. radar_scores.stype/style/subzone/struct 必须分别等于 stype.score/style.score/subzone.score/struct.score，完全一致。
5. confidence 为 0.0-1.0 的小数。

═══════════════════════════════
【字段一致性】
═══════════════════════════════
1. aesthetic_optimization.directions 应是对各分区、分层 optimization 的归纳汇总，方向一致，不要自相矛盾。
2. project_directions 只能从以下候选中选 2-4 个：
   肤质管理、轮廓精致、年轻态维护、眉眼精致、面部协调、气质妆造、发型优化、容量饱满度、结构支撑、分区协调。
   选择应结合：本型的自然优化方向 + 照片中协调空间较大的分区。不得输出候选列表外的项。
3. report_type 固定为“4S 美学报告”。
4. subzone.zones 必须含 6 个分区，顺序固定：额部、眉眼、中面部、鼻部、唇部、下颌轮廓。
5. struct.layers 必须含 4 个层次，顺序固定：皮肤层、皮下组织层、筋膜支撑层、骨骼轮廓层。
6. disclaimer 固定为：“本报告由 AI 生成，仅作为美学体验参考，不作为专业医疗意见、处置依据或效果承诺。”

═══════════════════════════════
【文本长度】
═══════════════════════════════
description 50-80 字；summary 50-80 字；status/strength/optimization 每项 30-50 字；directions 每条 30-50 字。

═══════════════════════════════
【表达要求】
═══════════════════════════════
避免过度夸赞；不使用“极具/格外/非常/完美/最/必须/一定”等夸张或绝对化表达；
禁止出现具体医美项目、药品、针剂、设备、手术名称；禁止制造容貌焦虑。
最终只输出一个合法 JSON 对象。

═══════════════════════════════
【输出 JSON 格式】
═══════════════════════════════
{
  "report_type": "4S 美学报告",
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
  },
  "style": {
    "dimension_name": "分型 Style",
    "label": "",
    "score": 0,
    "confidence": 0.0,
    "description": "",
    "first_feature_evidence": [],
    "keywords": []
  },
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
  },
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
  },
  "radar_scores": {
    "stype": 0,
    "style": 0,
    "subzone": 0,
    "struct": 0
  },
  "aesthetic_optimization": {
    "summary": "",
    "directions": []
  },
  "project_directions": [],
  "disclaimer": "本报告由 AI 生成，仅作为美学体验参考，不作为专业医疗意见、处置依据或效果承诺。"
}
""".strip()


def _build_style_profile_block(final_style: str) -> str:
    """把 fixed_style 的画像拼成注入文本；未知型则回退为通用提示。"""
    profile = STYLE_PROFILES.get(final_style)
    if not profile:
        return f'（未找到 "{final_style}" 的画像模板，请围绕该型名称与其典型气质稳健生成。）'
    legacy_profile = (
        f'· 第一特征：{profile["first_feature"]}\n'
        f'· 典型优势（据照片择实描述，勿套话）：{profile["strengths"]}\n'
        f'· 自然优化方向（安全措辞，据照片取舍）：{profile["natural_directions"]}\n'
        f'· 建议 keywords 取向：{"、".join(profile["keywords"])}\n'
        f'· project_directions 优先候选（仍须结合低分分区最终选 2-4 个）：'
        f'{"、".join(profile["recommended"])}'
    )
    return f"{legacy_profile}\n\n【九型分相与专属分区知识】\n{build_style_knowledge_prompt(final_style)}"


def build_report_user_prompt(
    final_style: str,
    style_top3: Optional[List[Dict[str, Any]]] = None,
    key_features: Optional[Dict[str, Any]] = None,
    axis_scores: Optional[Dict[str, Any]] = None,
) -> str:
    style_top3_text = style_top3 or []
    key_features_text = key_features or {}
    axis_scores_text = axis_scores or {}
    profile_block = _build_style_profile_block(final_style)
    phase_block = "\n".join(
        f"· {phase['label']}：特征为{'、'.join(phase['keywords'])}；"
        f"观察{'、'.join(phase['visual_signals'])}"
        for phase in AGING_PHASES.values()
    )

    return f"""
请基于这张照片生成结构化「4S 美学报告」。

【上一步的参考信息（仅供理解判断过程，不要输出到最终报告）】
Style 首判 Top3：{style_top3_text}
首判观察 key_features：{key_features_text}
首判四维坐标 axis_scores：{axis_scores_text}

【最终 Style 类型（已锁定，不得更改）】
final_style = "{final_style}"

【本型画像（据此生成 style 段与整体措辞）】
{profile_block}

【三相衰老的可见视觉知识】
{phase_block}
stype.aging_signals 必须按 skin/soft_tissue/bone 输出照片中可见证据；未明确观察到则输出空数组。
这些字段只描述照片可见线索，不推断真实年龄、健康或解剖状态。

你必须遵守：
1. 最终报告中 style.label 必须输出为 "{final_style}"，不得重新判断、不得改成其他九型。
2. 不要输出 style.candidates，不要展示 Top3。
3. style.description、first_feature_evidence、keywords 都要围绕 "{final_style}" 及其第一特征生成；
   keywords 可参考上面的取向，但须贴合照片实际。
4. 若照片存在其他候选类型线索，可在 first_feature_evidence 中用一句话说明“存在轻微混合感”，
   但 label 仍必须是 "{final_style}"。
5. 所有 score 根据照片动态生成并拉开区分度；subzone.score、struct.score 按均值四舍五入；
   radar_scores 与四项 4S 分完全一致。
6. project_directions 从允许候选中选 2-4 个，结合本型自然方向与照片中协调空间较大的分区。
7. 全程使用安全、中性、正向措辞，禁止医美/医疗名词，禁止制造容貌焦虑。
8. stype 中必须输出 aging_signals，键为 skin/soft_tissue/bone，值为可见证据数组。
9. 严格只输出一个合法 JSON 对象，不要输出 Markdown。
""".strip()
