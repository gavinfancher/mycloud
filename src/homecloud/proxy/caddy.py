from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from homecloud.config import settings

logger = logging.getLogger(__name__)


class CaddyProxy:
    """Write per-VM reverse proxy configs for Cloudflare Tunnel → VM."""

    def __init__(self) -> None:
        self.config_dir = Path(settings.caddy_config_dir)
        self.domain = settings.domain

    def fqdn(self, hostname: str) -> str:
        if hostname.endswith(self.domain):
            return hostname
        return f"{hostname}.{self.domain}"

    def ensure_route(
        self,
        hostname: str,
        *,
        upstream_host: str,
        upstream_port: int = 80,
    ) -> dict:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        fqdn = self.fqdn(hostname)
        safe_name = hostname.split(".")[0]
        config_path = self.config_dir / f"{safe_name}.caddy"

        config_path.write_text(
            f"{fqdn} {{\n"
            f"    reverse_proxy {upstream_host}:{upstream_port}\n"
            f"}}\n"
        )
        self._reload()
        return {
            "hostname": fqdn,
            "upstream": f"{upstream_host}:{upstream_port}",
            "config": str(config_path),
        }

    def remove_route(self, hostname: str) -> None:
        safe_name = hostname.split(".")[0]
        config_path = self.config_dir / f"{safe_name}.caddy"
        if config_path.exists():
            config_path.unlink()
            self._reload()

    def _reload(self) -> None:
        cmd = settings.caddy_reload_cmd.strip()
        if not cmd:
            return
        try:
            subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
            logger.info("Caddy reloaded")
        except subprocess.CalledProcessError as exc:
            logger.warning("Caddy reload failed: %s", exc.stderr or exc)
