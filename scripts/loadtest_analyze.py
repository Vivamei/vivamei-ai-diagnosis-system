#!/usr/bin/env python3
"""venus-4s 报告生成压测：验证「N 个学员在 D 秒内完成报告生成」。

设计（两阶段，隔离出真正想压的 LLM 并发路径）：
  阶段 1「准备」：每个虚拟用户走完 登录 → 传图 → 注册照片，拿到 photoId。
                 用小并发 + 退避，避开 SMS 的 IP/手机号限流。此阶段不计时。
  阶段 2「突发」：同一时刻并发触发全部 analyze，逐个消费 SSE 到 done/error。
                 只测「建 analyze → 报告 done」这段，即报告生成的真实吞吐。

为什么分两阶段：SMS 有 IP 每分钟限流（rl_sms_ip_per_min，默认 5），单机 200 并发登录
会被 429 打散；而我们真正要验证的是「LLM 并发能否 2 分钟出 200 份」。把登录/传图挪到
不计时的准备阶段，突发阶段只打 analyze，测得的数才干净。

用法：
    poetry run python scripts/loadtest_analyze.py \
        --base-url http://localhost:8080 \
        --concurrency 200 \
        --deadline 120

    # 压真实 LLM（llm_provider=qwen/qwen-sync）时务必传一张真人脸图：
    poetry run python scripts/loadtest_analyze.py --image /path/to/face.jpg -c 200

被测端需临时放宽限流（否则准备阶段很慢、突发阶段被 429）：
    RL_SMS_IP_PER_MIN=100000  RL_ANALYZE_PER_HOUR=100000  RL_ANALYZE_PER_DAY=100000
准备阶段仍会自动对 429 退避重试，但放宽后跑得快很多。

依赖：httpx（api 项目已含）。在 apps/api 下用 poetry 跑，或 `pip install httpx`。
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import random
import statistics
import time
from dataclasses import dataclass, field

import httpx

# 1x1 像素的最小合法 JPEG（够 mock/审核跑通；真实 LLM 请用 --image 传真人脸图）。
_TINY_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8U"
    "HRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA"
    "/8QAFAABAAAAAAAAAAAAAAAAAAAAC//EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEA"
    "AD8A0s8g/9k="
)


@dataclass
class VU:
    """一个虚拟学员的全程记录。"""

    idx: int
    phone: str
    token: str | None = None
    photo_id: int | None = None
    # 阶段 2 计时
    analyze_start: float | None = None
    done_at: float | None = None
    ok: bool = False
    fail_reason: str | None = None


@dataclass
class Stats:
    prepared: int = 0
    prepare_failed: int = 0
    done_ok: int = 0
    done_fail: int = 0
    within_deadline: int = 0
    durations: list[float] = field(default_factory=list)  # analyze→done 秒
    fail_reasons: dict[str, int] = field(default_factory=dict)

    def add_fail(self, reason: str) -> None:
        self.fail_reasons[reason] = self.fail_reasons.get(reason, 0) + 1


def _pctl(xs: list[float], p: float) -> float:
    if not xs:
        return float("nan")
    xs = sorted(xs)
    k = max(0, min(len(xs) - 1, int(round((p / 100) * (len(xs) - 1)))))
    return xs[k]


async def _retry_429(coro_factory, *, tries: int, base_sleep: float):
    """对 429 做指数退避重试。coro_factory 每次返回一个新的 awaitable。"""
    last = None
    for i in range(tries):
        resp = await coro_factory()
        if resp.status_code != 429:
            return resp
        last = resp
        await asyncio.sleep(base_sleep * (2**i) + random.uniform(0, 0.5))
    return last


async def prepare_vu(client: httpx.AsyncClient, vu: VU, args) -> None:
    """阶段 1：登录 → 传图 → 注册照片。失败则标 fail_reason。"""
    # 1) 发验证码（测试模式：133 开头手机号收到固定码 sms_test_code）
    r = await _retry_429(
        lambda: client.post(
            "/api/auth/sms/send", json={"phone": vu.phone, "scene": "login"}
        ),
        tries=6,
        base_sleep=1.0,
    )
    if r.status_code != 200:
        vu.fail_reason = f"sms_send:{r.status_code}"
        return

    # 2) 校验码换 token
    r = await _retry_429(
        lambda: client.post(
            "/api/auth/sms/verify",
            json={
                "phone": vu.phone,
                "code": args.sms_code,
                "consentVer": args.consent_ver,
                "username": f"load{vu.idx}",
            },
        ),
        tries=6,
        base_sleep=1.0,
    )
    if r.status_code != 200:
        vu.fail_reason = f"sms_verify:{r.status_code}:{r.text[:120]}"
        return
    vu.token = r.json()["accessToken"]
    auth = {"Authorization": f"Bearer {vu.token}"}

    # 3) 拿上传 token（本地模式回 MOCK 凭证 + objectKey）
    r = await client.post("/api/upload/token", headers=auth)
    if r.status_code != 200:
        vu.fail_reason = f"upload_token:{r.status_code}"
        return
    object_key = r.json()["objectKey"]

    # 4) 本地直传图片字节
    r = await client.post(
        "/api/upload/local",
        headers=auth,
        data={"objectKey": object_key},
        files={"file": ("face.jpg", args.image_bytes, "image/jpeg")},
    )
    if r.status_code != 200:
        vu.fail_reason = f"upload_local:{r.status_code}:{r.text[:120]}"
        return

    # 5) 注册照片记录 → photoId（审核在后台跑，mock 即时通过）
    r = await client.post(
        "/api/photos",
        headers=auth,
        json={
            "ossKey": object_key,
            "width": 1,
            "height": 1,
            "bytes": len(args.image_bytes),
            "mime": "image/jpeg",
        },
    )
    if r.status_code != 200:
        vu.fail_reason = f"photo_register:{r.status_code}:{r.text[:120]}"
        return
    vu.photo_id = r.json()["photoId"]


async def burst_vu(client: httpx.AsyncClient, vu: VU, args, stats: Stats) -> None:
    """阶段 2：建 analyze → 消费 SSE 到 done/error。"""
    auth = {"Authorization": f"Bearer {vu.token}"}
    vu.analyze_start = time.perf_counter()

    # 建任务。照片审核后台异步，可能短暂 425 pending → 重试。
    task_id = None
    for _ in range(20):
        r = await client.post(
            "/api/analyze", headers=auth, json={"photoId": vu.photo_id}
        )
        if r.status_code == 202:
            task_id = r.json()["taskId"]
            break
        if r.status_code == 425:  # 审核中
            await asyncio.sleep(0.3)
            continue
        if r.status_code == 429:  # 分析限流
            vu.fail_reason = "analyze:429_rate_limited"
            stats.add_fail(vu.fail_reason)
            stats.done_fail += 1
            return
        vu.fail_reason = f"analyze:{r.status_code}:{r.text[:120]}"
        stats.add_fail(vu.fail_reason)
        stats.done_fail += 1
        return
    if not task_id:
        vu.fail_reason = "analyze:still_pending"
        stats.add_fail(vu.fail_reason)
        stats.done_fail += 1
        return

    # 消费 SSE，等 done/error。用 token query 回退（EventSource 语义）。
    url = f"/api/analyze/{task_id}/stream?token={vu.token}"
    try:
        async with client.stream(
            "GET", url, timeout=httpx.Timeout(args.deadline + 60)
        ) as resp:
            if resp.status_code != 200:
                vu.fail_reason = f"stream:{resp.status_code}"
                stats.add_fail(vu.fail_reason)
                stats.done_fail += 1
                return
            cur_event = None
            async for line in resp.aiter_lines():
                if line.startswith("event:"):
                    cur_event = line[6:].strip()
                elif line.startswith("data:") and cur_event in ("done", "error"):
                    vu.done_at = time.perf_counter()
                    dur = vu.done_at - vu.analyze_start
                    if cur_event == "done":
                        vu.ok = True
                        stats.done_ok += 1
                        stats.durations.append(dur)
                        if dur <= args.deadline:
                            stats.within_deadline += 1
                    else:
                        vu.fail_reason = f"stream_error:{line[5:80].strip()}"
                        stats.add_fail("stream_error")
                        stats.done_fail += 1
                    return
    except (httpx.ReadTimeout, httpx.TimeoutException):
        vu.fail_reason = "stream:timeout"
        stats.add_fail(vu.fail_reason)
        stats.done_fail += 1
        return
    except Exception as e:  # noqa: BLE001
        vu.fail_reason = f"stream:exc:{type(e).__name__}"
        stats.add_fail(vu.fail_reason)
        stats.done_fail += 1
        return

    # 流结束但没见 done/error
    if not vu.ok and not vu.fail_reason:
        vu.fail_reason = "stream:ended_no_terminal"
        stats.add_fail(vu.fail_reason)
        stats.done_fail += 1


async def bounded_gather(coros, limit: int):
    sem = asyncio.Semaphore(limit)

    async def _wrap(c):
        async with sem:
            return await c

    await asyncio.gather(*[_wrap(c) for c in coros])


async def main() -> None:
    ap = argparse.ArgumentParser(description="venus-4s 报告生成压测")
    ap.add_argument("--base-url", default="http://localhost:8080",
                    help="API 网关地址（web 反代 /api）。直连 api 用 http://localhost:8000")
    ap.add_argument("-c", "--concurrency", type=int, default=200,
                    help="虚拟学员数 / 突发并发数")
    ap.add_argument("--deadline", type=float, default=120.0,
                    help="判定「按时完成」的秒数（默认 120=2 分钟）")
    ap.add_argument("--prepare-concurrency", type=int, default=8,
                    help="准备阶段并发（小一点以躲 SMS 限流）")
    ap.add_argument("--sms-code", default="100000",
                    help="测试模式固定验证码（对齐 SMS_TEST_CODE）")
    ap.add_argument("--phone-prefix", default="133",
                    help="测试手机号前缀（对齐 SMS_TEST_PHONE_PREFIX）")
    ap.add_argument("--consent-ver", default="v1")
    ap.add_argument("--image", default=None,
                    help="上传用图片路径；压真实 LLM 时传真人脸图。缺省用内置 1x1 JPEG")
    args = ap.parse_args()

    args.image_bytes = (
        open(args.image, "rb").read() if args.image else _TINY_JPEG  # noqa: SIM115
    )

    # 生成唯一手机号：前缀 + 补足到 11 位的随机尾号
    tail_len = 11 - len(args.phone_prefix)
    used: set[str] = set()
    vus: list[VU] = []
    for i in range(args.concurrency):
        while True:
            tail = "".join(random.choices("0123456789", k=tail_len))
            phone = args.phone_prefix + tail
            if phone not in used:
                used.add(phone)
                break
        vus.append(VU(idx=i, phone=phone))

    stats = Stats()
    limits = httpx.Limits(
        max_connections=args.concurrency + 50,
        max_keepalive_connections=args.concurrency + 50,
    )
    async with httpx.AsyncClient(
        base_url=args.base_url, limits=limits, timeout=30.0
    ) as client:
        # ---------- 阶段 1：准备 ----------
        print(f"[prepare] {args.concurrency} 个虚拟学员登录+传图中"
              f"（并发 {args.prepare_concurrency}）…")
        t0 = time.perf_counter()
        await bounded_gather(
            [prepare_vu(client, vu, args) for vu in vus],
            limit=args.prepare_concurrency,
        )
        for vu in vus:
            if vu.photo_id is not None:
                stats.prepared += 1
            else:
                stats.prepare_failed += 1
                stats.add_fail(vu.fail_reason or "prepare:unknown")
        print(f"[prepare] 完成：成功 {stats.prepared} / 失败 {stats.prepare_failed}"
              f"，耗时 {time.perf_counter() - t0:.1f}s")

        ready = [vu for vu in vus if vu.photo_id is not None]
        if not ready:
            print("[abort] 无一准备成功，检查限流/被测端是否可用。")
            _report(stats, args, wall=0.0, n_ready=0)
            return

        # ---------- 阶段 2：突发 ----------
        print(f"[burst] 同时触发 {len(ready)} 个 analyze，等报告 done…")
        wall0 = time.perf_counter()
        await asyncio.gather(*[burst_vu(client, vu, args, stats) for vu in ready])
        wall = time.perf_counter() - wall0
        print(f"[burst] 全部收敛，墙钟 {wall:.1f}s")

    _report(stats, args, wall=wall, n_ready=len(ready))


def _report(stats: Stats, args, *, wall: float, n_ready: int) -> None:
    d = stats.durations
    print("\n" + "=" * 56)
    print("压测结果")
    print("=" * 56)
    print(f"目标            : {args.concurrency} 份 / {args.deadline:.0f}s 内完成")
    print(f"准备成功        : {stats.prepared}  (失败 {stats.prepare_failed})")
    print(f"报告 done       : {stats.done_ok}  (失败 {stats.done_fail})")
    print(f"按时完成(≤{args.deadline:.0f}s): {stats.within_deadline} / {n_ready}")
    print(f"突发墙钟        : {wall:.1f}s")
    if d:
        print(f"analyze→done 秒 : p50={_pctl(d,50):.1f}  p90={_pctl(d,90):.1f}  "
              f"p99={_pctl(d,99):.1f}  max={max(d):.1f}  min={min(d):.1f}  "
              f"mean={statistics.mean(d):.1f}")
        if wall > 0:
            print(f"有效吞吐        : {stats.done_ok / wall:.2f} 份/秒")
    if stats.fail_reasons:
        print("\n失败明细：")
        for k, v in sorted(stats.fail_reasons.items(), key=lambda x: -x[1]):
            print(f"  {v:4d}  {k}")
    # 结论
    ok = stats.within_deadline >= args.concurrency
    print("\n判定 :", "✅ 达标" if ok else "❌ 未达标",
          f"（{stats.within_deadline}/{args.concurrency} 按时完成）")
    print("=" * 56)


if __name__ == "__main__":
    asyncio.run(main())
