"""启动自检：把「配置漏填 → 静默降级成 mock」变成一次显式的启动期决策。

各子系统本来就有各自的降级开关（短信没配模板发假验证码、微信没配 appid 造假 openid、
LLM_PROVIDER=mock 读本地 json…），单看都合理，合起来的问题是：**降级只打一行 warning**，
线上漏配一项没人会发现，直到用户收不到短信才被动暴露。

这里把所有降级点汇总到一处，**所有环境同一套规则**：
  - 仍在 mock 且不在 ALLOW_MOCK 名单里的，直接抛 RuntimeError 拒绝启动。
    列进 ALLOW_MOCK = 明知故犯并接受后果（如小程序内测期的 wechat）。
  - 例外：app_env == test 视同全 mock 放行，跑 pytest 不用维护名单。
  - 占位配置检查（域名/JWT_SECRET 等）只在 app_env == prod 生效：dev 本来就用
    localhost 和模板密钥，在那里报错纯属噪音。

新人零配置起项目的办法不是「非 prod 不校验」，而是 dev.env.example 里预先填好
ALLOW_MOCK=sms,wechat,llm,moderation,oss —— 走哪条路永远写在配置里，看得见。

同时提供 CLI，可在滚容器之前先跑一次预检，配置错就不动线上：
    docker compose -f docker-compose.ecs.yml run --rm api python -m app.core.preflight
"""

from loguru import logger

from app.core.config import settings

# 生产里不该出现的占位符（大小写不敏感），来自各 *.example 模板
_PLACEHOLDERS = ("your-domain.com", "your-llm-endpoint", "change-me", "replace", "localhost")

# ALLOW_MOCK 的合法取值，与 collect_mock_subsystems 的 key 一一对应
MOCK_NAMES = ("sms", "wechat", "llm", "moderation", "oss")


def collect_mock_subsystems() -> dict[str, str]:
    """返回 {子系统: 当前处于 mock 的后果}，只含真正在 mock 的项。

    延迟 import services，避免 core 与 services 形成 import 环。
    """
    from app.services.moderation import is_moderation_configured
    from app.services.oss import is_oss_configured
    from app.services.sms import is_sms_configured
    from app.services.wechat import is_wx_configured

    mocks: dict[str, str] = {}

    if not is_sms_configured():
        mocks["sms"] = (
            f"不发真实短信：仅 {settings.sms_test_phone_prefix} 开头的手机号能登录，"
            f"验证码恒为 {settings.sms_test_code}（缺 ALI_ACCESS_KEY_ID/SECRET/"
            f"ALI_SMS_SIGN/ALI_SMS_TEMPLATE_LOGIN 之一）"
        )
    if not is_wx_configured():
        mocks["wechat"] = (
            "不调微信开放接口：openid 由 wx.login 的 code 派生（换台机器就变），"
            f"授权手机号返回 {settings.sms_test_phone_prefix} 开头的假号"
            "（缺 WX_APPID / WX_SECRET）"
        )
    if settings.llm_provider_effective == "mock":
        mocks["llm"] = "不调真实模型：所有报告都读 mock/sample_report.json，内容与本人无关"
    if not is_moderation_configured():
        mocks["moderation"] = (
            "不调阿里云内容安全：图片只按 object_key 含 REJECT 判违规、"
            "文本只匹配几个固定词，等同没有机审"
        )
    if not is_oss_configured():
        mocks["oss"] = (
            "不上传 OSS：原图落本机 var/uploads/，容器重建即丢，且多实例之间互相读不到"
        )
    return mocks


