"""Authoritative, compliance-safe knowledge for the nine aesthetic styles.

《九大气质分型·专属面部精细化改善方案》+ PDF 升单路径.

"""

from copy import deepcopy
from typing import Any, Dict


AGING_PHASES = {
    "skin": {
        "label": "皮相",
        "keywords": ["暗", "纹"],
        "visual_signals": ["光泽与色泽均匀度", "表面纹理与细腻度", "毛孔可见度"],
    },
    "soft_tissue": {
        "label": "肉相",
        "keywords": ["松", "凹"],
        "visual_signals": ["软组织平整度", "容量感与轻盈度", "轮廓清晰度"],
    },
    "bone": {
        "label": "骨相",
        "keywords": ["垮", "垂"],
        "visual_signals": ["轮廓承托感", "整体支撑感", "五官立体度"],
    },
}


STYLE_KNOWLEDGE: Dict[str, Dict[str, Any]] = {
    "甜美少女型": {
        "skin_stars": 3,
        "soft_tissue_stars": 4,
        "bone_stars": 3,
        "principle": "以柔和、丰盈且富有弹力的软组织突出元气感，肉相表达应远大于骨相表达，避免骨点过度显露",
        "first_feature": "饱满卧蚕、嘟嘟唇（圆润果冻唇/花瓣唇）、桃心头包脸",
        "zone_directions": {
            "额部": "关注上庭与额颞区的饱满协调，强化「头包脸」的柔和比例",
            "眉眼": "维护柔和圆弧眉形、微笑卧蚕的饱满灵动与浅开扇双眼皮的幼态感",
            "中面部": "关注苹果肌饱满圆润的元气感与面中柔和过渡",
            "鼻部": "保持鼻头短圆、鼻梁柔和适中，不追求高直立体",
            "唇部": "维护唇面饱满的果冻感、嘴角微扬与人中区的幼态比例",
            "下颌轮廓": "保持下巴圆润微翘、下庭留白紧凑，下颌缘紧致而不锋利",
        },
        "avoidance": ["避免骨点和下颌线过度锋利", "避免鼻唇线条过度锐利"],
        "style_protection": [
            "过于立体高耸的眉弓会削弱幼态柔和感",
            "尖锐鼻尖与偏薄唇形不符合甜美元气气质",
            "过于锋利清晰的下颌线会丢失少女圆润感",
        ],
        "priority_directions": ["眉眼精致", "容量饱满度", "年轻态维护", "面部协调"],
        "tiers": {"基础": ["容量饱满度", "年轻态维护"], "强化": ["眉眼精致", "面部协调"]},
        "priority_safe_directions": ["保持中上庭轻盈丰盈", "维护幼态柔和的整体连贯感"],
        "extra": "颈部纤细白皙感是本型加分项",
    },
    "魅力时尚型": {
        "skin_stars": 3,
        "soft_tissue_stars": 2,
        "bone_stars": 5,
        "principle": "苹果肌不宜过度饱满，适当保留颊部转折以维持时尚高级感",
        "first_feature": "微菱形脸、丝滑紧致长颈",
        "zone_directions": {
            "额部": "关注额颧宽度关系与微菱形轮廓，上庭线条平整利落",
            "眉眼": "维护微拱流线眉与眉峰的利落感，眼型纤长精致、弱化卧蚕",
            "中面部": "保留轻微颊部转折的高级感与面部留白，苹果肌不过度饱满",
            "鼻部": "保持鼻部精巧微翘、立体度适中不笨重",
            "唇部": "维护清晰唇线与均衡厚薄，不追求过度饱满",
            "下颌轮廓": "关注微方精巧下巴、清晰下颌线与颈颌衔接",
        },
        "avoidance": ["避免苹果肌和卧蚕过度饱满", "避免下巴过度圆润幼态"],
        "style_protection": [
            "苹果肌过度饱满会破坏清冷时尚的高级氛围",
            "过重的卧蚕与圆润短下巴不符合摩登气质",
        ],
        "priority_directions": ["轮廓精致", "面部协调", "气质妆造", "分区协调"],
        "tiers": {"基础": ["轮廓精致", "年轻态维护"], "强化": ["气质妆造", "分区协调"]},
        "priority_safe_directions": ["维护都市摩登的轻盈留白", "关注颈颌线条连贯度"],
        "extra": "颈部线条紧致流畅（天鹅颈感）是本型重要的气质载体，颈部状态维护价值高",
    },
    "盐系简洁型": {
        "skin_stars": 3,
        "soft_tissue_stars": 3,
        "bone_stars": 4,
        "principle": "软组织轻盈同时保留适度丰盈，呈现清爽克制的盐系观感",
        "first_feature": "干净利落的直鼻（直而挺）与少年清冷感",
        "zone_directions": {
            "额部": "保持上庭略长的清爽比例与瓜子脸线条",
            "眉眼": "维护平直浅眉、长杏仁眼与浅淡自然卧蚕的少年清爽感",
            "中面部": "关注软组织轻盈平整，避免厚重堆叠",
            "鼻部": "突出直而利落的鼻部中轴，鼻头不圆钝、不必过高",
            "唇部": "保持唇线清晰、整体偏薄利落，下唇略有厚度",
            "下颌轮廓": "维护短而微方、干净利落的下颌缘线条",
        },
        "avoidance": ["避免苹果肌和唇部过度圆润", "避免轮廓曲线过度柔软"],
        "style_protection": [
            "饱满苹果肌与圆润鼻头会丢失盐系少年清冷感",
            "过厚的唇形与柔和圆弧下颌不符合简洁利落气质",
        ],
        "priority_directions": ["轮廓精致", "肤质管理", "面部协调"],
        "tiers": {"基础": ["轮廓精致", "肤质管理"], "强化": ["眉眼精致", "面部协调"]},
        "priority_safe_directions": ["保持清爽克制的少年感", "关注面部软组织轻盈度"],
        "extra": "颈部干净清爽是本型必备",
    },
    "温婉柔美型": {
        "skin_stars": 4,
        "soft_tissue_stars": 4,
        "bone_stars": 2,
        "principle": "以柔和自然的苹果肌体现温润、优越且端庄的面部观感",
        "first_feature": "柔和自然的苹果肌",
        "zone_directions": {
            "额部": "保持上庭圆润饱满、线条平缓与鹅蛋脸过渡",
            "眉眼": "维护柔和弯月眉的平缓弧度与眼尾微扬的端庄柔和",
            "中面部": "关注苹果肌柔和自然的饱满度，面中过渡温润不突兀",
            "鼻部": "保持鼻部匀称协调、鼻尖圆润不尖翘",
            "唇部": "维护柔和唇线与均衡厚薄，唇峰不过分清晰锐利",
            "下颌轮廓": "保持带钝感的流畅下颌与精巧微圆下巴，无尖锐骨点感",
        },
        "avoidance": ["避免骨点、眉峰和下颌过度锋利", "避免大面积颊部凹陷感"],
        "style_protection": [
            "过于立体的鼻背线条会破坏温婉柔和的整体感",
            "锋利下颌与偏薄锐利的唇形不符合柔美端庄气质",
            "明显颊部凹陷会削弱温润亲和的氛围",
        ],
        "priority_directions": ["容量饱满度", "面部协调", "肤质管理", "年轻态维护"],
        "tiers": {"基础": ["容量饱满度", "肤质管理"], "强化": ["面部协调", "年轻态维护"]},
        "priority_safe_directions": ["维护温柔端庄的曲线连贯感", "关注中下庭柔和平整"],
        "extra": "口周平滑细腻的状态维护对本型气质贡献大",
    },
    "自然优雅型": {
        "skin_stars": 4,
        "soft_tissue_stars": 4,
        "bone_stars": 2,
        "principle": "骨肉均衡且肉相略多于骨相，保持直线与曲线平衡并突出自然和谐",
        "first_feature": "标准鹅蛋脸与骨肉均衡",
        "zone_directions": {
            "额部": "保持额颧颌比例均衡舒展、上庭平整协调",
            "眉眼": "维护平缓优美的弧形眉与端庄均衡的眼型，留白适中",
            "中面部": "关注骨肉均衡、面中平整，不臃肿也不凹陷",
            "鼻部": "保持鼻部协调匀称、立体度适中、鼻尖圆润平衡",
            "唇部": "维护柔和线条与均衡厚薄，不刻意饱满或单薄",
            "下颌轮廓": "保持下颌线流畅清晰且不过度锋利，颈部线条顺滑",
        },
        "avoidance": ["避免任何单一区域走向极端", "避免过度幼态或冷锐的结构表达"],
        "style_protection": [
            "过度幼态饱满或过度锋利的骨相感都会打破均衡和谐",
            "单一五官过度突出会破坏优雅的整体感",
        ],
        "priority_directions": ["面部协调", "分区协调", "肤质管理"],
        "tiers": {"基础": ["面部协调", "分区协调"], "强化": ["肤质管理", "年轻态维护"]},
        "priority_safe_directions": ["维护三庭五眼整体平衡", "保持骨肉与直曲自然协调"],
        "extra": "耳垂饱满圆润可增添优雅贵气感；全脸各分区的均衡度本身就是本型核心价值",
    },
    "知性沉着型": {
        "skin_stars": 3,
        "soft_tissue_stars": 3,
        "bone_stars": 4,
        "principle": "肉相略少于骨相，保留清晰T区、适度颊部转折与理性结构感",
        "first_feature": "直挺或微驼峰的鼻背与深且清晰的人中沟",
        "zone_directions": {
            "额部": "关注修长脸型与上中庭比例，T区起点清晰立体",
            "眉眼": "维护眉弓适度上扬的深邃感、眉形偏直有气场与沉静眼神，不宜饱满卧蚕",
            "中面部": "保留轻微颊部转折的干练感与T区清晰度，苹果肌不厚重",
            "鼻部": "突出直挺偏长的鼻背线条（可带轻微驼峰特征），鼻尖利落不圆钝",
            "唇部": "维护清晰人中沟与利落唇线，厚薄适中偏薄",
            "下颌轮廓": "保持下颌轻微骨点感与颏部轮廓立体，增添智性气场",
        },
        "avoidance": ["避免苹果肌和唇部过度饱满", "避免鼻部与下巴过度短圆"],
        "style_protection": [
            "苹果肌过度饱满与圆润唇形会削弱知性干练气场",
            "圆润短下巴与短小圆鼻不符合理性沉稳气质",
        ],
        "priority_directions": ["轮廓精致", "面部协调", "气质妆造"],
        "tiers": {"基础": ["轮廓精致", "面部协调"], "强化": ["气质妆造", "结构支撑"]},
        "priority_safe_directions": ["强化理性沉静的T区结构感", "关注口周线条清晰协调"],
        "extra": "颀长的颈部线条可放大知性气质",
    },
    "华丽高雅型": {
        "skin_stars": 3,
        "soft_tissue_stars": 4,
        "bone_stars": 3,
        "principle": "内外轮廓保持适度折叠度，内轮廓软组织平整轻盈并避免厚重堆叠",
        "first_feature": "大而长且上扬的眼与高挺立体的鼻",
        "zone_directions": {
            "额部": "保持窄瓜子脸与三庭均衡，上庭与眉弓衔接立体",
            "眉眼": "维护上扬落尾眉的舒展气场与睑裂修长、眼尾上扬的孤高精致感，卧蚕不厚重",
            "中面部": "关注内轮廓平整轻盈与清晰折叠度，无厚重堆叠",
            "鼻部": "突出高挺立体且利落的鼻部中轴，鼻头精致不圆钝",
            "唇部": "保持唇线清晰利落与厚薄均衡，不臃肿",
            "下颌轮廓": "维护精致尖翘下巴与清晰下颌缘，自带华贵气场",
        },
        "avoidance": ["避免软组织厚重堆叠", "避免五官短圆和轮廓钝化"],
        "style_protection": [
            "过度圆钝柔和的五官感会弱化华丽大气的气场",
            "面中过度饱满堆叠会失去高级折叠度",
        ],
        "priority_directions": ["眉眼精致", "轮廓精致", "结构支撑", "面部协调"],
        "tiers": {"基础": ["眉眼精致", "轮廓精致"], "强化": ["结构支撑", "面部协调"]},
        "priority_safe_directions": ["维护明艳大气的眼鼻组合", "关注内外轮廓折叠与轻盈度"],
        "extra": "微微昂首间的下颌缘清晰度是本型气场的点睛处",
    },
    "浪漫性感型": {
        "skin_stars": 3,
        "soft_tissue_stars": 5,
        "bone_stars": 2,
        "principle": "肉相略多于骨相，以柔和曲线为主并减少直线条的生硬感",
        "first_feature": "微翘微翻且饱满的柔媚唇",
        "zone_directions": {
            "额部": "保持椭圆脸与额颧颌曲线平衡，上庭线条平缓圆润",
            "眉眼": "维护柔和双C弧度眉与开扇型双眼皮、眼尾微扬的柔媚感",
            "中面部": "关注苹果肌平整与颧颊柔和过渡，弱化颧部锐度感",
            "鼻部": "保持鼻部长度适中、线条柔和，鼻头圆润不尖锐高耸",
            "唇部": "突出上唇微翻、上下唇饱满的柔媚唇形，唇线清晰",
            "下颌轮廓": "维护流畅紧致下颌与圆润微翘下巴，无尖锐感",
        },
        "avoidance": ["避免下颌、鼻尖和面中过度锋利凹陷", "避免唇部过薄过平"],
        "style_protection": [
            "锋利下颌与高尖立体鼻会丢失柔媚曲线氛围",
            "偏薄扁平的唇形与面中凹陷不符合浪漫丰盈气质",
        ],
        "priority_directions": ["面部协调", "轮廓精致", "气质妆造", "肤质管理"],
        "tiers": {"基础": ["面部协调", "肤质管理"], "强化": ["轮廓精致", "气质妆造"]},
        "priority_safe_directions": ["强化成熟柔媚的曲线表达", "关注唇周与面部曲线连贯"],
        "extra": "颈部顺滑与整体曲线流畅度是性感氛围的重要组成",
    },
    "飒爽前卫型": {
        "skin_stars": 2,
        "soft_tissue_stars": 3,
        "bone_stars": 5,
        "principle": "控制软组织占比并突出清晰骨相、颧弓与锋利下颌的力量感",
        "first_feature": "清晰突出的颧弓与锋利下颌线",
        "zone_directions": {
            "额部": "保持额颧颌均衡与中庭力量感，上庭平整利落",
            "眉眼": "维护上扬利落、线条偏直的眉形与长型上扬眼的凌厉清冷表达，无卧蚕",
            "中面部": "保留清晰颧弓骨相并控制软组织厚重感，面中轻盈平整即可",
            "鼻部": "保持鼻头偏锐利落、突出骨相锋利感，不必追求高挺",
            "唇部": "维护偏薄上唇、下唇略厚与清晰利落唇线，无柔媚曲线",
            "下颌轮廓": "突出锋利短方的下颌线条与锐利清晰的下颌缘",
        },
        "avoidance": ["避免苹果肌和唇部过度圆润饱满", "避免下颌轮廓过度柔和"],
        "style_protection": [
            "饱满苹果肌与圆润鼻头会完全丢失飒爽先锋气质",
            "柔和圆润的下颌处理与饱满唇形不符合凌厉帅气风格",
        ],
        "priority_directions": ["轮廓精致", "结构支撑", "面部协调"],
        "tiers": {"基础": ["轮廓精致", "结构支撑"], "强化": ["眉眼精致", "气质妆造"]},
        "priority_safe_directions": ["突出帅气犀利的骨相辨识度", "关注颧颌结构的清晰连贯"],
        "extra": "颈部平滑与下颌线的锐利感共同构成压迫式气场",
    },
}


