from __future__ import annotations

import logging

import httpx

from homecloud.config import settings

logger = logging.getLogger(__name__)

CF_API = "https://api.cloudflare.com/client/v4"


class CloudflareDNS:
    """Manage DNS records for myhomecloud.dev via Cloudflare API."""

    def __init__(self) -> None:
        self.token = settings.cloudflare_api_token
        self.zone_id = settings.cloudflare_zone_id
        self.domain = settings.domain
        self.tunnel_cname = settings.cloudflare_tunnel_cname

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.zone_id and self.tunnel_cname)

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=CF_API,
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=30.0,
        )

    def fqdn(self, hostname: str) -> str:
        if hostname.endswith(self.domain):
            return hostname
        return f"{hostname}.{self.domain}"

    def ensure_vm_record(self, hostname: str) -> dict:
        """Create or update CNAME → Cloudflare Tunnel for a VM hostname."""
        if not self.enabled:
            logger.warning("Cloudflare DNS not configured — skipping record for %s", hostname)
            return {"skipped": True, "hostname": self.fqdn(hostname)}

        name = hostname.removesuffix(f".{self.domain}")
        with self._client() as client:
            existing = client.get(
                f"/zones/{self.zone_id}/dns_records",
                params={"type": "CNAME", "name": self.fqdn(name)},
            )
            existing.raise_for_status()
            records = existing.json().get("result", [])

            payload = {
                "type": "CNAME",
                "name": name,
                "content": self.tunnel_cname,
                "proxied": True,
                "comment": "homecloud-vm",
            }

            if records:
                record_id = records[0]["id"]
                resp = client.put(f"/zones/{self.zone_id}/dns_records/{record_id}", json=payload)
            else:
                resp = client.post(f"/zones/{self.zone_id}/dns_records", json=payload)

            resp.raise_for_status()
            result = resp.json()["result"]
            return {
                "hostname": self.fqdn(name),
                "record_id": result["id"],
                "content": result["content"],
            }

    def delete_vm_record(self, hostname: str) -> None:
        if not self.enabled:
            return
        name = hostname.removesuffix(f".{self.domain}")
        with self._client() as client:
            existing = client.get(
                f"/zones/{self.zone_id}/dns_records",
                params={"type": "CNAME", "name": self.fqdn(name)},
            )
            existing.raise_for_status()
            for record in existing.json().get("result", []):
                client.delete(f"/zones/{self.zone_id}/dns_records/{record['id']}")