def collect_config_errors() -> list[str]:
    """生产环境下必然导致线上功能不可用的配置错误（与 mock 无关，一律不可放行）。"""
    errors: list[str] = []

    for field in ("app_base_url", "web_base_url"):
        value = getattr(settings, field)
        hit = next((p for p in _PLACEHOLDERS if p in value.lower()), None)
        if hit:
            errors.append(f"{field.upper()}={value} 仍是占位/本机地址（命中 {hit!r}）")

    if settings.llm_provider_effective in ("sync", "queue"):
        url = settings.llm_sync_base_url
        if not url or any(p in url.lower() for p in _PLACEHOLDERS):
            errors.append(
                f"LLM_PROVIDER={settings.llm_provider} 需要 LLM_SYNC_BASE_URL 指向真实服务，"
                f"当前为 {url or '(空)'}"
            )
    elif settings.llm_provider_effective == "async":
        url = settings.llm_qwen_base_url
        if not url or any(p in url.lower() for p in _PLACEHOLDERS):
            errors.append(f"LLM_PROVIDER=async 需要 LLM_QWEN_BASE_URL，当前为 {url or '(空)'}")

    if any(p in settings.jwt_secret.lower() for p in _PLACEHOLDERS):
        errors.append("JWT_SECRET 仍是模板占位串，签出的令牌任何人都能伪造")

    return errors


def run_preflight() -> None:
    """启动自检。有未放行的 mock 或（生产下的）配置错误则抛 RuntimeError（fail-fast）。"""
    # 自动化测试视同全 mock 放行：跑 pytest 不用维护 ALLOW_MOCK 名单。
    if settings.app_env == "test":
        return

    mocks = collect_mock_subsystems()
    is_prod = settings.app_env == "prod"

    allowed = set(settings.allow_mock_list)
    unknown = allowed - set(MOCK_NAMES)
    if unknown:
        logger.warning(f"[preflight] ALLOW_MOCK 含未知项 {'、'.join(sorted(unknown))}，已忽略")

    blocked = {n: e for n, e in mocks.items() if n not in allowed}
    for name in (n for n in mocks if n in allowed):
        logger.warning(f"[preflight] 显式放行 mock:{name} —— {mocks[name]}")

    # 占位符/密钥检查只在生产做：dev 用 localhost 和模板 JWT_SECRET 是正常的。
    errors = collect_config_errors() if is_prod else []
    if is_prod:
        if not settings.admin_token:
            logger.warning("[preflight] ADMIN_TOKEN 为空，/api/admin/* 将一律拒绝（fail-closed）")
        if settings.app_debug:
            logger.warning("[preflight] APP_DEBUG=true，生产建议置 false 以免日志泄露细节")

    if blocked or errors:
        lines = [f"  - {n}：{e}" for n, e in blocked.items()]
        lines += [f"  - {e}" for e in errors]
        hint = (
            f"\n如确认这些子系统就是要走 mock，把名字加进 ALLOW_MOCK（当前 "
            f"{settings.allow_mock or '(空)'}），例如 "
            f"ALLOW_MOCK={','.join(sorted(set(settings.allow_mock_list) | set(blocked)))}"
            if blocked
            else ""
        )
        raise RuntimeError(
            f"启动自检未通过（APP_ENV={settings.app_env}）：\n" + "\n".join(lines) + hint
        )

    logger.info(f"[preflight] 配置自检通过（APP_ENV={settings.app_env}）")


def main() -> int:
    """CLI：部署前预检。打印报告，有问题返回非 0。"""
    import sys

    from app.core.logging import configure_logging

    # Windows 控制台默认 cp1252/GBK，中文报告会 UnicodeEncodeError
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    configure_logging(level="INFO")
    mocks = collect_mock_subsystems()
    print(f"APP_ENV = {settings.app_env}")
    print(f"ALLOW_MOCK = {settings.allow_mock or '(空)'}")
    print("--- mock 子系统 ---")
    print("\n".join(f"  {n}: {e}" for n, e in mocks.items()) if mocks else "  （无，全部走真实服务）")
    try:
        run_preflight()
    except RuntimeError as exc:
        print(f"\n[FAIL] {exc}")
        return 1
    print("\n[OK] 自检通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
