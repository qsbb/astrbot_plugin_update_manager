from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1].parent))

from astrbot_plugin_update_manager.core.webui_artifacts import (
    MAX_ARTIFACT_BYTES,
    ArtifactStore,
)


def test_artifact_store_put_get_snapshot():
    store = ArtifactStore()
    record = store.put(
        plugin_id="astrbot_plugin_voice_hub",
        panel="voices",
        filename="preview.wav",
        mime="audio/wav",
        data=b"RIFF0000",
    )
    assert store.get(record.artifact_id).data == b"RIFF0000"
    snapshot = store.snapshot(record.artifact_id)
    assert snapshot["filename"] == "preview.wav"
    assert snapshot["mime"] == "audio/wav"
    assert snapshot["size"] == 8


def test_artifact_store_rejects_empty_and_oversized():
    store = ArtifactStore()
    with pytest.raises(ValueError, match="EMPTY_ARTIFACT"):
        store.put(plugin_id="x", panel="y", filename="a", mime="", data=b"")
    with pytest.raises(ValueError, match="ARTIFACT_TOO_LARGE"):
        store.put(
            plugin_id="x",
            panel="y",
            filename="big",
            mime="application/octet-stream",
            data=b"x" * (MAX_ARTIFACT_BYTES + 1),
        )
