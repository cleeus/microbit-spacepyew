import microbit
import time
import random
import math
import array
from micropython import const

def clamp(x, min_value, max_value):
    return max(min(x, max_value), min_value)

class DoubleBuffered5x5Display:
    def __init__(self):
        self.pixels = array.array("b", range(0, 5 * 5))
        self.old_pixels = array.array("b", range(0, 5 * 5))

    def set_pixel(self, x, y, v):
        x = int(round(x))
        y = int(round(y))
        if x >= 0 and x <= 4 and y >= 0 and y <= 4:
            self.pixels[y * 5 + x] = v

    def clear(self):
        # clear new pixel array
        for p in range(0, len(self.pixels)):
            self.pixels[p] = 0

    def update(self):
        # update real display by pixel differences
        for y in range(0, 5):
            for x in range(0, 5):
                old_px = self.old_pixels[y * 5 + x]
                new_px = self.pixels[y * 5 + x]
                if old_px != new_px:
                    microbit.display.set_pixel(x, y, new_px)

        # swap old and new pixel arrays
        temp = self.old_pixels
        self.old_pixels = self.pixels
        self.pixels = temp

    def scroll(self, s, delay=150):
        microbit.display.scroll(s, delay=delay)
        self.clear()
        self.update()
        self.clear()
        self.update()


class GameObject:
    def __init__(self, name, cs):
        self.name = name
        self.cs = cs
        self.pos_x = 0.0
        self.pos_y = 0.0

        # speed is in pixel per ms
        self.speed_x = 0.0
        self.speed_y = 0.0

        self.is_visible = False

    def draw(self, display):
        if self.is_visible:
            display.set_pixel(self.cs.to_x(self.pos_x), self.cs.to_y(self.pos_y), 5)

    def update(self, delta_t_ms, clipping=True):
        self.pos_x += self.speed_x * delta_t_ms
        self.pos_y += self.speed_y * delta_t_ms
        if clipping:
            self.pos_x = self.cs.clip_x(self.pos_x)
            self.pos_y = self.cs.clip_y(self.pos_y)

    def move_to(self, x, y=None):
        if y is None:
            other = x
            self.pos_x = other.pos_x
            self.pos_y = other.pos_y
        else:
            self.pos_x = x
            self.pos_y = y


class Enemy(GameObject):
    def __init__(self, cs):
        super().__init__("enemy", cs)
        self.base_speed_px_per_s = const(1)
        self.speed_px_per_s = self.base_speed_px_per_s
        self.speed_y = self.cs.to_speed(self.base_speed_px_per_s)
        self.pos_x = self.cs.max_x
        self.pos_y = random.randint(self.cs.min_y, self.cs.max_y)
        self.is_visible = True
        self.evade_countdown_ms = random.randint(5000, 10000)

    def update(self, delta_t_ms, difficulty, projectile, ship):
        self._difficulty_updates(delta_t_ms, difficulty, projectile, ship)

        super().update(delta_t_ms)

        if self.pos_y >= self.cs.max_y:
            self._reflect_speed_y()
        elif self.pos_y <= self.cs.min_y:
            self._reflect_speed_y()

    def _reflect_speed_y(self):
        self.speed_y = -self.speed_y

    def _evade_y(self, obj):
        evade_distance = const(2)
        if (
            obj.is_visible
            and abs(self.pos_y - obj.pos_y) <= evade_distance
        ):
            if (self.pos_y < obj.pos_y and self.speed_y > 0) or (
                self.pos_y > obj.pos_y and self.speed_y < 0
            ):
                self._reflect_speed_y()

    def _evasive_jump(self, projectile):
        new_pos_y = self.pos_y + (1 if random.randint(0, 1) else -1)
        new_pos_y_px = self.cs.to_y(new_pos_y)
        if (
            new_pos_y_px != self.cs.to_y(projectile.pos_y)
            and new_pos_y_px > self.cs.max_y
            and new_pos_y_px < self.cs.min_y
        ):
            self.pos_y = new_pos_y

    def _difficulty_updates(self, delta_t_ms, difficulty, projectile, ship):
        self.speed_px_per_s = self.base_speed_px_per_s * (1.0 + difficulty / 10)
        self.speed_y = math.copysign(
            self.cs.to_speed(self.speed_px_per_s), self.speed_y
        )

        self.evade_countdown_ms -= delta_t_ms

        if self.evade_countdown_ms < 0:
            max_difficulty = const(50)
            self.evade_countdown_ms = (
                clamp(
                    random.randint(1, max(2, max_difficulty - difficulty)),
                    1,
                    max_difficulty,
                )
                * 20
                + 50
            )

            action = random.randint(1, 6)
            if action == 1 or action == 2 or action == 3:
                self._evade_y(projectile if projectile.is_visible else ship)
            elif action == 4 or action == 5:
                self._evasive_jump(projectile)
            elif action == 6:
                self._reflect_speed_y()


