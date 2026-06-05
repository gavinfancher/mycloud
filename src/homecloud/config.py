from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Proxmox
    proxmox_host: str = "localhost"
    proxmox_user: str = "root@pam"
    proxmox_token_name: str = ""
    proxmox_token_value: str = ""
    proxmox_verify_ssl: bool = False
    proxmox_node: str = "pve-root"
    proxmox_storage: str = "ssd-pool"
    proxmox_bridge: str = "vmbr0"
    proxmox_snippets_dir: str = "/var/lib/vz/snippets"
    proxmox_ssh_host: str = ""
    proxmox_base_template_id: int = 9000

    # Tailscale — VMs join tailnet; SSH via MagicDNS (name.tailnet.ts.net)
    tailscale_api_key: str = ""
    tailscale_tailnet: str = ""
    tailscale_auth_key: str = ""

    # VM SSH user
    vm_ssh_user: str = "ubuntu"

    # Controller (AGENT_HOST/AGENT_PORT still accepted for back-compat)
    controller_host: str = Field(
        default="0.0.0.0",
        validation_alias=AliasChoices("CONTROLLER_HOST", "AGENT_HOST"),
    )
    controller_port: int = Field(
        default=8080,
        validation_alias=AliasChoices("CONTROLLER_PORT", "AGENT_PORT"),
    )

    # Public domain
    domain: str = "myhomecloud.dev"

    # Cloudflare
    cloudflare_api_token: str = ""
    cloudflare_zone_id: str = ""
    cloudflare_tunnel_id: str = ""
    cloudflare_tunnel_cname: str = ""

    # Caddy
    caddy_config_dir: str = "/etc/caddy/sites"
    caddy_reload_cmd: str = ""

    # Local resolver (split DNS)
    coredns_zone_path: str = "/etc/coredns/db.myhomecloud.dev"
    coredns_reload_cmd: str = ""
    control_node_tailscale_ip: str = ""

    # Default primary web port for an instance's base hostname
    default_web_port: int = 80


settings = Settings()
