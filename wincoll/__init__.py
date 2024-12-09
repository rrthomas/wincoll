#!/usr/bin/env python3
#
# © Reuben Thomas <rrt@sc3d.org> 2024
# Released under the GPL version 3, or (at your option) any later version.

import importlib.metadata
import os
import sys
from enum import Enum
import argparse
from pathlib import Path
import pickle
import warnings
from warnings import warn
from typing import NoReturn, Tuple, List, Optional
from collections.abc import Iterator
from itertools import chain

from typing_extensions import Self

import pyscroll  # type: ignore
import pytmx  # type: ignore

from . import ptext
from .warnings_util import simple_warning

# Import pygame, suppressing extra messages that it prints on startup.
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import pygame


VERSION = importlib.metadata.version("wincoll")

CURRENT_DIR = Path(__file__).parent
RESOURCES_DIR = CURRENT_DIR
SAVED_POSITION_FILE = RESOURCES_DIR / "saved_position.pkl"


def die(code: int, msg: str) -> NoReturn:
    warn(msg)
    sys.exit(code)


levels = 16
level_size = 50  # length of side of world in blocks
block_pixels = 16  # size of (square) block sprites in pixels
window_blocks = 15
window_pixels = window_blocks * block_pixels
TEXT_COLOUR = (255, 255, 255)
BACKGROUND_COLOUR = (0, 0, 255)


def load_image(filename: str) -> pygame.Surface:
    return pygame.image.load(RESOURCES_DIR / filename)


SPLAT_IMAGE = load_image("200.png")
TITLE_IMAGE = load_image("title.png")


COLLECT_SOUND: pygame.mixer.Sound
SLIDE_SOUND: pygame.mixer.Sound
UNLOCK_SOUND: pygame.mixer.Sound
SPLAT_SOUND: pygame.mixer.Sound


# pygame's Vector2d class is float-only. We want integer vectors!
class Vector:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def __add__(self, v: Self) -> Self:
        return type(self)(self.x + v.x, self.y + v.y)

    def __mul__(self, n: int) -> Self:
        return type(self)(self.x * n, self.y * n)

    def __iter__(self) -> Iterator[int]:
        yield self.x
        yield self.y


screen: pygame.Surface


def init_screen(flags: int = pygame.SCALED) -> None:
    global screen
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


def print_screen(pos: Tuple[int, int], msg: str) -> None:
    font_pixels = 8
    ptext.draw(  # type: ignore[no-untyped-call]
        msg,
        (pos[0] * font_pixels, pos[1] * font_pixels),
        fontname=str(RESOURCES_DIR / "master.ttf"),
        fontsize=ptext.DEFAULT_FONT_SIZE / 2,
    )


def quit_game() -> NoReturn:
    pygame.quit()
    sys.exit()


def handle_global_input(event: pygame.event.Event) -> None:
    if event.type == pygame.QUIT:
        quit_game()
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_F11:
            pygame.display.toggle_fullscreen()


