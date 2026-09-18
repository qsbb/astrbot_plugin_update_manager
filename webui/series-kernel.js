/* 凝心溯溪 · 核专用共享逻辑（pages/manager 与 webui 共用）。
 *
 * 只放纯函数与协议细节：诊断日志增量游标协议、问题聚合、建议文案、
 * 状态标签映射。DOM 渲染与传输层（bridge / fetch）仍由各自前端负责。
 * 由 core/series_ui.py 的 sync 分发，禁止手改各目录下的副本。
 */
(function () {
  "use strict";

  const VERSION = "1.0.0";

  // 诊断日志成员是否还有未拉取的历史
  function memberHasMore(member) {
    return Boolean(member?.has_more ?? member?.truncated ?? member?.payload_has_more);
  }

  // 从成员列表推导增量拉取游标；只有 ready 的成员参与
  function deriveCursors(members) {
    const cursors = {};
    const streams = {};
    (members || []).forEach((member) => {
      if (!member || member.status !== "ready") return;
      const next = Number(member.next_seq);
      cursors[member.plugin_id] = Number.isFinite(next) && next >= 0 ? next : 0;
      if (member.stream_id) streams[member.plugin_id] = member.stream_id;
    });
    return { cursors, streams };
  }

  // 成员变化后的状态收敛：剔除已下线/被重置插件的事件与游标。
  // events/cursors/streams 均被原地修改；返回 { removed, reset, changed }。
  function pruneForMembers(events, cursors, streams, members) {
    const activeIds = new Set((members || []).map((item) => item.plugin_id));
    const resetIds = new Set(
      (members || []).filter((item) => item.reset).map((item) => item.plugin_id)
    );
    let changed = false;
    if (resetIds.size || events.some((item) => !activeIds.has(item.plugin_id))) {
      const kept = events.filter(
        (item) => activeIds.has(item.plugin_id) && !resetIds.has(item.plugin_id)
      );
      if (kept.length !== events.length) {
        events.splice(0, events.length, ...kept);
        changed = true;
      }
    }
    [cursors, streams].forEach((table) => {
      Object.keys(table || {}).forEach((pluginId) => {
        if (!activeIds.has(pluginId)) {
          delete table[pluginId];
          changed = true;
        }
      });
    });
    return { removed: !changed && false, reset: resetIds.size > 0, changed: changed || resetIds.size > 0 };
  }

  // 增量事件合并：按 plugin_id:seq 去重追加，超上限裁掉最旧的。
  // 返回 { fresh, changed }；events 原地修改。
  function mergeLogEvents(events, incoming, { cap = 10000 } = {}) {
    const seen = new Set(events.map((item) => `${item.plugin_id}:${item.seq}`));
    const fresh = [];
    (incoming || []).forEach((item) => {
      const key = `${item.plugin_id}:${item.seq}`;
      if (seen.has(key)) return;
      seen.add(key);
      events.push(item);
      fresh.push(item);
    });
    let changed = fresh.length > 0;
    if (cap > 0 && events.length > cap) {
      events.splice(0, events.length - cap);
      changed = true;
    }
    return { fresh, changed };
  }

  // 问题聚合：按 插件:事件码 分组统计 ERROR/WARNING/CRITICAL。
  // 返回 [{ plugin_id, plugin_name, code, level, count, last }]，ERROR 优先、次数降序。
  function aggregateProblems(events, { limit = 0 } = {}) {
    const groups = new Map();
    (events || [])
      .filter((item) => ["ERROR", "WARNING", "CRITICAL"].includes(String(item.level || "").toUpperCase()))
      .forEach((item) => {
        const key = `${item.plugin_id}:${item.code || "UNKNOWN"}`;
        const current = groups.get(key) || {
          plugin_id: item.plugin_id,
          plugin_name: item.plugin_name || item.plugin_id,
          code: item.code || "UNKNOWN",
          level: "WARNING",
          count: 0,
          last: item.timestamp,
        };
        current.count += 1;
        if (String(item.timestamp || "") > String(current.last || "")) current.last = item.timestamp;
        if (String(item.level || "").toUpperCase() !== "WARNING") current.level = "ERROR";
        groups.set(key, current);
      });
    const sorted = [...groups.values()].sort(
      (a, b) => (b.level === "ERROR") - (a.level === "ERROR") || b.count - a.count
    );
    return limit > 0 ? sorted.slice(0, limit) : sorted;
  }

  // 问题建议文案（双前端统一用这一份）
  function problemSuggestion(code) {
    const value = String(code || "").toUpperCase();
    if (value.includes("RATE_LIMIT")) return "GitHub 限流：稍后重试，或先在镜像加速里选择可用站点。";
    if (value.includes("TIMEOUT") || value.includes("UNREACHABLE") || value.includes("NETWORK")) return "网络或超时：确认代理与镜像可达后重试。";
    if (value.includes("MIGRAT") || value.includes("SCHEMA") || value.includes("CONFIG")) return "配置或迁移：核对配置页中该模块字段后重试。";
    if (value.includes("AUTH") || value.includes("TOKEN") || value.includes("CREDENTIAL")) return "凭据问题：检查 GitHub Token 或控制中心账户权限。";
    if (value.includes("IMPORT") || value.includes("LOAD")) return "加载失败：展开事件详情确认依赖与运行环境。";
    return "展开该事件详情查看上下文，再决定是否重试。";
  }

  const LINK_STATE_LABELS = {
    ready: "正常",
    degraded: "降级",
    unavailable: "不可用",
    disabled: "已关闭",
    stale: "数据陈旧",
    unknown: "未知",
  };
  const LINK_STATE_CLASSES = {
    ready: "ok",
    degraded: "warn",
    unavailable: "warn",
    disabled: "native",
    stale: "mixed",
    unknown: "native",
  };

  function linkStateLabel(state) {
    return LINK_STATE_LABELS[String(state || "")] || "未知";
  }

  function linkStateClass(state) {
    return LINK_STATE_CLASSES[String(state || "")] || "native";
  }

  window.SeriesKernel = Object.freeze({
    version: VERSION,
    memberHasMore,
    deriveCursors,
    pruneForMembers,
    mergeLogEvents,
    aggregateProblems,
    problemSuggestion,
    linkStateLabel,
    linkStateClass,
  });
})();
