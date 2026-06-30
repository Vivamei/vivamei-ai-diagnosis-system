# AI 4S 美学顾问 Prompt 实现版

这个版本用于验证甲方最新需求：

> 上传人脸照片 → 基础质检 → 调用多模态大模型 → 输出结构化 4S 美学报告 → 合规过滤 → 生成 4S 雷达图数据 → 项目方向映射 → 返回前端 JSON

## 4S 输出内容

- **Stype 分相**：骨相主导 / 肉相主导 / 皮相主导 / 复合型
- **Style 分型**：温婉知性 / 清冷高级 / 明艳大气 / 甜美灵动等气质风格
- **Subzone 分区**：额部、眉眼、中面部、鼻部、唇部、下颌轮廓
- **Struct 分层**：皮肤层、皮下组织层、筋膜支撑层、骨骼轮廓层
- **4S 雷达图**：`radar_chart.labels` + `radar_chart.values`
- **美学优化方向**：文字版方向建议，不输出具体医美项目

## 运行

```bash
python -m pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app:app --reload
```

打开：

```text
http://127.0.0.1:8000/docs
```

## .env 示例

```env
LLM_PROVIDER=qwen
DASHSCOPE_API_KEY=sk-ws-你的key
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen3.7-plus

ARK_API_KEY=
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
ARK_MODEL=

PUBLIC_BASE_URL=
HOST=0.0.0.0
PORT=8000
```

如果模型不支持 `enable_thinking=False`，代码会自动降级重试。

## 测试 /analyze-url

```json
{
  "image_url": "https://img0.baidu.com/it/u=2007626721,1807681470&fm=253&fmt=auto&app=138&f=JPEG?w=500&h=837",
  "user_id": "test_001"
}
```

## 前端雷达图字段

后端返回：

```json
"radar_chart": {
  "labels": ["分相 Stype", "分型 Style", "分区 Subzone", "分层 Struct"],
  "keys": ["stype", "style", "subzone", "struct"],
  "values": [82, 86, 80, 78],
  "max": 100
}
```

前端只需要用 `labels` 和 `values` 画雷达图。

## 当前版本边界

本版本已经完成 4S 报告结构和雷达图数据输出，但仍是 Prompt 版：

- 人脸质量检测仍是基础图片格式/分辨率检查；正式上线建议接入腾讯云/百度人脸检测或 MediaPipe。
- OSS 上传和临时 URL 生成尚未内置；正式上线应将本地图片上传到 OSS，生成临时 URL，再调用模型，分析后删除原图。
- 内容安全目前是本地敏感词规则；正式上线建议叠加内容安全 API 和人工审核。
