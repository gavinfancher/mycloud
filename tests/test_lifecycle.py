"""Tests for VM pause/resume (phase 13) and cooperative job cancellation."""
from __future__ import annotations

import pytest

import homecloud.images.deployer as deployer_module
import homecloud.jobs as jobs_module
from homecloud.images.deployer import VMDeployer, VMManager
from homecloud.jobs import JobCancelled, JobStore
from homecloud.tailscale.client import TailscaleClient


class FakeProxmox:
    def __init__(self):
        self.calls = []

    def suspend(self, vmid):
        self.calls.append(("suspend", vmid))
        return "UPID:suspend"

    def resume(self, vmid):
        self.calls.append(("resume", vmid))
        return "UPID:resume"

    def stop(self, vmid):
        self.calls.append(("stop", vmid))
        return "UPID:stop"

    def delete_vm(self, vmid):
        self.calls.append(("delete_vm", vmid))
        return "UPID:delete"

    def wait_for_task(self, task, **kwargs):
        self.calls.append(("wait", task))


class FakeTailscale:
    def __init__(self, devices: dict[str, dict] | None = None):
        self.devices = devices or {}
        self.deleted: list[str] = []

    def get_device_by_hostname(self, hostname: str) -> dict | None:
        return self.devices.get(hostname)

    def delete_device_by_hostname(self, hostname: str) -> bool:
        if hostname not in self.devices:
            return False
        device = self.devices.pop(hostname)
        self.deleted.append(TailscaleClient.device_id(device))
        return True


# ---------------------------------------------------------------------------
# VMManager suspend / resume
# ---------------------------------------------------------------------------


def test_suspend_calls_proxmox_and_waits():
    fp = FakeProxmox()
    result = VMManager(proxmox=fp).suspend(501)
    assert result == {"vmid": 501, "status": "paused"}
    assert ("suspend", 501) in fp.calls
    assert ("wait", "UPID:suspend") in fp.calls


def test_resume_calls_proxmox_and_waits():
    fp = FakeProxmox()
    result = VMManager(proxmox=fp).resume(501)
    assert result == {"vmid": 501, "status": "running"}
    assert ("resume", 501) in fp.calls
    assert ("wait", "UPID:resume") in fp.calls


# ---------------------------------------------------------------------------
# VMManager delete + Tailscale cleanup
# ---------------------------------------------------------------------------


def test_delete_removes_tailscale_device_when_configured(monkeypatch):
    fp = FakeProxmox()
    ft = FakeTailscale(
        devices={"app": {"nodeId": "n123", "name": "app.tailnet.ts.net"}},
    )
    monkeypatch.setattr(deployer_module.settings, "tailscale_api_key", "tskey-test")
    monkeypatch.setattr(deployer_module, "unregister_vm", lambda name: None)
    monkeypatch.setattr(deployer_module, "write_zone", lambda: None)
    monkeypatch.setattr(
        deployer_module.ProxmoxClient, "invalidate_vm_list_cache", staticmethod(lambda: None)
    )
    logs: list[tuple[str, str]] = []

    result = VMManager(proxmox=fp, tailscale=ft).delete(
        501, name="app", log=lambda level, msg: logs.append((level, msg))
    )

    assert result == {"vmid": 501, "status": "deleted", "tailscale_removed": True}
    assert ft.deleted == ["n123"]
    assert ("stop", 501) in fp.calls
    assert ("delete_vm", 501) in fp.calls
    assert any("Removed app from Tailnet" in msg for _, msg in logs)


def test_delete_skips_tailscale_when_no_api_key(monkeypatch):
    fp = FakeProxmox()
    ft = FakeTailscale(devices={"app": {"nodeId": "n123"}})
    monkeypatch.setattr(deployer_module.settings, "tailscale_api_key", "")
    monkeypatch.setattr(deployer_module, "unregister_vm", lambda name: None)
    monkeypatch.setattr(deployer_module, "write_zone", lambda: None)
    monkeypatch.setattr(
        deployer_module.ProxmoxClient, "invalidate_vm_list_cache", staticmethod(lambda: None)
    )

    result = VMManager(proxmox=fp, tailscale=ft).delete(501, name="app")

    assert result["tailscale_removed"] is False
    assert ft.deleted == []


def test_delete_continues_when_tailscale_device_missing(monkeypatch):
    fp = FakeProxmox()
    ft = FakeTailscale()
    monkeypatch.setattr(deployer_module.settings, "tailscale_api_key", "tskey-test")
    monkeypatch.setattr(deployer_module, "unregister_vm", lambda name: None)
    monkeypatch.setattr(deployer_module, "write_zone", lambda: None)
    monkeypatch.setattr(
        deployer_module.ProxmoxClient, "invalidate_vm_list_cache", staticmethod(lambda: None)
    )
    logs: list[tuple[str, str]] = []

    result = VMManager(proxmox=fp, tailscale=ft).delete(
        501, name="app", log=lambda level, msg: logs.append((level, msg))
    )

    assert result["tailscale_removed"] is False
    assert ("delete_vm", 501) in fp.calls
    assert any("tailnet cleanup skipped" in msg for _, msg in logs)


def test_tailscale_device_id_prefers_node_id():
    assert TailscaleClient.device_id({"nodeId": "n1", "id": 42}) == "n1"


def test_tailscale_device_id_falls_back_to_numeric_id():
    assert TailscaleClient.device_id({"id": 42}) == "42"


# ---------------------------------------------------------------------------
# Job cancellation
# ---------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs_module, "JOBS_FILE", tmp_path / "jobs.json")
    return JobStore()


def test_request_cancel_flags_running_job(store):
    job = store.create("deploy_vm", label="app")
    store.start(job["id"])
    assert store.request_cancel(job["id"]) is True
    assert store.is_cancel_requested(job["id"]) is True


def test_request_cancel_returns_false_for_completed(store):
    job = store.create("deploy_vm", label="app")
    store.complete(job["id"], {"ok": True})
    assert store.request_cancel(job["id"]) is False


def test_request_cancel_returns_false_for_unknown():
    s = JobStore()
    assert s.request_cancel("nope") is False


def test_cancelled_sets_terminal_status(store):
    job = store.create("deploy_vm", label="app")
    store.start(job["id"])
    store.cancelled(job["id"])
    assert store.get(job["id"])["status"] == "cancelled"


# ---------------------------------------------------------------------------
# Deploy honours cancellation checkpoints
# ---------------------------------------------------------------------------


def test_deploy_raises_at_first_checkpoint(monkeypatch):
    monkeypatch.setattr(deployer_module, "hydrate_registry", lambda: None)
    deployer = VMDeployer.__new__(VMDeployer)  # bypass __init__ (no Proxmox/Tailscale)
    with pytest.raises(JobCancelled):
        deployer.deploy(
            name="app", cores=1, memory_gb=1, disk_gb=10, cancel_check=lambda: True
        )


def test_wait_for_tailscale_ip_cancels():
    deployer = VMDeployer.__new__(VMDeployer)
    with pytest.raises(JobCancelled):
        deployer._wait_for_tailscale_ip("app", cancel_check=lambda: True)
