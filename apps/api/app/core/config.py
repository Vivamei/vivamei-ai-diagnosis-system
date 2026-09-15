from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

# 全项目配置集中在根目录 config/。本地开发读 config/dev.env（绝对路径，脚本从任何
# CWD 启动都能读到）；Docker 镜像里该绝对路径不存在会被跳过，转而读 /app/.env
# （由 config/prod.baseline.env 在构建时 COPY），运行时环境变量优先级最高。
_parents = Path(__file__).resolve().parents
_ROOT = _parents[4] if len(_parents) > 4 else _parents[-1]
_DEV_ENV = _ROOT / "config" / "dev.env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_DEV_ENV), ".env"), case_sensitive=False, extra="ignore"
    )

    # App
    app_env: Literal["dev", "test", "prod"] = "dev"
    app_debug: bool = True
    app_base_url: str = "http://localhost:8080"
    web_base_url: str = "http://localhost:5173"
    # 跨域来源白名单，逗号分隔的完整 origin（含协议与端口）。留空 = 不挂 CORS 中间件。
    # 前端与 API 同域部署（Nginx 反代 /api）时本就无跨域，保持留空即可，不要无谓放开；
    # 仅当前端挂在独立域名（如 H5 走 CDN）时才填，浏览器才允许带 Authorization 的跨域请求。
    # 小程序不受同源策略约束，与此项无关（它看的是微信后台的服务器域名白名单）。
    cors_origins: str = ""

    # mock 放行名单（逗号分隔），可选值见 app/core/preflight.py 的 MOCK_NAMES：
    #   sms / wechat / llm / moderation / oss
    # 它既是「开关」也是「放行条」：列进来的子系统直接按 mock 跑（即使凭据已配齐），
    # 不必再去单独改 LLM_PROVIDER / OSS_ENABLED —— 一个子系统只由这一处决定。
    # 没列进来的子系统必须走真实服务，凭据缺失会让启动直接失败（fail-fast），
    # 避免「配置漏填 → 静默降级 → 线上发不出真短信/不调真模型」这类只有用户能发现的故障。
    # 所有环境同一套规则，只有 app_env == "test" 例外：自动化测试视同全 mock，
    # 跑 pytest 不用维护名单，也不会误发真短信 / 误传真 OSS。
    allow_mock: str = ""

    # DB / Cache
    database_url: str
    redis_url: str
    # 进程内共享的 Redis 连接池上限。SSE 流 replay + 创建/后台 runner 都从此池借还连接，
    # 突发高并发（如 800 人同时出报告）时 20 会被打满报 "Too many connections"，按并发调大。
    redis_max_connections: int = 200

    # DB 连接池（每进程一份）。总连接数 ≈ (db_pool_size + db_max_overflow) × uvicorn_workers，
    # 需 ≤ RDS max_connections。突发活动（如 200 人同时出报告）按并发调大，改完重启 api 生效。
    db_pool_size: int = 5
    db_max_overflow: int = 10
    # 池满时等空闲连接的最长秒数，超时抛错而非无限等待。
    db_pool_timeout: int = 30
    # uvicorn worker 进程数。仅由 Dockerfile CMD 的 ${UVICORN_WORKERS} 读取（此字段仅作
    # 文档与校验用）。多 worker 时进程内并发闸门 analyze_max_concurrency 变为「每进程」，
    # 全局并发 = uvicorn_workers × analyze_max_concurrency，排队位置也按进程独立计算。
    uvicorn_workers: int = 1

    # 管理员令牌：保护 /api/admin/* 数据导出接口（返回解密手机号等 PII）。
    # 留空则接口一律拒绝（fail-closed），避免未配置时裸奔。生产在外置 .env 设一个长随机串。
    admin_token: str = ""

    # JWT
    jwt_secret: str
    jwt_access_ttl_seconds: int = 3600
    # 刷新令牌有效期 = 用户「记住登录」的最长窗口。默认 7 天（604800s），符合营销/
    # 测评类低敏感 H5 的业内惯例；前端 AuthStore 也按同样天数控制本地留存，两者需一致。
    jwt_refresh_ttl_seconds: int = 604800

    # Phone crypto
    phone_dek_base64: str
    phone_hmac_key: str

    # 阿里云
    ali_access_key_id: str = ""
    ali_access_key_secret: str = ""
    ali_region: str = "cn-hangzhou"
    # OSS 总开关：默认关，本地一律走 /upload/local 文件直传。仅当真正接入 OSS
    # （STS AssumeRole 已实现且 bucket/role 为真实值）时在 prod 置 true。不能用
    # ali_access_key_id / oss_bucket 等推断——AK 与短信共用、dev.env 里 OSS 是占位假值。
    oss_enabled: bool = False
    oss_bucket: str = ""
    oss_endpoint: str = ""
    oss_internal_endpoint: str = ""
    # OSS 专用 AK：留空则回退用 ali_access_key_id/secret。给「OSS 用独立子账号 AK」的部署留口子。
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""
    # 公网访问基址（bucket 虚拟主机域名，如 https://rerna.oss-cn-beijing.aliyuncs.com）。
    # 远端 LLM 走公网拉图，签名 GET URL 用它；后端自身上传/回读走内网 oss_endpoint 省流量。
    oss_public_base_url: str = ""
    # STS role（可选）。填了才走「前端 STS 直传」；留空则走「后端代传 OSS」，只需 AK 即可。
    oss_sts_role_arn: str = ""
    oss_sts_ttl: int = 900
    # STS 服务接入点。留空则按 ali_region 拼 sts.<region>.aliyuncs.com；
    # 就近或走 VPC 内网 STS 时可在此显式指定（如 sts-vpc.cn-hangzhou.aliyuncs.com）。
    oss_sts_endpoint: str = ""
    # 配了 OSS 时，给 LLM 拉图的签名 URL 有效期（秒）。默认 10 分钟，够 LLM 拉完。
    oss_download_url_ttl: int = 600
    ali_green_region: str = "cn-shanghai"
    # 内容安全（阿里云 Green）总开关：默认关，走 mock 机审。与 OSS 同理，不能靠
    # ali_access_key_id 推断——AK 与短信共用，填了短信会误判审核为真、走进未实现分支
    # 使照片卡在 pending。仅真正接入 Green（imageScan/textScan 已实现）时置 true。
    moderation_enabled: bool = False
    ali_sms_sign: str = ""
    ali_sms_template_login: str = ""

    # 微信小程序。两者任一为空即进入 mock 模式：openid 由 wx.login 的 code 派生、
    # 手机号返回 sms_test_phone_prefix 打头的固定号，便于拿到正式 appid 前联调。
    wx_appid: str = ""
    wx_secret: str = ""
    # 微信绑定令牌有效期：wx/login 返回 needPhone 后，用户点「手机号授权」的容忍间隔。
    wx_bind_ttl_seconds: int = 300

    # 短信测试模式：未配短信模板（ali_sms_sign/ali_sms_template_login 任一为空）时启用。
    # 仅 sms_test_phone_prefix 开头的手机号可收到固定验证码 sms_test_code，其他号码被拒。
    sms_test_code: str = "100000"
    # 测试前缀取真实号段 133，前端手机号校验（1[3-9]）才放行；仅未配短信模板时生效。
    sms_test_phone_prefix: str = "133"

    # LLM 对接方式（按通信模式命名）：
    #   mock  —— 进程内 MockLLMProvider，读 mock/sample_report.json 伪流式，无需外部服务
    #   async —— 异步：与贵方 SSE 流式服务（/v1/analyze，text/event-stream）逐帧对接
    #   sync  —— 同步：贵方 /api/analyze-url|analyze-file 一次性返回整份报告
    #   queue —— 轮询：贵方 /api/analyze-url|analyze-file 只提交返回 job_id，本方轮询
    #            /api/analysis-jobs/{job_id} 直到 SUCCESS/FAILURE
    llm_provider: Literal["mock", "async", "sync", "queue"] = "mock"
    # 异步（async）SSE 服务基址
    llm_qwen_base_url: str = ""
    # 贵方服务基址（/analyze-url 契约），sync / queue 两种模式共用
    llm_sync_base_url: str = ""
    # 调用下游 LLM 的超时（秒）。真实出报告最慢约数分钟，默认 600（10 分钟）留足余量，
    # 避免长任务被 httpx 提前 ReadTimeout 打断。可在外置 .env 用 LLM_TIMEOUT_SECONDS 覆盖。
    llm_timeout_seconds: int = 600
    # queue（轮询）模式：贵方 /api/analyze-url 只提交任务返回 job_id，
    # 本方轮询 /api/analysis-jobs/{job_id} 直到 SUCCESS/FAILURE。下面是轮询间隔（秒）。
    llm_poll_interval_seconds: float = 2.0
    # 调下游 LLM 的 httpx 连接池上限（每 worker 一份，单例客户端共享）。每个在途分析在
    # submit→轮询 SUCCESS 期间全程占 1 条连接（最长 llm_timeout_seconds），突发高并发按
    # 每 worker 峰值在途数调大（外置 .env 可覆盖，改完重启 api 生效）。
    llm_http_max_connections: int = 200
    llm_http_max_keepalive: int = 50
    # 后台分析的进程内并发上限。超过则请求在页面内排队，逐个放行，避免瞬时打爆下游 LLM。
    # 应对活动峰值时按下游实际吞吐调整（外置 .env 可覆盖，改完重启 api 生效）。
    analyze_max_concurrency: int = 5
    # 重启重放窗口（秒）。分析走进程内 BackgroundTasks，worker 重启/崩溃会丢在途任务，DB 留下
    # 卡在 queued/streaming 的行。启动时扫这些行：created_at 在本窗口内的重新 dispatch 跑完；
    # 超窗口的（用户早已放弃）标记 failed 收尾。默认 1800s 与 SSE buffer TTL / LLM 超时对齐。
    analyze_recover_max_age_seconds: int = 1800
    # 仅 llm_provider=mock 时生效：mock 报告逐帧输出的节奏系数。1.0≈单份 24s（模拟真实
    # LLM 时序）；设 0 则 mock 瞬时返回，用于压测「除模型外程序自身」的并发上限。
    mock_frame_delay: float = 1.0

    # Rate limit
    rl_sms_ip_per_min: int = 5
    rl_sms_phone_per_min: int = 1
    rl_sms_phone_per_day: int = 10
    rl_analyze_per_hour: int = 3
    rl_analyze_per_day: int = 5

    # Photo
    photo_ttl_days: int = 10
    photo_max_bytes: int = 5_242_880

    # 前端「预计等待时长」提示（秒）。真实出报告约 2–3 分钟，可按实际在外置 .env 调整。
    analyze_eta_seconds: int = 150
    # 分析页固定文案（均可在外置 .env 调整，改完重启 api 即生效，无需重打 web 镜像）。
    analyze_title_preparing: str = "AI 分析准备中…"
    analyze_title_analyzing: str = "AI 正在为您分析…"
    analyze_subtitle: str = "分型 · 分相 · 分区 · 分层"
    # 等待期滚动提示，多条用「|」分隔
    analyze_wait_hints: str = (
        "正在读取面部轮廓与光影结构…"
        "|比对分型 / 分相 / 分区 / 分层四维模型…"
        "|结合个人特征生成美学建议…"
        "|即将完成，正在整理报告…"
    )
    analyze_wait_note: str = "请勿关闭页面"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allow_mock_list(self) -> list[str]:
        return [s.strip().lower() for s in self.allow_mock.split(",") if s.strip()]

    def is_mocked(self, name: str) -> bool:
        """该子系统是否按 mock 跑。name 取 preflight.MOCK_NAMES 之一。

        各 is_*_configured() 都会先问这里，所以列进 ALLOW_MOCK 就够了，
        不用再把 LLM_PROVIDER 改成 mock、把 OSS_ENABLED 改成 false。
        """
        return self.app_env == "test" or name in self.allow_mock_list

    @property
    def llm_provider_effective(self) -> str:
        """真正生效的 LLM 对接方式：被 mock 掉时恒为 mock，否则就是 LLM_PROVIDER。"""
        return "mock" if self.is_mocked("llm") else self.llm_provider


settings = Settings()
