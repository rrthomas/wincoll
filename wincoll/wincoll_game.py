# © Reuben Thomas <rrt@sc3d.org> 2024
# Released under the GPL version 3, or (at your option) any later version.
# mypy: disable-error-code=attr-defined

import os
import warnings
from pathlib import Path
from typing import Callable, Tuple

from aenum import extend_enum  # type: ignore

from chambercourt.game import DEFAULT_VOLUME, Game, Tile
from chambercourt.screen import Screen

# Placeholder for gettext
_: Callable[[str], str] = lambda _: _

# Import pygame, suppressing extra messages that it prints on startup.
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import pygame
    from pygame import Vector2


DIAMOND_IMAGE: pygame.Surface

COLLECT_SOUND: pygame.mixer.Sound
SLIDE_SOUND: pygame.mixer.Sound
UNLOCK_SOUND: pygame.mixer.Sound


for name in ("SAFE", "DIAMOND", "BLOB", "EARTH", "ROCK", "KEY"):
    extend_enum(Tile, name, name.lower())


class WincollGame(Game):
    def __init__(
        self,
        screen: Screen,
        window_size: Tuple[int, int],
        levels_arg: os.PathLike[str],
        hero_image: pygame.Surface,
        die_image: pygame.Surface,
        die_sound: pygame.mixer.Sound,
    ) -> None:
        super().__init__(
            screen, window_size, levels_arg, hero_image, die_image, die_sound
        )
        self.falling = False
        self.diamonds: int

    @staticmethod
    def description() -> str:
        return _("Collect all the diamonds while digging through earth dodging rocks.")

    @staticmethod
    def instructions() -> str:
        # fmt: off
# TRANSLATORS: Please keep this text wrapped to 40 characters. The font
# used in-game is lacking many glyphs, so please test it with your
# language and let me know if I need to add glyphs.
        return _("""\
Collect all the diamonds on each level.
Get a key to turn safes into diamonds.
Avoid falling rocks!

    Z/X - Left/Right   '/? - Up/Down
     or use the arrow keys to move
        S/L - Save/load position
    R - Restart level  Q - Quit game
        F11 - toggle full screen


 (choose with movement keys and digits)

      Press the space bar to play!
"""
        # fmt: on
        )

    @staticmethod
    def screen_size() -> Tuple[int, int]:
        return (640, 512)

    @staticmethod
    def window_size() -> Tuple[int, int]:
        return (240, 240)

    @staticmethod
    def load_assets(levels_path: Path) -> None:
        global DIAMOND_IMAGE
        global COLLECT_SOUND, SLIDE_SOUND, UNLOCK_SOUND
        DIAMOND_IMAGE = pygame.image.load(levels_path / "Diamond.png")
        COLLECT_SOUND = pygame.mixer.Sound(levels_path / "Collect.wav")
        COLLECT_SOUND.set_volume(DEFAULT_VOLUME)
        SLIDE_SOUND = pygame.mixer.Sound(levels_path / "Slide.wav")
        SLIDE_SOUND.set_volume(DEFAULT_VOLUME)
        UNLOCK_SOUND = pygame.mixer.Sound(levels_path / "Unlock.wav")
        UNLOCK_SOUND.set_volume(DEFAULT_VOLUME)

    def init_physics(self) -> None:
        super().init_physics()
        self.diamonds = 0
        for x in range(self.level_width):
            for y in range(self.level_height):
                block = self.get(Vector2(x, y))
                if block in (Tile.DIAMOND, Tile.SAFE):
                    self.diamonds += 1

    def restart_level(self) -> None:
        super().restart_level()
        self.window_pos = (
            (self.screen.surface.get_width() - self.window_scaled_width) // 2,
            (self.screen.surface.get_height() - self.window_scaled_width) // 2
            + 4 * self.screen.window_scale,
        )

    def unlock(self) -> None:
        """Turn safes into diamonds"""
        for x in range(self.level_width):
            for y in range(self.level_height):
                block = self.get(Vector2(x, y))
                if block == Tile.SAFE:
                    self.set(Vector2(x, y), Tile.DIAMOND)
        UNLOCK_SOUND.play()

    def can_move(self, velocity: Vector2) -> bool:
        newpos = self.hero.position + velocity
        block = self.get(newpos)
        if block in (
            Tile.EMPTY,
            Tile.EARTH,
            Tile.DIAMOND,
            Tile.KEY,
        ):
            return True
        if block == Tile.ROCK:
            new_rockpos = self.hero.position + velocity * 2
            return velocity.y == 0 and self.get(new_rockpos) == Tile.EMPTY
        return False

    def do_move(self) -> None:
        newpos = self.hero.position + self.hero.velocity
        block = self.get(newpos)
        if block == Tile.DIAMOND:
            COLLECT_SOUND.play()
            self.diamonds -= 1
        elif block == Tile.KEY:
            self.unlock()
        elif block == Tile.ROCK:
            new_rockpos = newpos + self.hero.velocity
            self.set(new_rockpos, Tile.ROCK)
        self.set(newpos, Tile.EMPTY)

    def can_roll(self, pos: Vector2) -> bool:
        side_block = self.get(pos)
        side_below_block = self.get(pos + Vector2(0, 1))
        return side_block == Tile.EMPTY and side_below_block == Tile.EMPTY

    def die(self) -> None:
        SLIDE_SOUND.stop()
        super().die()

    def do_physics(self) -> None:
        # Put Win into the map data for collision detection.
        self.set(self.hero.position, Tile.HERO)
        new_fall = False

        def fall(oldpos: Vector2, newpos: Vector2) -> None:
            block_below = self.get(newpos + Vector2(0, 1))
            if block_below == Tile.HERO:
                self.dead = True
            self.set(oldpos, Tile.EMPTY)
            self.set(newpos, Tile.ROCK)
            nonlocal new_fall
            if self.falling is False:
                self.falling = True
                SLIDE_SOUND.play(-1)
            new_fall = True

        for x in range(self.level_width):
            for y in range(self.level_height - 1, 0, -1):
                block = self.get(Vector2(x, y))
                if block == Tile.ROCK:
                    pos = Vector2(x, y)
                    pos_below = pos + Vector2(0, 1)
                    block_below = self.get(pos_below)
                    if block_below == Tile.EMPTY:
                        fall(pos, pos_below)
                    elif block_below in (
                        Tile.ROCK,
                        Tile.KEY,
                        Tile.DIAMOND,
                        Tile.BLOB,
                    ):
                        pos_left = pos + Vector2(-1, 0)
                        if self.can_roll(pos_left):
                            fall(pos, pos_left + Vector2(0, 1))
                        else:
                            pos_right = pos + Vector2(1, 0)
                            if self.can_roll(pos_right):
                                fall(pos, pos_right + Vector2(0, 1))

        if new_fall is False:
            self.falling = False
            SLIDE_SOUND.stop()

        self.set(self.hero.position, Tile.EMPTY)

    def show_status(self) -> None:
        super().show_status()
        self.screen.surface.blit(
            DIAMOND_IMAGE,
            (
                (self.window_pos[0] - self.screen.font_pixels) // 2,
                int(1.5 * self.screen.font_pixels),
            ),
        )
        self.screen.print_screen(
            (0, 3),
            str(self.diamonds),
            width=self.window_pos[0],
            align="center",
        )

    def finished(self) -> bool:
        if self.diamonds == 0:
            SLIDE_SOUND.stop()
            return True
        return False