class Ship(GameObject):
    def __init__(self, cs):
        super().__init__("ship", cs)
        self.pos_x = self.cs.min_x
        self.pos_y = self.cs.center_y
        self.is_visible = True
        self.gravity_acc = self.cs.to_speed(0.02)

    def update(self, delta_t_ms):
        self.speed_y += delta_t_ms * self.gravity_acc
        super().update(delta_t_ms)
        if self.pos_y >= self.cs.max_y:
            self.speed_y = 0


class Projectile(GameObject):
    def __init__(self, cs):
        super().__init__("proj", cs)
        self.on_miss_callback = None

    def fire(self, start_position, speed_x, on_miss_callback):
        self.move_to(start_position)
        self.is_visible = True
        self.speed_x = speed_x
        self.on_miss_callback = on_miss_callback

    def update(self, delta_t_ms):
        if self.is_visible:
            super().update(delta_t_ms, clipping=False)
            if (
                self.pos_x > self.cs.max_x + 1
                or self.pos_x < self.cs.min_x - 1
                or self.pos_y < self.cs.min_y - 1
                or self.pos_y > self.cs.max_y + 1
            ):
                self.on_miss()

    def on_miss(self):
        self.is_visible = False
        on_miss_callback = self.on_miss_callback
        self.on_miss_callback = None
        on_miss_callback()

    def draw(self, display):
        if self.is_visible:
            display.set_pixel(self.pos_x, self.pos_y, 9)
            display.set_pixel(self.pos_x - 1, self.pos_y, 4)


class BoomAnimation(GameObject):
    def __init__(self, cs):
        super().__init__("boom", cs)
        self.time_ms = 0
        self.animation_done_callback = None

    def start(self, animation_done_callback=None):
        self.is_visible = True
        self.animation_time_ms = 0
        self.animation_done_callback = animation_done_callback

    def update(self, delta_t_ms):
        if self.is_visible:
            self.animation_time_ms += delta_t_ms
            if self.animation_time_ms >= 1000:
                self.is_visible = False
                if self.animation_done_callback is not None:
                    self.animation_done_callback()
                    self.animation_done_callback = None

    def _draw_T(self, display, brigthness):
        for x, y in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            display.set_pixel(self.pos_x + x, self.pos_y + y, brigthness)

    def _draw_X(self, display, brigthness):
        for x, y in [(-1, -1), (1, 1), (-1, 1), (1, -1)]:
            display.set_pixel(self.pos_x + x, self.pos_y + y, brigthness)

    def draw(self, display):
        if self.is_visible:
            if self.animation_time_ms <= 100:
                display.set_pixel(self.pos_x, self.pos_y, 9)
            elif self.animation_time_ms <= 400:
                self._draw_T(display, 9)
            elif self.animation_time_ms <= 700:
                self._draw_T(display, 5)
                self._draw_X(display, 9)
            elif self.animation_time_ms <= 1000:
                self._draw_X(display, 4)


class CoordinateSystem:
    min_x = const(0)
    min_y = const(0)
    max_x = const(4)
    max_y = const(4)
    center_x = const(2)
    center_y = const(2)

    @staticmethod
    def to_x(x):
        return int(round(x))

    @staticmethod
    def to_y(y):
        return int(round(y))

    @staticmethod
    def clip_x(x):
        return clamp(x, CoordinateSystem.min_x, CoordinateSystem.max_x)

    @staticmethod
    def clip_y(y):
        return clamp(y, CoordinateSystem.min_y, CoordinateSystem.max_y)

    @staticmethod
    def to_speed(speed_in_pixel_per_second):
        return speed_in_pixel_per_second / 1000.0


class JoystickAxisAutoCalibration:
    def __init__(self, initial_center):
        self.center = initial_center
        self.values = [self.center]
        self.capacity = const(32)

    def add(self, value):
        if len(self.values) >= self.capacity:
            self.values.pop(0)
        self.values.append(value)

    def analyze(self):
        if len(self.values) < self.capacity / 2:
            return

        ref_v = self.values[0]
        v_sum = 0
        position_is_stable = True
        for v in self.values:
            v_sum += v
            if abs(ref_v - v) > 1:
                position_is_stable = False
                break

        if not position_is_stable:
            return

        avg_v = v_sum / len(self.values)

        if abs(avg_v - self.center) < 5:
            self.center = avg_v