def get_style_knowledge(style: str) -> Dict[str, Any]:
    """Return a defensive copy so callers cannot mutate the source of truth."""
    return deepcopy(STYLE_KNOWLEDGE.get(style, {}))


def build_style_reference(style: str) -> Dict[str, Any]:
    """Build the stable frontend representation for a style composition."""
    item = STYLE_KNOWLEDGE.get(style)
    if not item:
        return {"style": style, "composition": {}, "principle": ""}
    return {
        "style": style,
        "composition": {
            "skin": {"label": "皮相", "stars": item["skin_stars"], "max_stars": 5},
            "soft_tissue": {
                "label": "肉相",
                "stars": item["soft_tissue_stars"],
                "max_stars": 5,
            },
            "bone": {"label": "骨相", "stars": item["bone_stars"], "max_stars": 5},
        },
        "principle": item["principle"],
    }


def build_style_knowledge_prompt(style: str) -> str:
    """Format the selected style knowledge for model prompts."""
    item = STYLE_KNOWLEDGE.get(style)
    if not item:
        return f"最终分型：{style}。仅根据照片可见特征稳健分析。"
    zones = "\n".join(
        f"  · {name}：{text}" for name, text in item["zone_directions"].items()
    )
    protect = "\n".join(f"  · {p}" for p in item["style_protection"])
    tiers = item["tiers"]
    parts = [
        f"最终分型：{style}",
        f"皮相/肉相/骨相参考星级：{item['skin_stars']}/{item['soft_tissue_stars']}/{item['bone_stars']}（满分5星）",
        f"分型原则：{item['principle']}",
        f"第一特征：{item['first_feature']}",
        f"分区方向（zones[].optimization 与 aesthetic_optimization.directions 须与之方向一致，并贴合照片实际取舍）：\n{zones}",
        f"避免方向（模型内部约束）：{'；'.join(item['avoidance'])}",
        f"风格保护提示（style_protection 字段的生成依据，措辞正向、保护用户原有风格优势）：\n{protect}",
        f"方向分层（directions 须以【基础】/【气质强化】标注）：基础优化：{'、'.join(tiers['基础'])}；气质强化：{'、'.join(tiers['强化'])}",
    ]
    if item.get("extra"):
        parts.append(f"本型加分项：{item['extra']}")
    return "\n".join(parts)