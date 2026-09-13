"""凝心 UI canonical source and vendored Page copy synchronization."""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
from pathlib import Path

UI_VERSION = "1.0.1"
ASSETS = ("series-ui.css", "series-ui.js")
TARGETS = {
    "astrbot_plugin_active_learner": ("pages/manager",),
    "astrbot_plugin_conversation_flow": ("pages/manager",),
    "astrbot_plugin_identity_guardian": ("pages/join_review",),
    "astrbot_plugin_relationship": ("pages/manager",),
    "astrbot_plugin_environment_awareness": ("pages/status",),
    "astrbot_plugin_voice_hub": ("pages/settings",),
    "astrbot_plugin_embodiment_bridge": ("pages/operator",),
    "astrbot_plugin_update_manager": ("pages/manager", "webui"),
}


def canonical_root() -> Path:
    return Path(__file__).resolve().parents[1] / "ui"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root: Path) -> list[str]:
    root = root.resolve()
    source = root / "astrbot_plugin_update_manager" / "ui"
    errors: list[str] = []
    for name in ASSETS:
        if not (source / name).is_file():
            errors.append(f"series.ui canonical missing: {name}")
    if errors:
        return errors
    expected = {name: _digest(source / name) for name in ASSETS}
    for plugin_id, page_dirs in TARGETS.items():
        for page_dir in page_dirs:
            target = root / plugin_id / page_dir
            for name in ASSETS:
                copied = target / name
                if not copied.is_file():
                    errors.append(f"series.ui copy missing: {plugin_id}/{page_dir}/{name}")
                    continue
                if _digest(copied) != expected[name]:
                    errors.append(f"series.ui copy drifted: {plugin_id}/{page_dir}/{name}")
            index = target / "index.html"
            if index.is_file():
                text = index.read_text(encoding="utf-8", errors="ignore")
                if "series-ui.css" not in text:
                    errors.append(f"series.ui stylesheet not linked: {plugin_id}/{page_dir}/index.html")
                if "series-ui.js" not in text:
                    errors.append(f"series.ui script not linked: {plugin_id}/{page_dir}/index.html")
                if "data-series-ui" not in text:
                    errors.append(f"series.ui body marker missing: {plugin_id}/{page_dir}/index.html")
                positions = {
                    "style": text.find("style.css"),
                    "shared_css": text.find("series-ui.css"),
                    "shared_js": text.find("series-ui.js"),
                    "app": text.find("app.js"),
                }
                ordered = (
                    positions["style"] >= 0
                    and positions["style"] < positions["shared_css"]
                    and positions["shared_css"] < positions["shared_js"]
                    and positions["shared_js"] < positions["app"]
                )
                if not ordered:
                    errors.append(
                        f"series.ui asset order invalid: {plugin_id}/{page_dir}/index.html"
                    )
    return errors


def audit_interactions(root: Path) -> dict[str, list[str]]:
    """Audit page-owned interaction implementations that bypass SeriesUI.

    Native dialogs, page-local toast implementations, and static #toast nodes are
    hard errors. Static page modals are reported as warnings because some legacy
    business dialogs still need a migration pass.
    """
    root = root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    native_dialog = re.compile(
        r"(?:window|globalThis|self)\s*\??\s*\.\s*(alert|confirm|prompt)\s*\("
        r"|(?<![.\w])(alert|confirm|prompt)\s*\("
    )
    local_toast = re.compile(
        r"(?:function\s+|(?:const|let|var)\s+)(toast|showToast)\s*(?:=|\(|\{)"
    )
    static_toast = re.compile(r"""id=["']toast["']""")
    static_modal = re.compile(r"""class=["'][^"']*\bmodal(?:\s|["'])""")
    page_css_toast = re.compile(r"#toast\b")
    page_css_generic_toast = re.compile(r"(?<![-\w])\.toast\s*(?:[,{])")
    fallback_node = re.compile(r"""data-toast-fallback|id=["'](?:bridge-error|startup-error|page-error)["']""")
    for plugin_id, page_dirs in TARGETS.items():
        for page_dir in page_dirs:
            target = root / plugin_id / page_dir
            if not target.is_dir():
                continue
            for script in sorted(target.glob("*.js")):
                if script.name == "series-ui.js":
                    continue
                text = script.read_text(encoding="utf-8", errors="ignore")
                for match in native_dialog.finditer(text):
                    errors.append(
                        f"native dialog bypass: {plugin_id}/{page_dir}/{script.name} ({match.group(1) or match.group(2)})"
                    )
                for match in local_toast.finditer(text):
                    errors.append(
                        f"page-local toast bypass: {plugin_id}/{page_dir}/{script.name} ({match.group(1)})"
                    )
            index = target / "index.html"
            if not index.is_file():
                continue
            html = index.read_text(encoding="utf-8", errors="ignore")
            if static_toast.search(html):
                errors.append(f"static #toast node: {plugin_id}/{page_dir}/index.html")
            if static_modal.search(html):
                warnings.append(
                    f"static modal remains page-owned: {plugin_id}/{page_dir}/index.html"
                )
            for css in sorted(target.glob("*.css")):
                if css.name == "series-ui.css":
                    continue
                css_text = css.read_text(encoding="utf-8", errors="ignore")
                if page_css_toast.search(css_text):
                    errors.append(f"page-local #toast CSS: {plugin_id}/{page_dir}/{css.name}")
                if page_css_generic_toast.search(css_text):
                    warnings.append(
                        f"page-local .toast CSS override: {plugin_id}/{page_dir}/{css.name}"
                    )
            if (target / "index.html").is_file() and not fallback_node.search(html):
                if any("const notify =" in script.read_text(encoding="utf-8", errors="ignore")
                       for script in target.glob("*.js") if script.name != "series-ui.js"):
                    warnings.append(
                        f"notify() has no inline fallback node: {plugin_id}/{page_dir}/index.html"
                    )
    return {"errors": errors, "warnings": warnings}


def sync(root: Path) -> list[str]:
    root = root.resolve()
    source = root / "astrbot_plugin_update_manager" / "ui"
    for name in ASSETS:
        if not (source / name).is_file():
            raise FileNotFoundError(source / name)
    written: list[str] = []
    for plugin_id, page_dirs in TARGETS.items():
        for page_dir in page_dirs:
            target = root / plugin_id / page_dir
            if not target.is_dir():
                raise FileNotFoundError(target)
            for name in ASSETS:
                destination = target / name
                shutil.copyfile(source / name, destination)
                written.append(str(destination.relative_to(root)))
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="凝心 UI 正本同步与漂移检查")
    parser.add_argument("command", choices=("sync", "check"))
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if args.command == "sync":
        for path in sync(root):
            print(f"synced {path}")
        return 0
    errors = verify(root)
    interactions = audit_interactions(root)
    errors.extend(interactions["errors"])
    for warning in interactions["warnings"]:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    print(f"series.ui {UI_VERSION}: {'ok' if not errors else 'drift'}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