class SoundSystem:
    # SoundEffect(freq_start=500, freq_end=2500, duration=500, vol_start=255, vol_end=0, waveform=WAVEFORM_SQUARE, fx=FX_NONE, shape=SHAPE_LOG)
    FIRE = microbit.audio.SoundEffect(
        duration=300,
        freq_start=4000,
        freq_end=1200,
        vol_start=64,
        vol_end=0,
        waveform=microbit.audio.SoundEffect.WAVEFORM_SAWTOOTH,
        fx=microbit.audio.SoundEffect.FX_NONE,
        shape=microbit.audio.SoundEffect.SHAPE_LINEAR,
    )
    BOOM = microbit.audio.SoundEffect(
        duration=800,
        freq_start=2000,
        freq_end=1500,
        vol_start=255,
        vol_end=0,
        waveform=microbit.audio.SoundEffect.WAVEFORM_NOISE,
        fx=microbit.audio.SoundEffect.FX_NONE,
        shape=microbit.audio.SoundEffect.SHAPE_LINEAR,
    )
    MISS = microbit.audio.SoundEffect(
        duration=200,
        freq_start=800,
        freq_end=300,
        vol_start=112,
        vol_end=0,
        waveform=microbit.audio.SoundEffect.WAVEFORM_SINE,
        fx=microbit.audio.SoundEffect.FX_NONE,
        shape=microbit.audio.SoundEffect.SHAPE_LINEAR,
    )

    def play(self, sound_effect):
        microbit.audio.play(sound_effect, wait=False)


class SpacePyew:
    def __init__(self):
        self.cs = CoordinateSystem()
        self.sound = SoundSystem()
        self.jsycal = JoystickAxisAutoCalibration(microbit.pin2.read_analog())

        self.display = DoubleBuffered5x5Display()
        # self.display = Direct5x5Display()

        self.delta_t_ms = 0.0
        self.start_t_ms = 0.0

        self.enemy = Enemy(self.cs)
        self.ship = Ship(self.cs)
        self.projectile = Projectile(self.cs)
        self.boom = BoomAnimation(self.cs)

        self.difficulty = 0

    def measure_delta_t(self):
        now_ms = time.ticks_us() / 1000.0
        self.delta_t_ms = now_ms - self.start_t_ms
        self.start_t_ms = time.ticks_us() / 1000.0

    def run(self):
        self.measure_delta_t()

        while True:
            self.measure_delta_t()
            self.process_input()
            self.update_game_state()
            self.draw()
            idle(10)

    def process_input(self):
        global button_e, button_f, button_d

        joystick_y = microbit.pin2.read_analog()
        self.jsycal.add(joystick_y)
        self.jsycal.analyze()

        joystick_y_delta = joystick_y - self.jsycal.center

        if abs(joystick_y_delta) > 3:
            self.ship.speed_y = -self.cs.to_speed(joystick_y_delta / 32.0)

        button_press_speed = const(2)
        # down
        if button_e.was_pressed():
            self.ship.pos_y += 1
            self.ship.speed_y = self.cs.to_speed(button_press_speed)

        # up
        if microbit.button_a.was_pressed() or button_d.was_pressed():
            self.ship.pos_y -= 1
            self.ship.speed_y = self.cs.to_speed(-button_press_speed)

        # B or right
        if microbit.button_b.was_pressed() or button_f.was_pressed():
            self.ship_fires()

        # left
        if button_c.was_pressed():
            self.increase_difficulty()

    def update_game_state(self):
        self.ship.update(self.delta_t_ms)
        self.projectile.update(self.delta_t_ms)
        self.enemy.update(self.delta_t_ms, self.difficulty, self.projectile, self.ship)

        self.check_projectile_hits_enemy()

        self.boom.update(self.delta_t_ms)

    def on_hit_enemy(self):
        global rumbler

        self.enemy.is_visible = False
        self.projectile.is_visible = False
        self.sound.play(self.sound.BOOM)
        self.boom.move_to(self.enemy)
        self.boom.start(lambda: self.on_boom_done())
        rumbler.play(rumbler.BOOM)

    def on_boom_done(self):
        self.increase_difficulty()
        self.respawn_enemy()

    def increase_difficulty(self):
        self.difficulty += 1
        self.display.scroll("%d" % self.difficulty, delay=100)
        self.measure_delta_t()
        self.measure_delta_t()

    def respawn_enemy(self):
        self.enemy.move_to(self.cs.max_x, random.randint(self.cs.min_y, self.cs.max_y))
        self.enemy.is_visible = True

    def check_projectile_hits_enemy(self):
        if self.projectile.is_visible and self.enemy.is_visible:
            if self.cs.to_x(self.projectile.pos_x) >= self.cs.to_x(
                self.enemy.pos_x
            ) and self.cs.to_y(self.projectile.pos_y) == self.cs.to_y(self.enemy.pos_y):
                self.on_hit_enemy()

    def draw(self):
        self.display.clear()

        self.projectile.draw(self.display)
        self.boom.draw(self.display)
        self.enemy.draw(self.display)
        self.ship.draw(self.display)

        self.display.update()

    def ship_fires(self):
        global rumbler

        if not self.projectile.is_visible and self.enemy.is_visible:
            self.sound.play(self.sound.FIRE)
            rumbler.play(rumbler.BEEP)

            self.projectile.fire(
                self.ship,
                self.cs.to_speed(const(6)),
                on_miss_callback=lambda: self.on_miss_callback(),
            )

    def on_miss_callback(self):
        self.sound.play(self.sound.MISS)


