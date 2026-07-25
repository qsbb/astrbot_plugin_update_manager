"""GitHub 镜像加速站解析与 URL 前缀拼接。

镜像只是"前缀代理"：把原始完整 URL 直接接在加速站后面，由加速站回源 GitHub。
因此本模块不重写 path、不改查询串，也不猜测加速站的私有路由格式——任何形如
``https://mirror/https://raw.githubusercontent.com/...`` 的写法都由加速站自行解析。

镜像默认关闭（空字符串表示直连）。启用后仍必须保留直连回退：加速站属于第三方
基础设施，挂掉的概率显著高于 GitHub 本身，绝不能因为镜像不可用就把"检查更新"
判成失败。
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

#: 内置候选加速站，按社区可用性经验排序；用户可在配置里追加自定义站点。
BUILTIN_MIRRORS: tuple[str, ...] = (
    "https://edgeone.gh-proxy.com",
    "https://hk.gh-proxy.com",
    "https://gh-proxy.com",
    "https://gh.dpik.top",
)

#: 只有 GitHub 家族域名值得走加速站；其余域名原样直连，避免把无关请求代理出去。
MIRRORABLE_HOSTS = frozenset(
    {
        "github.com",
        "raw.githubusercontent.com",
        "codeload.github.com",
        "objects.githubusercontent.com",
        "api.github.com",
    }
)

#: 测速探针：GitHub 官方示例仓库的 README，仅几十字节且长期稳定存在。
BENCHMARK_PROBE_URL = (
    "https://raw.githubusercontent.com/octocat/Hello-World/master/README"
)
#: 单站测速默认超时（秒）；测速是可选诊断动作，不该让页面长时间转圈。
DEFAULT_BENCHMARK_TIMEOUT_SECONDS = 5.0


def normalize_mirror(value: Any) -> str | None:
    """把单个加速站收敛成 ``https://host[/path]`` 形式；非法项返回 None。

    强制 https：镜像承载的是待安装的插件压缩包，明文信道上的中间人可以直接替换
    归档内容。同时拒绝带凭据（user:password）的 URL，避免把凭据写进日志。
    """
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = urlsplit(text)
    except ValueError:
        return None
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        return None
    return text.rstrip("/") or None


def parse_mirror_candidates(value: Any) -> tuple[str, ...]:
    """解析自定义加速站列表：换行或逗号分隔、去重、必须 https、非法项忽略。

    非法项被静默丢弃而不是整体报错——配置里一个笔误不应该让镜像功能全盘不可用。
    """
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        raw_items: list[Any] = list(value)
    else:
        # 换行与逗号（含中文逗号）都当分隔符，贴合用户在文本框里的自然输入。
        raw_items = list(
            str(value).replace(",", "\n").replace("，", "\n").splitlines()
        )
    normalized = (normalize_mirror(item) for item in raw_items)
    return tuple(dict.fromkeys(item for item in normalized if item))


def available_mirrors(custom: Any = None) -> tuple[str, ...]:
    """内置站点 + 自定义站点，保持内置优先且整体去重。"""
    return tuple(dict.fromkeys(BUILTIN_MIRRORS + parse_mirror_candidates(custom)))


def resolve_mirror(value: Any) -> str | None:
    """把配置里选中的加速站收敛成可用前缀；留空或非法即视为直连。"""
    return normalize_mirror(value)


def apply_mirror(url: str, mirror: str | None) -> str:
    """给 GitHub URL 套上加速站前缀；无镜像或非 GitHub 域名时原样返回。

    拼接规则固定为 ``f"{mirror.rstrip('/')}/{原始完整URL}"``，保留原始 scheme，
    这样加速站才能识别回源目标。
    """
    prefix = normalize_mirror(mirror)
    if not prefix or not url:
        return url
    try:
        host = (urlsplit(url).hostname or "").lower()
    except ValueError:
        return url
    if host not in MIRRORABLE_HOSTS:
        return url
    return f"{prefix}/{url}"


def normalize_benchmark_timeout(
    value: Any, *, default: float = DEFAULT_BENCHMARK_TIMEOUT_SECONDS
) -> float:
    """把测速超时收敛成 >=0.5 的浮点秒；非法值回落到默认值。"""
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0.5 else default
