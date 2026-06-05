from __future__ import annotations

import json
from pathlib import Path

STATE_FILE = Path(".homecloud/state.json")


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {
            "setup_complete": False,
            "ssh_public_key": None,
            "built_templates": {},
            "custom_templates": {},
            "vms": {},
        }
    state = json.loads(STATE_FILE.read_text())
    state.setdefault("setup_complete", False)
    state.setdefault("ssh_public_key", None)
    state.setdefault("vms", {})
    return state


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_ssh_public_key() -> str | None:
    return load_state().get("ssh_public_key")


def save_setup(*, ssh_public_key: str) -> None:
    key = ssh_public_key.strip()
    if not key.startswith(("ssh-ed25519 ", "ssh-rsa ", "ecdsa-sha2-")):
        raise ValueError("Invalid SSH public key format")
    state = load_state()
    state["ssh_public_key"] = key.splitlines()[0]
    state["setup_complete"] = True
    save_state(state)


def is_setup_complete() -> bool:
    state = load_state()
    return bool(state.get("setup_complete") and state.get("ssh_public_key"))


def set_built_template(image_id: str, template_id: int) -> None:
    state = load_state()
    state.setdefault("built_templates", {})[image_id] = template_id
    save_state(state)


def get_built_template(image_id: str) -> int | None:
    state = load_state()
    return state.get("built_templates", {}).get(image_id)


def register_custom_template(name: str, template_id: int, base_image_id: str) -> None:
    state = load_state()
    state.setdefault("custom_templates", {})[name] = {
        "template_id": template_id,
        "base_image_id": base_image_id,
    }
    save_state(state)


def register_vm(name: str, record: dict) -> None:
    state = load_state()
    state.setdefault("vms", {})[name] = record
    save_state(state)


def unregister_vm(name: str) -> None:
    state = load_state()
    state.get("vms", {}).pop(name, None)
    save_state(state)


def list_registered_vms() -> dict:
    return load_state().get("vms", {})


def hydrate_registry() -> None:
    from homecloud.images.registry import BUILTIN_IMAGES

    state = load_state()
    for image_id, template_id in state.get("built_templates", {}).items():
        if image_id in BUILTIN_IMAGES:
            BUILTIN_IMAGES[image_id].template_id = template_id
