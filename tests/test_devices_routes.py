import pytest

from toddler_transducer.device_config import bind_to_master, is_master, is_slave, load_device_config, set_role


class TestDeviceStatus:
    def test_status_default_unset(self, client):
        resp = client.get("/api/devices/status")
        assert resp.status_code == 200
        assert resp.json["role"] == "unset"

    def test_status_shows_sync_fields(self, client):
        resp = client.get("/api/devices/status")
        assert "last_synced" in resp.json
        assert "song_count" in resp.json
        assert "device_name" in resp.json

    def test_set_role_slave(self, client):
        resp = client.post("/api/devices/role", json={"role": "slave"})
        assert resp.status_code == 200
        assert resp.json == {"ok": True}
        assert is_slave()

    def test_set_role_master(self, client):
        client.post("/api/devices/role", json={"role": "master"})
        assert is_master()

    def test_set_role_invalid(self, client):
        resp = client.post("/api/devices/role", json={"role": "wat"})
        assert resp.status_code == 400


class TestSlaveGuards:
    def test_upload_forbidden_on_slave(self, client):
        client.post("/api/devices/role", json={"role": "slave"})
        resp = client.post("/upload_track", headers={"Referer": "/"})
        assert resp.status_code == 403

    def test_delete_forbidden_on_slave(self, client):
        client.post("/api/devices/role", json={"role": "slave"})
        resp = client.post("/api/delete_track", json={"track_name": "Test Track 1"})
        assert resp.status_code == 403

    def test_home_hides_upload_on_slave(self, client):
        client.post("/api/devices/role", json={"role": "slave"})
        resp = client.get("/")
        assert b"Upload New Track" not in resp.data
        assert b"Devices" in resp.data

    def test_home_shows_upload_on_master(self, client):
        client.post("/api/devices/role", json={"role": "master"})
        resp = client.get("/")
        assert b"Upload New Track" in resp.data


class TestMasterPairing:
    def _become_master(self, client):
        client.post("/api/devices/role", json={"role": "master"})
        return client.get("/api/devices/status").json["pairing_code"]

    def test_master_has_pairing_code(self, client):
        code = self._become_master(client)
        assert code

    def test_pair_with_wrong_code_rejected(self, client):
        self._become_master(client)
        resp = client.post("/api/devices/pair", json={"code": "ZZZZZZ", "device_name": "Slave"})
        assert resp.status_code == 401

    def test_pair_with_correct_code(self, client):
        code = self._become_master(client)
        resp = client.post("/api/devices/pair", json={"code": code, "device_name": "Slave"})
        assert resp.status_code == 200
        data = resp.json
        assert data["ok"] is True
        assert data["token"]
        assert data["device_name"]
        assert "Slave" in client.get("/api/devices/status").json["bound_slaves"]

    def test_pair_when_not_master(self, client):
        resp = client.post("/api/devices/pair", json={"code": "ABCDEF", "device_name": "Slave"})
        assert resp.status_code == 403

    def test_regenerate_pairing_code(self, client):
        first = self._become_master(client)
        resp = client.post("/api/devices/pairing_code")
        assert resp.status_code == 200
        assert resp.json["pairing_code"] != first

    def test_unpair_removes_slave(self, client):
        code = self._become_master(client)
        client.post("/api/devices/pair", json={"code": code, "device_name": "Slave"})
        resp = client.post("/api/devices/unpair", json={"device_name": "Slave"})
        assert resp.status_code == 200
        assert client.get("/api/devices/status").json["bound_slaves"] == []


class TestSyncEndpoints:
    def _pair_and_token(self, client):
        client.post("/api/devices/role", json={"role": "master"})
        code = client.get("/api/devices/status").json["pairing_code"]
        resp = client.post("/api/devices/pair", json={"code": code, "device_name": "Slave"})
        return resp.json["token"]

    def test_manifest_requires_token(self, client):
        resp = client.get("/api/sync/manifest")
        assert resp.status_code == 401

    def test_manifest_with_token(self, client):
        token = self._pair_and_token(client)
        resp = client.get("/api/sync/manifest", headers={"X-Sync-Token": token})
        assert resp.status_code == 200
        assert "abc-123" in resp.json["songs"]
        assert resp.json["songs"]["abc-123"]["rfid_id"] == 1001

    def test_manifest_rejects_bad_token(self, client):
        self._pair_and_token(client)
        resp = client.get("/api/sync/manifest", headers={"X-Sync-Token": "wrong"})
        assert resp.status_code == 401

    def test_file_requires_token(self, client):
        resp = client.get("/api/sync/file/abc-123")
        assert resp.status_code == 401

    def test_file_with_token(self, client):
        token = self._pair_and_token(client)
        resp = client.get("/api/sync/file/abc-123", headers={"X-Sync-Token": token})
        assert resp.status_code == 200
        assert resp.data == b"fake-audio-data"

    def test_file_missing_404(self, client):
        token = self._pair_and_token(client)
        resp = client.get("/api/sync/file/zzz", headers={"X-Sync-Token": token})
        assert resp.status_code == 404


class TestScanAndBind:
    def test_scan_returns_devices(self, client, monkeypatch):
        monkeypatch.setattr(
            "toddler_transducer.web_ui.devices.browse_masters",
            lambda timeout=3.0: [{"device_name": "MasterPi", "hostname": "masterpi.local", "port": 8080}],
        )
        resp = client.post("/api/devices/scan")
        assert resp.status_code == 200
        assert resp.json["devices"][0]["device_name"] == "MasterPi"

    def test_bind_stores_config(self, client, monkeypatch):
        monkeypatch.setattr(
            "toddler_transducer.web_ui.devices.http_post_json",
            lambda *args, **kwargs: {"ok": True, "token": "tok123", "device_name": "MasterPi"},
        )
        resp = client.post("/api/devices/bind", json={"hostname": "masterpi.local", "port": 8080, "code": "ABCDEF"})
        assert resp.status_code == 200
        config = load_device_config()
        assert config["role"] == "slave"
        assert config["master_hostname"] == "masterpi.local"
        assert config["token"] == "tok123"

    def test_bind_requires_hostname_and_code(self, client):
        resp = client.post("/api/devices/bind", json={"hostname": "x.local"})
        assert resp.status_code == 400

    def test_bind_reports_pairing_failure(self, client, monkeypatch):
        monkeypatch.setattr(
            "toddler_transducer.web_ui.devices.http_post_json",
            lambda *args, **kwargs: {"ok": False, "error": "invalid pairing code"},
        )
        resp = client.post("/api/devices/bind", json={"hostname": "x.local", "port": 8080, "code": "NOPE"})
        assert resp.status_code == 401

    def test_unbind_reverts_to_master(self, client):
        bind_to_master("masterpi.local", 8080, "tok123")
        resp = client.post("/api/devices/unbind")
        assert resp.status_code == 200
        assert is_master()
        assert not is_slave()
        assert load_device_config().get("master_hostname") is None

    def test_sync_now_runs_on_slave(self, client, monkeypatch):
        bind_to_master("masterpi.local", 8080, "tok123")
        triggered = {}
        monkeypatch.setattr(
            "toddler_transducer.web_ui.devices.run_sync_once",
            lambda: triggered.update(started=True),
        )
        resp = client.post("/api/devices/sync_now")
        assert resp.status_code == 200
        for _ in range(100):
            if triggered.get("started"):
                return
            import time

            time.sleep(0.01)
        assert triggered["started"]

    def test_sync_now_rejected_on_master(self, client):
        set_role("master")
        resp = client.post("/api/devices/sync_now")
        assert resp.status_code == 400
