# © Reuben Thomas <rrt@sc3d.org> 2024
# Released under the GPL version 3, or (at your option) any later version.

import importlib.metadata
import os
import sys
from enum import Enum
from pathlib import Path
import pickle
import warnings
from warnings import warn
from typing import NoReturn, Tuple, List, Optional, Union, Iterator
from itertools import chain
import locale
import gettext
from datetime import datetime

import importlib_resources
from typing_extensions import Self
from platformdirs import user_cache_dir

from .warnings_util import simple_warning
from .langdetect import language_code

locale.setlocale(locale.LC_ALL, "")

# Try to set LANG for gettext if not already set
if not "LANG" in os.environ:
    lang = language_code()
    if lang is not None:
        os.environ["LANG"] = lang

# Set app name for SDL
os.environ["SDL_APP_NAME"] = "WinColl"

# Internationalize argparse
with importlib_resources.as_file(importlib_resources.files()) as path:
    gettext.bindtextdomain("argparse", path / "locale")
    gettext.textdomain("argparse")
    import argparse

# Import pygame, suppressing extra messages that it prints on startup.
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import pygame
    import pyscroll  # type: ignore
    import pytmx  # type: ignore
    from . import ptext


VERSION = importlib.metadata.version("wincoll")

with importlib_resources.as_file(importlib_resources.files()) as path:
    cat = gettext.translation("wincoll", path / "locale", fallback=True)
    _ = cat.gettext

