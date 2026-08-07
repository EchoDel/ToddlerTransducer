import pytest

from toddler_transducer.proxies import SimpleMFRC522Proxy


class TestSimpleMFRC522Proxy:
    def test_always_none_returns_none(self):
        proxy = SimpleMFRC522Proxy(always_none=True)
        result = proxy.read_id_no_block()
        assert result is None

    def test_always_none_returns_previous_value(self):
        proxy = SimpleMFRC522Proxy(always_none=True)
        proxy.previous_value = 123
        result = proxy.read_id_no_block()
        assert result == 123

    def test_validate_persist_value_chance_raises(self):
        with pytest.raises(ValueError, match='persist_value_chance'):
            SimpleMFRC522Proxy(always_none=False, persist_value_chance=1.5)

    def test_validate_returned_value_chance_raises(self):
        with pytest.raises(ValueError, match='returned_value_chance'):
            SimpleMFRC522Proxy(always_none=False, returned_value_chance=-0.1)

    def test_validate_none_values_ok(self):
        proxy = SimpleMFRC522Proxy(always_none=False, persist_value_chance=None, returned_value_chance=None)
        assert proxy is not None
