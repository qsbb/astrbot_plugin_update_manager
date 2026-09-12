"""凝心 UI canonical source and vendored Page copy synchronization."""

from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path

UI_VERSION = "1.0.0"
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
    return errors


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
    for error in errors:
        print(error)
    print(f"series.ui {UI_VERSION}: {'ok' if not errors else 'drift'}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
