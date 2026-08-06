import pytest

from toddler_transducer import device_config
from toddler_transducer.device_config import (
    add_bound_slave,
    bind_to_master,
    clear_pairing_code,
    get_master_target,
    get_or_create_pairing_code,
    get_sync_token,
    is_master,
    is_slave,
    load_device_config,
    regenerate_pairing_code,
    remove_bound_slave,
    save_device_config,
    set_role,
    unbind_from_master,
    update_sync_status,
)


class TestDeviceConfigPersistence:
    def test_load_empty_when_missing(self):
        assert load_device_config() == {}

    def test_save_and_load_round_trip(self):
        save_device_config({"role": "master", "device_name": "Pi"})
        assert load_device_config() == {"role": "master", "device_name": "Pi"}

    def test_corrupt_file_returns_empty(self, monkeypatch):
        device_config.DEVICE_CONFIG_FILE_PATH.write_text("{not json")
        assert load_device_config() == {}


class TestRole:
    def test_unset_by_default(self):
        assert not is_master()
        assert not is_slave()

    def test_set_master(self):
        set_role("master")
        assert is_master()
        assert not is_slave()

    def test_set_slave_clears_master_fields(self):
        set_role("master")
        add_bound_slave("Slave", "tok")
        set_role("slave")
        config = load_device_config()
        assert config["role"] == "slave"
        assert "bound_slaves" not in config
        assert "pairing_code" not in config

    def test_set_master_clears_slave_fields(self):
        bind_to_master("master.local", 8080, "tok")
        set_role("master")
        config = load_device_config()
        assert config["role"] == "master"
        assert "master_hostname" not in config
        assert "token" not in config


class TestBoundSlaves:
    def test_add_and_remove(self):
        add_bound_slave("Slave", "tok")
        config = load_device_config()
        assert config["bound_slaves"]["Slave"] == {"token": "tok"}
        remove_bound_slave("Slave")
        assert "Slave" not in load_device_config()["bound_slaves"]


class TestPairingCode:
    def test_get_or_create_generates(self):
        code = get_or_create_pairing_code()
        assert code
        assert get_or_create_pairing_code() == code

    def test_regenerate_changes_code(self):
        first = get_or_create_pairing_code()
        second = regenerate_pairing_code()
        assert first != second

    def test_clear_removes_code(self):
        get_or_create_pairing_code()
        clear_pairing_code()
        assert "pairing_code" not in load_device_config()


class TestBinding:
    def test_bind_and_unbind(self):
        bind_to_master("master.local", 8080, "tok123")
        assert is_slave()
        assert get_master_target() == ("master.local", 8080)
        assert get_sync_token() == "tok123"
        unbind_from_master()
        assert is_master()
        assert get_master_target() is None
        assert get_sync_token() is None

    def test_bind_defaults_port(self):
        bind_to_master("master.local", None, "t")
        assert get_master_target() == ("master.local", 8080)

    def test_target_none_when_not_slave(self):
        set_role("master")
        assert get_master_target() is None


class TestSyncStatus:
    def test_update_status(self):
        update_sync_status(last_synced="2026-01-01T00:00:00", last_error=None, song_count=3)
        config = load_device_config()
        assert config["last_synced"] == "2026-01-01T00:00:00"
        assert config["song_count"] == 3
