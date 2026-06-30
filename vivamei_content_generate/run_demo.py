"""
run_demo.py

CLI demo script using the new service layer.
Tests the full 4S analysis pipeline without starting the web server.
"""

import json

from core.config import get_settings
from services.analysis import AnalysisService


def main():
    settings = get_settings()
    print("=" * 80)
    print("AI 4S 美学顾问 — 企业级 Demo")
    print(f"当前模型服务商：{settings.llm_provider}")
    print("=" * 80)

    image_url = (
        "local://demo_face.jpg"
        if settings.is_mock
        else "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241022/emyrja/dog_and_girl.jpeg"
    )

    service = AnalysisService(settings)
    result = service.analyze_url(image_url)

    print("\n[1] 大模型 4S 报告生成完成：")
    print(json.dumps(result.get("report", {}), ensure_ascii=False, indent=2))

    print("\n[2] 合规检查结果：")
    print(json.dumps(result.get("safety", {}), ensure_ascii=False, indent=2))

    if not result.get("success"):
        print("\n分析失败，请检查日志。")
        return

    print("\n[3] 项目方向映射结果：")
    print(json.dumps(result.get("mapped_project_directions", []), ensure_ascii=False, indent=2))

    print("\n[4] 前端雷达图数据：")
    print(json.dumps(result.get("radar_chart", {}), ensure_ascii=False, indent=2))

    print("\n[5] 最终结果：")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