class WincollGame:
    def __init__(self, level: int = 1) -> None:
        self.game_surface = pygame.Surface((window_pixels, window_pixels)).convert()
        self.window_pos = (
            (screen.get_width() - window_pixels) // 2,
            12,
        )
        self.quit = False
        self.dead = False
        self.level = level
        self.map_blocks: pytmx.TiledTileLayer
        self.gids: dict[TilesetGids, int]
        self.map_layer: pyscroll.BufferedRenderer
        self.group: pyscroll.PyscrollGroup
        self.hero: Win
        self.diamonds: int
        self.map_data: pyscroll.data.TiledMapData

    def restart_level(self) -> None:
        filename = RESOURCES_DIR / f"Level{str(self.level).zfill(2)}.tmx"
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
        self.hero.position = Vector(0, 0)
        self.group.add(self.hero)
        self.diamonds = 0
        self.survey()

    def start_level(self) -> None:
        self.restart_level()
        self.save_position()

    def get(self, pos: Vector) -> int:
        return self.map_blocks[pos.y][pos.x]  # type: ignore[no-any-return]

    def set(self, pos: Vector, gid: int) -> None:
        self.map_blocks[pos.y][pos.x] = gid
        # Update map
        # FIXME: We invoke protected methods and access protected members.
        ml = self.map_layer
        rect = (pos.x, pos.y, 1, 1)
        # pylint: disable-next=protected-access
        ml._tile_queue = chain(ml._tile_queue, ml.data.get_tile_images_by_rect(rect))
        # pylint: disable-next=protected-access
        self.map_layer._flush_tile_queue(self.map_layer._buffer)

    def save_position(self) -> None:
        with open(SAVED_POSITION_FILE, "wb") as fh:
            pickle.dump(self.map_blocks, fh)

    def load_position(self) -> None:
        if SAVED_POSITION_FILE.exists():
            with open(SAVED_POSITION_FILE, "rb") as fh:
                map_blocks = pickle.load(fh)
            for row, blocks in enumerate(map_blocks):
                for col, block in enumerate(blocks):
                    self.set(Vector(col, row), block)
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
                    self.hero.position = Vector(col, row)

    def unlock(self) -> None:
        """Turn safes into diamonds"""
        for row, blocks in enumerate(self.map_blocks):
            for col, block in enumerate(blocks):
                if block == self.gids[TilesetGids.SAFE]:
                    self.set(Vector(col, row), self.gids[TilesetGids.DIAMOND])
        UNLOCK_SOUND.play()

    def draw(self, surface: pygame.Surface) -> None:
        self.group.center(self.hero.rect.center)
        self.group.draw(surface)

    def handle_input(self) -> None:
        for event in pygame.event.get():
            handle_global_input(event)
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_z):
                    self.hero.velocity = Vector(-1, 0)
                elif event.key in (pygame.K_RIGHT, pygame.K_x):
                    self.hero.velocity = Vector(1, 0)
                elif event.key in (pygame.K_UP, pygame.K_QUOTE):
                    self.hero.velocity = Vector(0, -1)
                elif event.key in (pygame.K_DOWN, pygame.K_SLASH):
                    self.hero.velocity = Vector(0, 1)
                elif event.key == pygame.K_l:
                    self.load_position()
                elif event.key == pygame.K_s:
                    self.save_position()
                elif event.key == pygame.K_r:
                    self.restart_level()
                elif event.key == pygame.K_q:
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
                self.hero.velocity = Vector(0, 0)
        else:
            self.hero.velocity = Vector(0, 0)
        self.set(self.hero.position, self.gids[TilesetGids.GAP])
        self.set(self.hero.position + self.hero.velocity, self.gids[TilesetGids.WIN])

    def can_roll(self, pos: Vector) -> bool:
        side_block = self.get(pos)
        side_below_block = self.get(pos + Vector(0, 1))
        return (
            side_block == self.gids[TilesetGids.GAP]
            and side_below_block == self.gids[TilesetGids.GAP]
        )

    def rockfall(self) -> None:
        def fall(oldpos: Vector, newpos: Vector) -> None:
            block_below = self.get(newpos + Vector(0, 1))
            if block_below == self.gids[TilesetGids.WIN]:
                self.dead = True
            self.set(oldpos, self.gids[TilesetGids.GAP])
            self.set(newpos, self.gids[TilesetGids.ROCK])
            SLIDE_SOUND.play()

        for row, blocks in reversed(list(enumerate(self.map_blocks))):
            for col, block in enumerate(blocks):
                if block == self.gids[TilesetGids.ROCK]:
                    pos = Vector(col, row)
                    pos_below = pos + Vector(0, 1)
                    block_below = self.get(pos_below)
                    if block_below == self.gids[TilesetGids.GAP]:
                        fall(pos, pos_below)
                    elif block_below in (
                        self.gids[TilesetGids.ROCK],
                        self.gids[TilesetGids.KEY],
                        self.gids[TilesetGids.DIAMOND],
                        self.gids[TilesetGids.BLOB],
                    ):
                        pos_left = pos + Vector(-1, 0)
                        if self.can_roll(pos_left):
                            fall(pos, pos_left + Vector(0, 1))
                        else:
                            pos_right = pos + Vector(1, 0)
                            if self.can_roll(pos_right):
                                fall(pos, pos_right + Vector(0, 1))

    def update(self) -> None:
        self.process_move()
        self.rockfall()
        self.group.update()

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

    def show_status(self) -> None:
        print_screen((1, 0), f"Level: {self.level}")
        print_screen((23, 0), f"Diamonds: {self.diamonds}")

    def run(self) -> None:
        clock = pygame.time.Clock()
        fps = 10
        pygame.key.set_repeat(1000 // fps)

        while self.level <= levels:
            self.start_level()
            self.show_status()
            while self.diamonds > 0:
                self.load_position()
                while not self.dead and self.diamonds > 0:
                    clock.tick(fps)
                    self.hero.velocity = Vector(0, 0)
                    self.handle_input()
                    if self.quit:
                        self.quit = False
                        return
                    self.update()
                    self.draw(self.game_surface)
                    self.show_status()
                    self.show_screen()
                if self.dead:
                    SPLAT_SOUND.play()
                    self.game_surface.blit(
                        SPLAT_IMAGE,
                        self.game_to_screen(self.hero.position.x, self.hero.position.y),
                    )
                    self.show_screen()
                    pygame.time.wait(1000)
                    self.dead = False
            self.level += 1
        self.splurge(self.hero.image)


class Win(pygame.sprite.Sprite):  # pylint: disable=too-few-public-methods
    def __init__(self) -> None:
        pygame.sprite.Sprite.__init__(self)
        self.image = load_image("87.png")
        self.velocity = Vector(0, 0)
        self.position = Vector(0, 0)
        self.rect = self.image.get_rect()

    def update(self) -> None:
        self.position += self.velocity
        screen_pos = self.position * block_pixels
        self.rect.topleft = (screen_pos.x, screen_pos.y)


def get_key() -> int:
    while True:
        for event in pygame.event.get():
            handle_global_input(event)
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
    level = 0
    while True:
        reinit_screen()
        screen.blit(TITLE_IMAGE, (105, 20))
        print_screen(
            (0, 14),
            """\
Collect all the diamonds on each level.
Get a key to turn safes into diamonds.
Avoid falling rocks!

    Z/X - Left/Right   '/? - Up/Down
     or use the cursor keys to move
        S/L - Save/load position
    R - Restart level  Q - Quit game
        F11 - toggle full screen
    Type level number to select level


      Press the space bar to enjoy!
    """,
        )
        pygame.display.flip()
        key = get_key()
        if key == pygame.K_SPACE:
            break
        if key in DIGIT_KEYS:
            level = level * 10 + DIGIT_KEYS[key]
        else:
            level = 0
    return max(min(level, levels), 1)


def main(argv: List[str] = sys.argv[1:]) -> None:
    # Command-line arguments
    parser = argparse.ArgumentParser(
        description="Collect all the diamonds while digging through earth dodging rocks.",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {VERSION} (05 Dec 2024) by Reuben Thomas <rrt@sc3d.org>",
    )
    warnings.showwarning = simple_warning(parser.prog)
    parser.parse_args(argv)

    pygame.init()
    pygame.font.init()
    pygame.display.set_caption("WinColl")
    init_screen()

    global COLLECT_SOUND, SLIDE_SOUND, UNLOCK_SOUND, SPLAT_SOUND
    COLLECT_SOUND = pygame.mixer.Sound(RESOURCES_DIR / "Collect.wav")
    SLIDE_SOUND = pygame.mixer.Sound(RESOURCES_DIR / "Slide.wav")
    UNLOCK_SOUND = pygame.mixer.Sound(RESOURCES_DIR / "Unlock.wav")
    SPLAT_SOUND = pygame.mixer.Sound(RESOURCES_DIR / "Splat.wav")

    try:
        while True:
            level = instructions()
            game = WincollGame(level)
            game.run()
    except KeyboardInterrupt:
        quit_game()


if __name__ == "__main__":
    main()
