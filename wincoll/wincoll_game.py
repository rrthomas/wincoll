"""WinColl: Main game class.

© Reuben Thomas <rrt@sc3d.org> 2024-2025
Released under the GPL version 3, or (at your option) any later version.
"""

import gettext
import importlib
import importlib.resources
import os
import warnings
from enum import StrEnum, auto

from chambercourt.game import Game


# Placeholder for gettext
def _(message: str) -> str:
    return message


# Import pygame, suppressing extra messages that it prints on startup.
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import pygame
    from pygame import Color, Vector2


class Tile(StrEnum):
    """An enumeration representing the available map tiles."""

    EMPTY = auto()
    BRICK = auto()
    HERO = auto()
    SAFE = auto()
    DIAMOND = auto()
    BLOB = auto()
    EARTH = auto()
    ROCK = auto()
    KEY = auto()


class WincollGame(Game[Tile]):
    def __init__(self) -> None:
        super().__init__("wincoll", Tile, Tile.HERO, Tile.EMPTY, Tile.BRICK)
        self.falling = False
        self.dead = False
        self.diamonds: int
        self.die_image: pygame.Surface
        self.die_sound: pygame.mixer.Sound

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
""")
        # fmt: on

    screen_size = (640, 512)
    window_size = (240, 240)
    default_background_colour = Color(0, 0, 255)
    window_scale = 2

    diamond_image: pygame.Surface

    collect_sound: pygame.mixer.Sound
    rock_sound: pygame.mixer.Sound
    unlock_sound: pygame.mixer.Sound
    end_level_sound: pygame.mixer.Sound
    end_game_sound: pygame.mixer.Sound

    # Utility methods.
    def reset_falling(self) -> None:
        self.falling = False
        self.rock_sound.stop()

    # Overrides.
    def load_assets(self) -> None:
        super().load_assets()
        self.die_image = pygame.image.load(self.find_asset("Die.png"))
        self.die_sound = pygame.mixer.Sound(self.find_asset("Die.wav"))
        self.die_sound.set_volume(self.default_volume)
        self.diamond_image = pygame.image.load(self.find_asset("Diamond.png"))
        self.collect_sound = pygame.mixer.Sound(self.find_asset("Collect.wav"))
        self.collect_sound.set_volume(self.default_volume)
        self.rock_sound = pygame.mixer.Sound(str(self.find_asset("Slide.wav")))
        self.rock_sound.set_volume(self.default_volume)
        self.unlock_sound = pygame.mixer.Sound(str(self.find_asset("Unlock.wav")))
        self.unlock_sound.set_volume(self.default_volume)
        self.end_level_sound = pygame.mixer.Sound(str(self.find_asset("EndLevel.wav")))
        self.end_level_sound.set_volume(self.default_volume)
        self.end_game_sound = pygame.mixer.Sound(str(self.find_asset("EndGame.wav")))
        self.end_game_sound.set_volume(self.default_volume)

    def init_game(self) -> None:
        super().init_game()
        self.diamonds = 0
        self.dead = False
        for x in range(self.level_width):
            for y in range(self.level_height):
                block = self.get(Vector2(x, y))
                if block in (Tile.DIAMOND, Tile.SAFE):
                    self.diamonds += 1

    def try_move(self, delta: Vector2) -> bool:
        newpos = self.hero.position + delta
        block = self.get(newpos)
        if block in (Tile.EMPTY, Tile.EARTH):
            return True
        elif block == Tile.DIAMOND:
            self.collect_sound.play()
            self.diamonds -= 1
            return True
        elif block == Tile.KEY:
            # Turn safes into diamonds.
            for x in range(self.level_width):
                for y in range(self.level_height):
                    block = self.get(Vector2(x, y))
                    if block == Tile.SAFE:
                        self.set(Vector2(x, y), Tile.DIAMOND)
            self.unlock_sound.play()
            return True
        elif block == Tile.ROCK:
            new_rockpos = self.hero.position + delta * 2
            if delta.y == 0 and self.get(new_rockpos) == Tile.EMPTY:
                self.set(newpos, Tile.EMPTY)
                self.set(new_rockpos, Tile.ROCK)
                return True
        return False

    def update_map(self) -> None:
        new_fall = False

        def rock_to_roll(pos: Vector2) -> bool:
            if self.get(pos) == Tile.ROCK:
                block_below = self.get(pos + Vector2(0, 1))
                return block_below in (
                    Tile.ROCK,
                    Tile.KEY,
                    Tile.DIAMOND,
                    Tile.BLOB,
                )
            return False

        def fall(oldpos: Vector2, newpos: Vector2) -> None:
            block_below = self.get(newpos + Vector2(0, 1))
            if block_below == Tile.HERO and not self.finished():
                self.dead = True
            self.set(oldpos, Tile.EMPTY)
            self.set(newpos, Tile.ROCK)
            nonlocal new_fall
            if self.falling is False:
                self.falling = True
                self.rock_sound.play(-1)
            new_fall = True

        # Put Win into the map for collision detection
        self.set(self.hero.position, Tile.HERO)

        # Scan the map in bottom-to-top left-to-right order (excluding the
        # top row); for each space consider any rock above, then above
        # right, then above left.
        for y in range(self.level_height - 1, 0, -1):
            for x in range(self.level_width):
                pos = Vector2(x, y)
                block = self.get(pos)
                if block == Tile.EMPTY:
                    pos_above = pos + Vector2(0, -1)
                    block_above = self.get(pos_above)
                    if block_above == Tile.ROCK:
                        fall(pos_above, pos)
                    elif block_above == Tile.EMPTY:
                        pos_left = pos_above + Vector2(-1, 0)
                        if rock_to_roll(pos_left):
                            fall(pos_left, pos)
                        else:
                            pos_right = pos_above + Vector2(1, 0)
                            if rock_to_roll(pos_right):
                                fall(pos_right, pos)

        if self.falling and new_fall is False:
            self.reset_falling()

        self.set(self.hero.position, Tile.EMPTY)

    def end_level(self) -> None:
        if self.level < self.num_levels:
            self.end_level_sound.play()
        super().end_level()

    def win_game(self) -> None:
        self.end_game_sound.play()
        super().win_game()

    def show_status(self) -> None:
        super().show_status()
        self.surface.blit(
            self.diamond_image,
            (
                (self.window_pos[0] - self.font_pixels) // 2,
                int(1.5 * self.font_pixels),
            ),
        )
        self.print_screen(
            (0, 3),
            str(self.diamonds),
            width=self.window_pos[0],
            align="center",
        )

    def finished(self) -> bool:
        return self.diamonds == 0 or self.dead

    def stop_play(self) -> None:
        self.reset_falling()
        if self.dead:
            self.die_sound.play()
            self.game_surface.blit(
                self.die_image,
                self.game_to_screen(self.hero.position),
            )
            self.show_status()
            self.show_screen()
            pygame.time.wait(1000)
            self.dead = False

    def main(self, argv: list[str]) -> None:
        global _

        # Internationalise this module.
        with importlib.resources.as_file(importlib.resources.files()) as path:
            cat = gettext.translation("wincoll", path / "locale", fallback=True)
            _ = cat.gettext

        super().main(argv)
