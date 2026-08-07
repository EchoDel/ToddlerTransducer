import pytest

from toddler_transducer.proxies.fake_raspberry_pi import _GPIO as FakeGPIO
from toddler_transducer.config import ENCODER_VOLUME_NOTCH_PER_STEP, ENCODER_VOLUME_INCREASE_PER_STEP


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


class TestRotaryEncoderVolume:
    @pytest.fixture
    def encoder_and_gpio(self, monkeypatch):
        fake = FakeGPIO()
        monkeypatch.setattr('toddler_transducer.gpio.GPIO', fake)
        from toddler_transducer.gpio import RotaryEncoderVolume
        return RotaryEncoderVolume(3, 4, ENCODER_VOLUME_NOTCH_PER_STEP, ENCODER_VOLUME_INCREASE_PER_STEP), fake

    @pytest.fixture
    def vlc_mgr(self):
        return {'volume': 50}

    def _cw_step(self, encoder, gpio, vlc_mgr, edge: int):
        """Simulate one CLK edge in clockwise direction.
           Rising edge (odd): DT is LOW; Falling edge (even): DT is HIGH."""
        clk = 1 if edge % 2 else 0
        dt = 0 if edge % 2 else 1
        gpio.set_input(3, clk)
        gpio.set_input(4, dt)
        encoder.update(vlc_mgr)

    def _ccw_step(self, encoder, gpio, vlc_mgr, edge: int):
        """Simulate one CLK edge in counter-clockwise direction.
           Rising edge (odd): DT is HIGH; Falling edge (even): DT is LOW."""
        clk = 1 if edge % 2 else 0
        dt = 1 if edge % 2 else 0
        gpio.set_input(3, clk)
        gpio.set_input(4, dt)
        encoder.update(vlc_mgr)

    def test_initial_state(self, encoder_and_gpio):
        encoder, _ = encoder_and_gpio
        assert encoder.counter == 0
        assert encoder.notch_per_step == ENCODER_VOLUME_NOTCH_PER_STEP

    def test_cw_increases_volume(self, encoder_and_gpio, vlc_mgr):
        encoder, gpio = encoder_and_gpio
        for i in range(ENCODER_VOLUME_NOTCH_PER_STEP):
            self._cw_step(encoder, gpio, vlc_mgr, i + 1)
        assert vlc_mgr['volume'] == 50 + ENCODER_VOLUME_INCREASE_PER_STEP

    def test_ccw_decreases_volume(self, encoder_and_gpio, vlc_mgr):
        encoder, gpio = encoder_and_gpio
        vlc_mgr['volume'] = 50
        for i in range(ENCODER_VOLUME_NOTCH_PER_STEP):
            self._ccw_step(encoder, gpio, vlc_mgr, i + 1)
        assert vlc_mgr['volume'] == 50 - ENCODER_VOLUME_INCREASE_PER_STEP

    def test_volume_clamps_at_100(self, encoder_and_gpio, vlc_mgr):
        encoder, gpio = encoder_and_gpio
        vlc_mgr['volume'] = 100
        for i in range(ENCODER_VOLUME_NOTCH_PER_STEP):
            self._cw_step(encoder, gpio, vlc_mgr, i + 1)
        assert vlc_mgr['volume'] == 100

    def test_volume_clamps_at_0(self, encoder_and_gpio, vlc_mgr):
        encoder, gpio = encoder_and_gpio
        vlc_mgr['volume'] = 0
        for i in range(ENCODER_VOLUME_NOTCH_PER_STEP):
            self._ccw_step(encoder, gpio, vlc_mgr, i + 1)
        assert vlc_mgr['volume'] == 0

    def test_partial_turn_does_not_change_volume(self, encoder_and_gpio, vlc_mgr):
        encoder, gpio = encoder_and_gpio
        vlc_mgr['volume'] = 50
        for i in range(ENCODER_VOLUME_NOTCH_PER_STEP - 1):
            self._cw_step(encoder, gpio, vlc_mgr, i + 1)
        assert vlc_mgr['volume'] == 50

    def test_cw_then_ccw_cancels(self, encoder_and_gpio, vlc_mgr):
        encoder, gpio = encoder_and_gpio
        vlc_mgr['volume'] = 50
        for i in range(ENCODER_VOLUME_NOTCH_PER_STEP // 2):
            self._cw_step(encoder, gpio, vlc_mgr, i + 1)
        for i in range(ENCODER_VOLUME_NOTCH_PER_STEP // 2):
            self._ccw_step(encoder, gpio, vlc_mgr, i + 1)
        assert vlc_mgr['volume'] == 50


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