CACHE_DIR = Path(user_cache_dir("wincoll"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)
SAVED_POSITION_FILE = CACHE_DIR / "saved_position.pkl"


def die(code: int, msg: str) -> NoReturn:
    warn(msg)
    sys.exit(code)


with importlib_resources.as_file(importlib_resources.files()) as path:
    levels = len(list(Path(path / "levels").glob("Level??.tmx")))
level_size = 50  # length of side of world in blocks
block_pixels = 16  # size of (square) block sprites in pixels
window_blocks = 15
window_pixels = window_blocks * block_pixels
TEXT_COLOUR = (255, 255, 255)
BACKGROUND_COLOUR = (0, 0, 255)


def flash_background() -> None:
    global BACKGROUND_COLOUR
    BACKGROUND_COLOUR = (160, 160, 255)


def fade_background() -> None:
    global BACKGROUND_COLOUR
    BACKGROUND_COLOUR = (
        max(BACKGROUND_COLOUR[0] - 10, 0),
        max(BACKGROUND_COLOUR[0] - 10, 0),
        255,
    )


def load_image(filename: str) -> pygame.Surface:
    with importlib_resources.as_file(importlib_resources.files()) as path:
        return pygame.image.load(path / filename)


SPLAT_IMAGE = load_image("splat.png")
TITLE_IMAGE = load_image("title.png")


COLLECT_SOUND: pygame.mixer.Sound
SLIDE_SOUND: pygame.mixer.Sound
UNLOCK_SOUND: pygame.mixer.Sound
SPLAT_SOUND: pygame.mixer.Sound


screen: pygame.Surface

app_icon = load_image("levels/87.png")

def init_screen(flags: int = pygame.SCALED) -> None:
    global screen
    pygame.display.set_icon(app_icon)
    screen = pygame.display.set_mode((320, 256), flags)
    reinit_screen()


def reinit_screen() -> None:
    screen.fill(BACKGROUND_COLOUR)


# FIXME: get the GIDs from the tileset
class TilesetGids(Enum):
    GAP = 9
    BRICK = 10
    SAFE = 11
    DIAMOND = 12
    BLOB = 13
    EARTH = 14
    ROCK = 15
    KEY = 16
    WIN = 17
    WIN_PLACE = 18


def print_screen(
    pos: Tuple[int, int], msg: str, colour: Optional[Union[pygame.Color, str]] = None
) -> None:
    font_pixels = 8
    with importlib_resources.as_file(importlib_resources.files()) as path:
        ptext.draw(  # type: ignore[no-untyped-call]
            msg,
            (pos[0] * font_pixels, pos[1] * font_pixels),
            fontname=str(path / "acorn-mode-1.ttf"),
            fontsize=8,
            color=colour,
        )


def quit_game() -> NoReturn:
    pygame.quit()
    sys.exit()


def handle_global_event(event: pygame.event.Event) -> None:
    if event.type == pygame.QUIT:
        quit_game()
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_F11:
            pygame.display.toggle_fullscreen()


FRAMES_PER_SECOND = 10


class WincollGame:
    def __init__(self, level: int = 1) -> None:
        self.game_surface = pygame.Surface((window_pixels, window_pixels)).convert()
        self.window_pos = (
            (screen.get_width() - window_pixels) // 2,
            12,
        )
        self.quit = False
        self.dead = False
        self.falling = False
        self.level = level
        self.map_blocks: pytmx.TiledTileLayer
        self.gids: dict[TilesetGids, int]
        self.map_layer: pyscroll.BufferedRenderer
        self.group: pyscroll.PyscrollGroup
        self.hero: Win
        self.diamonds: int
        self.map_data: pyscroll.data.TiledMapData

    def restart_level(self) -> None:
        with importlib_resources.as_file(importlib_resources.files()) as path:
            filename = path / "levels" / f"Level{str(self.level).zfill(2)}.tmx"
        self.dead = False

        tmx_data = pytmx.load_pygame(filename)
        self.map_data = pyscroll.data.TiledMapData(tmx_data)
        self.map_blocks = self.map_data.tmx.get_layer_by_name("Tile Layer 1").data

        # Dict mapping tileset GIDs to map gids
        map_gids = self.map_data.tmx.gidmap
        self.gids = {i: map_gids[i.value + 1][0][0] for i in TilesetGids}

        w, h = window_blocks * block_pixels, window_blocks * block_pixels
        self.map_layer = pyscroll.BufferedRenderer(self.map_data, (w, h))
        self.group = pyscroll.PyscrollGroup(map_layer=self.map_layer)

        self.hero = Win()
        self.hero.position = pygame.Vector2(0, 0)
        self.group.add(self.hero)
        self.diamonds = 0
        self.survey()

    def start_level(self) -> None:
        self.restart_level()
        self.save_position()

    def get(self, pos: pygame.Vector2) -> int:
        # Anything outside the map is a brick
        x, y = int(pos.x), int(pos.y)
        if not ((0 <= x < level_size) and (0 <= y < level_size)):
            return self.gids[TilesetGids.BRICK]
        block = self.map_blocks[y][x]
        if block == 0:  # Missing tiles are gaps
            block = self.gids[TilesetGids.GAP]
        return block  # type: ignore[no-any-return]

    def set(self, pos: pygame.Vector2, gid: int) -> None:
        self.map_blocks[int(pos.y)][int(pos.x)] = gid
        # Update map
        # FIXME: We invoke protected methods and access protected members.
        ml = self.map_layer
        rect = (int(pos.x), int(pos.y), 1, 1)
        # pylint: disable-next=protected-access
        ml._tile_queue = chain(ml._tile_queue, ml.data.get_tile_images_by_rect(rect))
        # pylint: disable-next=protected-access
        self.map_layer._flush_tile_queue(self.map_layer._buffer)

    def save_position(self) -> None:
        self.set(self.hero.position, self.gids[TilesetGids.WIN])
        with open(SAVED_POSITION_FILE, "wb") as fh:
            pickle.dump(self.map_blocks, fh)

    def load_position(self) -> None:
        if SAVED_POSITION_FILE.exists():
            with open(SAVED_POSITION_FILE, "rb") as fh:
                map_blocks = pickle.load(fh)
            for row, blocks in enumerate(map_blocks):
                for col, block in enumerate(blocks):
                    self.set(pygame.Vector2(col, row), block)
            self.survey()

    def survey(self) -> None:
        """Count diamonds on level and find start position."""
        self.diamonds = 0
        for row, blocks in enumerate(self.map_blocks):
            for col, block in enumerate(blocks):
                if block in (
                    self.gids[TilesetGids.DIAMOND],
                    self.gids[TilesetGids.SAFE],
                ):
                    self.diamonds += 1
                elif block == self.gids[TilesetGids.WIN]:
                    self.hero.position = pygame.Vector2(col, row)
                    self.set(self.hero.position, self.gids[TilesetGids.WIN_PLACE])

    def unlock(self) -> None:
        """Turn safes into diamonds"""
        for row, blocks in enumerate(self.map_blocks):
            for col, block in enumerate(blocks):
                if block == self.gids[TilesetGids.SAFE]:
                    self.set(pygame.Vector2(col, row), self.gids[TilesetGids.DIAMOND])
        UNLOCK_SOUND.play()

    def draw(self) -> None:
        self.group.center(self.hero.rect.center)
        self.group.draw(self.game_surface)

    def handle_input(self) -> None:
        pressed = pygame.key.get_pressed()
        self.hero.velocity = pygame.Vector2(0, 0)
        if pressed[pygame.K_LEFT] or pressed[pygame.K_z]:
            self.hero.velocity = pygame.Vector2(-1, 0)
        elif pressed[pygame.K_RIGHT] or pressed[pygame.K_x]:
            self.hero.velocity = pygame.Vector2(1, 0)
        elif pressed[pygame.K_UP] or pressed[pygame.K_QUOTE]:
            self.hero.velocity = pygame.Vector2(0, -1)
        elif pressed[pygame.K_DOWN] or pressed[pygame.K_SLASH]:
            self.hero.velocity = pygame.Vector2(0, 1)
        elif pressed[pygame.K_l]:
            flash_background()
            self.load_position()
        elif pressed[pygame.K_s]:
            flash_background()
            self.save_position()
        elif pressed[pygame.K_r]:
            flash_background()
            self.restart_level()
        elif pressed[pygame.K_q]:
            self.quit = True

    def process_move(self) -> None:
        newpos = self.hero.position + self.hero.velocity
        block = self.get(newpos)
        if block in (self.gids[TilesetGids.GAP], self.gids[TilesetGids.EARTH]):
            pass
        elif block == self.gids[TilesetGids.DIAMOND]:
            COLLECT_SOUND.play()
            self.diamonds -= 1
        elif block == self.gids[TilesetGids.KEY]:
            self.unlock()
        elif block == self.gids[TilesetGids.ROCK]:
            new_rockpos = self.hero.position + (self.hero.velocity * 2)
            if (
                self.hero.velocity.y == 0
                and self.get(new_rockpos) == self.gids[TilesetGids.GAP]
            ):
                self.set(new_rockpos, self.gids[TilesetGids.ROCK])
            else:
                self.hero.velocity = pygame.Vector2(0, 0)
        else:
            self.hero.velocity = pygame.Vector2(0, 0)
        self.set(self.hero.position, self.gids[TilesetGids.GAP])
        self.set(
            self.hero.position + self.hero.velocity, self.gids[TilesetGids.WIN_PLACE]
        )

    def can_roll(self, pos: pygame.Vector2) -> bool:
        side_block = self.get(pos)
        side_below_block = self.get(pos + pygame.Vector2(0, 1))
        return (
            side_block == self.gids[TilesetGids.GAP]
            and side_below_block == self.gids[TilesetGids.GAP]
        )

    def rockfall(self) -> None:
        new_fall = False

        def fall(oldpos: pygame.Vector2, newpos: pygame.Vector2) -> None:
            block_below = self.get(newpos + pygame.Vector2(0, 1))
            if block_below == self.gids[TilesetGids.WIN_PLACE]:
                self.dead = True
            self.set(oldpos, self.gids[TilesetGids.GAP])
            self.set(newpos, self.gids[TilesetGids.ROCK])
            nonlocal new_fall
            if self.falling is False:
                self.falling = True
                SLIDE_SOUND.play(-1)
            new_fall = True

        for row, blocks in reversed(list(enumerate(self.map_blocks))):
            for col, block in enumerate(blocks):
                if block == self.gids[TilesetGids.ROCK]:
                    pos = pygame.Vector2(col, row)
                    pos_below = pos + pygame.Vector2(0, 1)
                    block_below = self.get(pos_below)
                    if block_below == self.gids[TilesetGids.GAP]:
                        fall(pos, pos_below)
                    elif block_below in (
                        self.gids[TilesetGids.ROCK],
                        self.gids[TilesetGids.KEY],
                        self.gids[TilesetGids.DIAMOND],
                        self.gids[TilesetGids.BLOB],
                    ):
                        pos_left = pos + pygame.Vector2(-1, 0)
                        if self.can_roll(pos_left):
                            fall(pos, pos_left + pygame.Vector2(0, 1))
                        else:
                            pos_right = pos + pygame.Vector2(1, 0)
                            if self.can_roll(pos_right):
                                fall(pos, pos_right + pygame.Vector2(0, 1))

        if new_fall is False:
            self.falling = False
            SLIDE_SOUND.stop()

    def game_to_screen(self, x: int, y: int) -> Tuple[int, int]:
        origin = self.map_layer.get_center_offset()
        return (origin[0] + x * block_pixels, origin[1] + y * block_pixels)

    def splurge(self, sprite: pygame.Surface) -> None:
        """Fill the game area with one sprite."""
        surface = pygame.Surface((window_pixels, window_pixels)).convert()
        for row in range(level_size):
            for col in range(level_size):
                surface.blit(sprite, self.game_to_screen(col, row))
        self.show_screen(surface)
        pygame.time.wait(3000)

    def show_screen(self, surface: Optional[pygame.Surface] = None) -> None:
        screen.blit(surface or self.game_surface, self.window_pos)
        pygame.display.flip()
        screen.fill(BACKGROUND_COLOUR)
        fade_background()

    def show_status(self) -> None:
        print_screen((1, 0), _("Level: {}").format(self.level))
        print_screen((23, 0), _("Diamonds: {}").format(self.diamonds))

    def run(self) -> None:
        clock = pygame.time.Clock()

        try:
            while self.level <= levels:
                self.start_level()
                self.show_status()
                self.show_screen()
                while self.diamonds > 0:
                    self.load_position()
                    while not self.dead and self.diamonds > 0:
                        clock.tick(FRAMES_PER_SECOND)
                        self.hero.velocity = pygame.Vector2(0, 0)
                        for event in pygame.event.get():
                            handle_global_event(event)
                        self.handle_input()
                        if self.quit:
                            self.quit = False
                            return
                        self.process_move()
                        self.rockfall()
                        subframes = 4
                        for _subframe in range(subframes):
                            self.group.update(1 / subframes)
                            self.draw()
                            self.show_status()
                            self.show_screen()
                            pygame.time.wait(1000 // FRAMES_PER_SECOND // subframes)
                    if self.dead:
                        SLIDE_SOUND.stop()
                        SPLAT_SOUND.play()
                        self.game_surface.blit(
                            SPLAT_IMAGE,
                            self.game_to_screen(
                                int(self.hero.position.x), int(self.hero.position.y)
                            ),
                        )
                        self.show_screen()
                        pygame.time.wait(1000)
                        self.dead = False
                self.level += 1
            self.splurge(Win().image)
        finally:
            SLIDE_SOUND.stop()


class Win(pygame.sprite.Sprite):  # pylint: disable=too-few-public-methods
    def __init__(self) -> None:
        pygame.sprite.Sprite.__init__(self)
        self.image = load_image("levels/87.png")
        self.velocity = pygame.Vector2(0, 0)
        self.position = pygame.Vector2(0, 0)
        self.rect = self.image.get_rect()

    def update(self, dt: float) -> None:
        self.position += self.velocity * dt
        screen_pos = self.position * block_pixels
        self.rect.topleft = (int(screen_pos.x), int(screen_pos.y))


def clear_keys() -> None:
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            pass
        handle_global_event(event)


def get_key() -> int:
    while True:
        for event in pygame.event.get():
            handle_global_event(event)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    quit_game()
                key: int = event.key
                return key


DIGIT_KEYS = {
    pygame.K_0: 0,
    pygame.K_1: 1,
    pygame.K_2: 2,
    pygame.K_3: 3,
    pygame.K_4: 4,
    pygame.K_5: 5,
    pygame.K_6: 6,
    pygame.K_7: 7,
    pygame.K_8: 8,
    pygame.K_9: 9,
    pygame.K_KP_0: 0,
    pygame.K_KP_1: 1,
    pygame.K_KP_2: 2,
    pygame.K_KP_3: 3,
    pygame.K_KP_4: 4,
    pygame.K_KP_5: 5,
    pygame.K_KP_6: 6,
    pygame.K_KP_7: 7,
    pygame.K_KP_8: 8,
    pygame.K_KP_9: 9,
}


def instructions() -> int:
    """Show instructions and choose start level."""
    clear_keys()
    level = 0
    clock = pygame.time.Clock()
    instructions = _(
        """\
Collect all the diamonds on each level.
Get a key to turn safes into diamonds.
Avoid falling rocks!

    Z/X - Left/Right   '/? - Up/Down
     or use the cursor keys to move
        S/L - Save/load position
    R - Restart level  Q - Quit game
        F11 - toggle full screen


 (choose with movement keys and digits)

      Press the space bar to play!
"""
    )
    instructions_y = 14
    start_level_y = (
        instructions_y + len(instructions.split("\n\n\n")[0].split("\n")) + 1
    )
    while True:
        reinit_screen()
        screen.blit(TITLE_IMAGE, (105, 20))
        print_screen((0, 14), instructions, "grey")
        print_screen(
            (0, start_level_y),
            _("            Start level: {}").format(1 if level == 0 else level),
            "white",
        )
        pygame.display.flip()
        key = get_key()
        clock.tick(FRAMES_PER_SECOND)
        if key == pygame.K_SPACE:
            break
        if key in (pygame.K_z, pygame.K_LEFT, pygame.K_SLASH, pygame.K_DOWN):
            level = max(1, level - 1)
        elif key in (pygame.K_x, pygame.K_RIGHT, pygame.K_QUOTE, pygame.K_UP):
            level = min(levels, level + 1)
        elif key in DIGIT_KEYS:
            level = min(levels, level * 10 + DIGIT_KEYS[key])
        else:
            level = 0
    return max(min(level, levels), 1)


def main(argv: List[str] = sys.argv[1:]) -> None:
    # Command-line arguments
    parser = argparse.ArgumentParser(
        description=_(
            "Collect all the diamonds while digging through earth dodging rocks."
        ),
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=_("%(prog)s {} ({}) by Reuben Thomas <rrt@sc3d.org>").format(
            VERSION, datetime(2024, 12, 16).strftime("%d %b %Y")
        ),
    )
    warnings.showwarning = simple_warning(parser.prog)
    parser.parse_args(argv)

    pygame.init()
    pygame.font.init()
    pygame.key.set_repeat()
    pygame.display.set_caption("WinColl")
    init_screen()

    global COLLECT_SOUND, SLIDE_SOUND, UNLOCK_SOUND, SPLAT_SOUND
    with importlib_resources.as_file(importlib_resources.files()) as path:
        COLLECT_SOUND = pygame.mixer.Sound(path / "Collect.wav")
        SLIDE_SOUND = pygame.mixer.Sound(path / "Slide.wav")
        UNLOCK_SOUND = pygame.mixer.Sound(path / "Unlock.wav")
        SPLAT_SOUND = pygame.mixer.Sound(path / "Splat.wav")

    try:
        while True:
            level = instructions()
            game = WincollGame(level)
            game.run()
    except KeyboardInterrupt:
        quit_game()


if __name__ == "__main__":
    main()
