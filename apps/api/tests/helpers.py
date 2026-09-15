"""集成测试共用的小工具。"""
import hashlib

# 测试造出来的 users 行统一带这个 phone_hash 前缀。
# 集成测试直接跑在本地 dev 那个库上（DATABASE_URL 来自 config/dev.env），
# 不能整表清空，所以靠前缀把「测试数据」和「你自己的开发数据」分开，
# conftest 的回收夹具只删带前缀的行。
TEST_PHONE_HASH_PREFIX = "pytest_"


def make_phone_hash(tag: str) -> str:
    """按 tag 造一个带测试前缀的 64 位 phone_hash。

    取 sha256 而不是把 tag 补零，避免 "bk1" 和 "bk10" 补完撞成同一个值
    —— 撞了就是 1062 Duplicate entry，排查起来完全看不出是命名问题。
    """
    return (TEST_PHONE_HASH_PREFIX + hashlib.sha256(tag.encode()).hexdigest())[:64]


# 集成测试里 photos 行统一用这个 object_key。
TEST_OSS_KEY = "uploads/x.jpg"

# 最小 JPEG（SOI + EOI）。mock LLM 不解码图片，只要文件存在、能读出字节即可。
_TINY_JPEG = b"\xff\xd8\xff\xd9"


def seed_local_object(object_key: str = TEST_OSS_KEY) -> None:
    """把测试图片落到本地 var/uploads/。

    APP_ENV=test 下 OSS 恒为 mock，上传走 file 方式，analyze_runner 会回读
    var/uploads/{object_key} 的字节送给 LLM。测试若只在库里插 photos 行而不落盘，
    runner 起来就是 FileNotFoundError → 任务 500，报错位置离真正原因很远。
    """
    from app.services.oss import save_local_object

    save_local_object(object_key, _TINY_JPEG)