class RumbleEffect:
    def __init__(
        self,
        duration_ms,
        strength_start=100,
        strength_end=100,
        freq_start=1953,
        freq_end=1953,
    ):
        self.duration_us = int(duration_ms * 1000)
        self.strength_start = strength_start
        self.strength_end = strength_end
        self.freq_start = freq_start
        self.freq_end = freq_end


class JoystickRumbleSystem:
    BOOM = RumbleEffect(
        500, strength_start=100, strength_end=10, freq_start=100, freq_end=5
    )
    BEEP = RumbleEffect(
        150, strength_start=50, strength_end=10, freq_start=100, freq_end=1000
    )

    def __init__(self, microbit_pin):
        self.pin = microbit_pin
        self.pin.set_pull(self.pin.PULL_UP)
        self.effect = None
        self.start_t_us = 0
        self.elapsed_t_us = 0

    def update(self):
        if self.effect:
            now_t_us = time.ticks_us()
            delta_t_us = now_t_us - self.start_t_us
            self.start_t_us = now_t_us
            self.elapsed_t_us += delta_t_us

            if self.elapsed_t_us >= self.effect.duration_us:
                self.stop()
            else:
                self._apply_pwm()

    @staticmethod
    def _strength_to_pwm_duty(strength):
        strength = clamp(strength, 0, 100)
        return int(((100 - strength) * 1023) / 100)

    @staticmethod
    def _freq_to_pwm_period(freq):
        freq = clamp(int(round(freq)), 1, 3906)
        period_us = int(round(1000000 / freq))
        if period_us < 256:
            period_us = 256
        return period_us

    def play(self, effect):
        self.effect = effect
        self.start_t_us = time.ticks_us()
        self.elapsed_t_us = 0
        self._apply_pwm()

    def _apply_pwm(self):
        if self.effect is None or self.effect.duration_us <= 0:
            return

        progress = self.elapsed_t_us / self.effect.duration_us
        freq = microbit.scale(
            progress,
            from_=(0.0, 1.0),
            to=(self.effect.freq_start, self.effect.freq_end),
        )
        strength = microbit.scale(
            progress,
            from_=(0.0, 1.0),
            to=(self.effect.strength_start, self.effect.strength_end),
        )

        self.pin.set_analog_period_microseconds(self._freq_to_pwm_period(freq))
        self.pin.write_analog(self._strength_to_pwm_duty(strength))

    def stop(self):
        self.pin.write_digital(1)
        self.effect = None


class MyButton:
    def __init__(self, microbit_pin):
        self.pin = microbit_pin
        self.pin.set_pull(self.pin.PULL_UP)
        self.pressed = False

        self.debounced_level = 1
        self.debounce_time_ms = 1.0
        self.debounce_countdown_ms = 0.0
        self.last_poll_time_us = 0

    def update(self):
        if self.debounce_countdown_ms > 0:
            now_us = time.ticks_us()
            delta_us = now_us - self.last_poll_time_us
            self.last_poll_time_us = now_us
            if delta_us == 0:
                delta_us = 1
            self.debounce_countdown_ms -= delta_us / 1000.0

        if self.debounce_countdown_ms > 0:
            return

        level = self.pin.read_digital()

        # begin of push
        if self.debounced_level == 1 and level == 0:
            self.debounce_countdown_ms = self.debounce_time_ms
            self.debounced_level = level
            self.pressed = True

        # begin of release
        if self.debounced_level == 0 and level == 1:
            self.debounce_countdown_ms = self.debounce_time_ms
            self.debounced_level = level

    def was_pressed(self):
        pressed = self.pressed
        self.pressed = False
        return pressed


button_c = MyButton(microbit.pin12)  # left
button_d = MyButton(microbit.pin13)  # up
button_e = MyButton(microbit.pin14)  # down
button_f = MyButton(microbit.pin15)  # right
rumbler = JoystickRumbleSystem(microbit.pin16)


def idle(duration_ms):
    start_us = time.ticks_us()
    while duration_ms > 0:
        now_us = time.ticks_us()
        delta_us = now_us - start_us
        start_us = now_us
        if delta_us == 0:
            delta_us = 1
        delta_t_ms = delta_us / 1000.0
        duration_ms -= delta_t_ms

        button_c.update()
        button_d.update()
        button_e.update()
        button_f.update()
        rumbler.update()

        microbit.sleep(0.5)


def main():
    microbit.display.scroll("SpacePyew!")

    sp = SpacePyew()
    sp.run()


main()
