"""Скачать последний MSI агента + манифест из GitHub Release (только на сервере)."""

from __future__ import annotations

import hashlib
import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

MANIFEST_NAME = "agent-release.json"
MSI_PREFIX = "bad-agent-"
MSI_SUFFIX = ".msi"


@dataclass(frozen=True)
class ReleaseAssets:
    tag: str
    version: str
    msi_name: str
    sha256: str
    msi_download_url: str
    manifest_download_url: str
    release_url: str


def _request_json(
    url: str,
    token: str = "",
    accept: str = "application/vnd.github+json",
) -> Any:
    req = urllib.request.Request(url, method="GET")
    req.add_header("Accept", accept)
    req.add_header("User-Agent", "bad-server-agent-update/0.2")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {exc.code} for {url}: {body[:300]}") from exc


def _download_bytes(url: str, token: str = "") -> bytes:
    req = urllib.request.Request(url, method="GET")
    req.add_header("Accept", "application/octet-stream")
    req.add_header("User-Agent", "bad-server-agent-update/0.2")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Download failed {exc.code} for {url}: {body[:300]}") from exc


def _pick_asset(assets: list[dict[str, Any]], name: str) -> Optional[dict[str, Any]]:
    for asset in assets:
        if asset.get("name") == name:
            return asset
    return None


def _pick_msi(assets: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    matches = [
        a
        for a in assets
        if isinstance(a.get("name"), str)
        and a["name"].startswith(MSI_PREFIX)
        and a["name"].endswith(MSI_SUFFIX)
    ]
    if not matches:
        return None
    # Предпочитать лексикографически последнее имя (имена файлов в духе semver).
    matches.sort(key=lambda a: a["name"], reverse=True)
    return matches[0]


def fetch_latest_release_assets(
    repo: str,
    token: str = "",
    api_base: str = "https://api.github.com",
) -> ReleaseAssets:
    """Загрузить последний GitHub Release с agent-release.json + MSI."""
    url = f"{api_base.rstrip('/')}/repos/{repo}/releases/latest"
    data = _request_json(url, token=token)
    assets = data.get("assets") or []
    if not isinstance(assets, list):
        raise RuntimeError("GitHub release assets payload is not a list")

    manifest_asset = _pick_asset(assets, MANIFEST_NAME)
    if not manifest_asset:
        raise RuntimeError(f"Release missing {MANIFEST_NAME}")

    manifest_url = manifest_asset.get("url") or manifest_asset.get("browser_download_url")
    if not manifest_url:
        raise RuntimeError("Manifest asset has no download URL")

    # Предпочитать URL asset через API (поддерживает private-репозитории с токеном).
    manifest_bytes = _download_bytes(str(manifest_url), token=token)
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("Invalid agent-release.json") from exc

    version = str(manifest.get("version") or "").strip()
    msi_name = str(manifest.get("msi_name") or "").strip()
    sha256 = str(manifest.get("sha256") or "").strip().lower()
    if not version or not msi_name or not sha256:
        raise RuntimeError("agent-release.json missing version/msi_name/sha256")

    msi_asset = _pick_asset(assets, msi_name) or _pick_msi(assets)
    if not msi_asset:
        raise RuntimeError(f"Release missing MSI asset {msi_name}")
    if msi_asset.get("name") != msi_name:
        # Fallback, но сохранить имя из манифеста для последующих проверок согласованности.
        logger.warning(
            "Manifest msi_name=%s but using asset %s", msi_name, msi_asset.get("name")
        )
        msi_name = str(msi_asset["name"])

    msi_url = msi_asset.get("url") or msi_asset.get("browser_download_url")
    if not msi_url:
        raise RuntimeError("MSI asset has no download URL")

    return ReleaseAssets(
        tag=str(data.get("tag_name") or ""),
        version=version,
        msi_name=msi_name,
        sha256=sha256,
        msi_download_url=str(msi_url),
        manifest_download_url=str(manifest_url),
        release_url=str(data.get("html_url") or ""),
    )


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def mirror_release_to_dir(
    assets: ReleaseAssets,
    dest_dir: Path,
    token: str = "",
) -> Path:
    """Скачать MSI, проверить sha256, атомарно записать в dest_dir. Вернуть путь к MSI."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    raw = _download_bytes(assets.msi_download_url, token=token)
    digest = sha256_hex(raw)
    if digest != assets.sha256.lower():
        raise RuntimeError(
            f"MSI sha256 mismatch: expected {assets.sha256}, got {digest}"
        )

    target = dest_dir / assets.msi_name
    tmp = dest_dir / f".{assets.msi_name}.tmp"
    tmp.write_bytes(raw)
    tmp.replace(target)

    manifest_path = dest_dir / MANIFEST_NAME
    manifest_path.write_text(
        json.dumps(
            {
                "version": assets.version,
                "msi_name": assets.msi_name,
                "sha256": assets.sha256,
            },
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    return target
