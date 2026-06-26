import pytest

from toddler_transducer.proxies.fake_raspberry_pi import _GPIO as FakeGPIO


@pytest.fixture(autouse=True)
def fresh_fake_gpio(monkeypatch):
    """Give every test its own isolated FakeGPIO instance."""
    fake = FakeGPIO()
    monkeypatch.setattr('toddler_transducer.gpio.GPIO', fake)
    return fake


class TestFakeGPIO:
    def test_setup_and_input(self):
        gpio = FakeGPIO()
        gpio.set_input(1, 1)
        assert gpio.input(1) == 1

    def test_input_default_zero(self):
        gpio = FakeGPIO()
        assert gpio.input(10) == 0

    def test_constants_exist(self):
        assert FakeGPIO.LOW == 0
        assert FakeGPIO.HIGH == 1
        assert FakeGPIO.BCM == 11
        assert FakeGPIO.BOARD == 10
        assert FakeGPIO.IN == 1
        assert FakeGPIO.OUT == 0


class TestLEDSwitch:
    @pytest.fixture
    def ls(self, monkeypatch):
        fake = FakeGPIO()
        monkeypatch.setattr('toddler_transducer.gpio.GPIO', fake)
        from toddler_transducer.gpio import LEDSwitch
        return LEDSwitch(38, 40)

    def test_initial_state_off(self, ls):
        assert ls.indicator_status is False

    def test_switch_on(self, ls):
        ls.switch_on()
        assert ls.indicator_status is True

    def test_switch_off(self, ls):
        ls.switch_on()
        ls.switch_off()
        assert ls.indicator_status is False

    def test_toggle(self, ls):
        ls.toggle()
        assert ls.indicator_status is True
        ls.toggle()
        assert ls.indicator_status is False

    def test_get_input(self, ls):
        val = ls.get_input()
        assert val in (0, 1)

    def test_update_falling_edge_toggles(self, ls):
        ls.switch_off()
        ls.was_high = True
        ls.get_input = lambda: FakeGPIO.LOW
        ls.update()
        assert ls.indicator_status is True

    def test_update_steady_low_no_toggle(self, ls):
        ls.switch_off()
        ls.get_input = lambda: FakeGPIO.LOW
        ls.was_high = False
        ls.update()
        assert ls.indicator_status is False

    def test_update_high_sets_was_high(self, ls):
        ls.get_input = lambda: FakeGPIO.HIGH
        ls.was_high = False
        ls.update()
        assert ls.was_high is True


class TestGpioUpdateLoop:
    def test_loop_updates_wifi_and_looping(self, monkeypatch):
        from toddler_transducer.gpio import gpio_update_loop
        vlc_mgr = {
            'is_looping': False,
            'toggle_looping': False,
        }
        wifi_mgr = {'wifi_state': False}

        fake = FakeGPIO()
        monkeypatch.setattr('toddler_transducer.gpio.GPIO', fake)
        monkeypatch.setattr('toddler_transducer.gpio.time.sleep', lambda _: (_ for _ in ()).throw(StopIteration))
        with pytest.raises(StopIteration):
            gpio_update_loop(wifi_mgr, vlc_mgr)
