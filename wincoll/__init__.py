# © Reuben Thomas <rrt@sc3d.org> 2024
# Released under the GPL version 3, or (at your option) any later version.

import importlib.metadata
import os
import sys
import argparse
from enum import StrEnum, auto
from pathlib import Path
import pickle
import warnings
from warnings import warn
from typing import (
    Self,
    Any,
    NoReturn,
    Tuple,
    List,
    Optional,
    Union,
    Iterator,
    ContextManager,
)
from itertools import chain
import locale
import gettext
from datetime import datetime
import contextlib
import zipfile
from tempfile import TemporaryDirectory
import atexit

import i18nparse  # type: ignore
import importlib_resources
from platformdirs import user_data_dir

from .warnings_util import simple_warning, die
from .langdetect import language_code

locale.setlocale(locale.LC_ALL, "")

# Try to set LANG for gettext if not already set
if not "LANG" in os.environ:
    lang = language_code()
    if lang is not None:
        os.environ["LANG"] = lang
i18nparse.activate()

# Set app name for SDL
os.environ["SDL_APP_NAME"] = "WinColl"

# Import pygame, suppressing extra messages that it prints on startup.
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import pygame
    from pygame import Vector2
    import pyscroll  # type: ignore
    import pytmx  # type: ignore
    from . import ptext


VERSION = importlib.metadata.version("wincoll")

with importlib_resources.as_file(importlib_resources.files()) as path:
    cat = gettext.translation("wincoll", path / "locale", fallback=True)
    _ = cat.gettext

DATA_DIR = Path(user_data_dir("wincoll"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
SAVED_POSITION_FILE = DATA_DIR / "saved_position.pkl"


levels: int
levels_files: List[Path]
(level_width, level_height) = (50, 50)  # dimensions of world in blocks
block_pixels = 16  # size of (square) block sprites in pixels
(window_width, window_height) = (15, 15)
(window_pixel_width, window_pixel_height) = (
    window_width * block_pixels,
    window_height * block_pixels,
)
window_scale = 2
window_scaled_width = window_pixel_width * window_scale
TEXT_COLOUR = (255, 255, 255)
BACKGROUND_COLOUR = (0, 0, 255)
window_pos: Tuple[int, int]


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


def show_screen(surface: pygame.Surface) -> None:
    screen.blit(scale_surface(surface), window_pos)
    pygame.display.flip()
    screen.fill(BACKGROUND_COLOUR)
    fade_background()


def load_image(filename: str) -> pygame.Surface:
    with importlib_resources.as_file(importlib_resources.files()) as path:
        return pygame.image.load(path / filename)


DIAMOND_IMAGE = load_image("diamond.png")
SPLAT_IMAGE = load_image("splat.png")
TITLE_IMAGE = load_image("title.png")


COLLECT_SOUND: pygame.mixer.Sound
SLIDE_SOUND: pygame.mixer.Sound
UNLOCK_SOUND: pygame.mixer.Sound
SPLAT_SOUND: pygame.mixer.Sound

DEFAULT_VOLUME = 0.6

screen: pygame.Surface

app_icon = load_image("levels/Win.png")


def init_screen(flags: int = pygame.SCALED) -> None:
    global screen, window_pos
    pygame.display.set_icon(app_icon)
    screen = pygame.display.set_mode((640, 512), flags)
    window_pos = ((screen.get_width() - window_scaled_width) // 2, 12 * window_scale)
    reinit_screen()


def reinit_screen() -> None:
    screen.fill(BACKGROUND_COLOUR)


class Tile(StrEnum):
    GAP = auto()
    BRICK = auto()
    SAFE = auto()
    DIAMOND = auto()
    BLOB = auto()
    EARTH = auto()
    ROCK = auto()
    KEY = auto()
    WIN = auto()


font_pixels = 8 * window_scale


def text_to_screen(pos: Tuple[int, int]) -> Tuple[int, int]:
    return (pos[0] * font_pixels, pos[1] * font_pixels)


def print_screen(pos: Tuple[int, int], msg: str, **kwargs: Any) -> None:
    with importlib_resources.as_file(importlib_resources.files()) as path:
        ptext.draw(  # type: ignore[no-untyped-call]
            msg,
            text_to_screen(pos),
            fontname=str(path / "acorn-mode-1.ttf"),
            fontsize=font_pixels,
            **kwargs,
        )


def quit_game() -> NoReturn:
    pygame.quit()
    sys.exit()


def handle_quit_event() -> None:
    if len(pygame.event.get(pygame.QUIT)) > 0:
        quit_game()


def handle_global_keys(event: pygame.event.Event) -> None:
    if event.key == pygame.K_F11:
        pygame.display.toggle_fullscreen()


FRAMES_PER_SECOND = 30


def scale_surface(surface: pygame.Surface) -> pygame.Surface:
    scaled_width = surface.get_width() * window_scale
    scaled_height = surface.get_height() * window_scale
    scaled_surface = pygame.Surface((scaled_width, scaled_height))
    pygame.transform.scale(surface, (scaled_width, scaled_height), scaled_surface)
    return scaled_surface


class WincollGame:
    def __init__(self, level: int = 1) -> None:
        self.game_surface = pygame.Surface((window_pixel_width, window_pixel_height))
        self.quit = False
        self.dead = False
        self.falling = False
        self.level = level
        self.map_blocks: pytmx.TiledTileLayer
        self.gids: dict[Tile, int]
        self.map_layer: pyscroll.BufferedRenderer
        self.group: pyscroll.PyscrollGroup
        self.hero: Hero
        self.diamonds: int
        self.map_data: pyscroll.data.TiledMapData
        self.joysticks: dict[int, pygame.joystick.JoystickType] = {}

    def restart_level(self) -> None:
        self.dead = False
        tmx_data = pytmx.load_pygame(levels_files[self.level - 1])
        self.map_data = pyscroll.data.TiledMapData(tmx_data)
        self.map_blocks = self.map_data.tmx.layers[0].data

        # Dict mapping tileset GIDs to map gids
        map_gids = self.map_data.tmx.gidmap
        self.gids = {}
        for i in map_gids:
            gid = map_gids[i][0][0]
            tile = Tile(self.map_data.tmx.get_tile_properties_by_gid(gid)["type"])
            self.gids[tile] = gid

        self.map_layer = pyscroll.BufferedRenderer(
            self.map_data, (window_pixel_width, window_pixel_height)
        )
        self.group = pyscroll.PyscrollGroup(map_layer=self.map_layer)

        self.hero = Hero()
        self.hero.position = Vector2(0, 0)
        self.group.add(self.hero)
        self.diamonds = 0
        self.survey()

    def start_level(self) -> None:
        self.restart_level()
        self.save_position()

    def get(self, pos: Vector2) -> Tile:
        # Anything outside the map is a brick
        x, y = int(pos.x), int(pos.y)
        if not ((0 <= x < level_width) and (0 <= y < level_height)):
            return Tile.BRICK
        block = self.map_blocks[y][x]
        if block == 0:  # Missing tiles are gaps
            block = Tile.GAP
        return Tile(self.map_data.tmx.get_tile_properties(x, y, 0)["type"])

    def set(self, pos: Vector2, tile: Tile) -> None:
        self.map_blocks[int(pos.y)][int(pos.x)] = self.gids[tile]
        # Update map
        # FIXME: We invoke protected methods and access protected members.
        ml = self.map_layer
        rect = (int(pos.x), int(pos.y), 1, 1)
        # pylint: disable-next=protected-access
        ml._tile_queue = chain(ml._tile_queue, ml.data.get_tile_images_by_rect(rect))
        # pylint: disable-next=protected-access
        self.map_layer._flush_tile_queue(self.map_layer._buffer)

    def save_position(self) -> None:
        self.set(self.hero.position, Tile.WIN)
        with open(SAVED_POSITION_FILE, "wb") as fh:
            pickle.dump(self.map_blocks, fh)

    def load_position(self) -> None:
        if SAVED_POSITION_FILE.exists():
            with open(SAVED_POSITION_FILE, "rb") as fh:
                self.map_blocks = pickle.load(fh)
            self.map_data.tmx.layers[0].data = self.map_blocks
            self.survey()

    def survey(self) -> None:
        """Count diamonds on level and find start position."""
        self.diamonds = 0
        for x in range(level_width):
            for y in range(level_height):
                block = self.get(Vector2(x, y))
                if block in (Tile.DIAMOND, Tile.SAFE):
                    self.diamonds += 1
                elif block == Tile.WIN:
                    self.hero.position = Vector2(x, y)
                    self.set(self.hero.position, Tile.GAP)

    def unlock(self) -> None:
        """Turn safes into diamonds"""
        for x in range(level_width):
            for y in range(level_height):
                block = self.get(Vector2(x, y))
                if block == Tile.SAFE:
                    self.set(Vector2(x, y), Tile.DIAMOND)
        UNLOCK_SOUND.play()

    def draw(self) -> None:
        self.group.center(self.hero.rect.center)
        self.group.draw(self.game_surface)

    def handle_joysticks(self) -> Tuple[int, int]:
        for event in pygame.event.get(pygame.JOYDEVICEADDED):
            joy = pygame.joystick.Joystick(event.device_index)
            self.joysticks[joy.get_instance_id()] = joy

        for event in pygame.event.get(pygame.JOYDEVICEREMOVED):
            del self.joysticks[event.instance_id]

        dx, dy = (0, 0)
        for joystick in self.joysticks.values():
            axes = joystick.get_numaxes()
            if axes >= 2:  # Hopefully 0=L/R and 1=U/D
                lr = joystick.get_axis(0)
                if lr < -0.5:
                    dx = -1
                elif lr > 0.5:
                    dx = 1
                ud = joystick.get_axis(1)
                if ud < -0.5:
                    dy = -1
                elif ud > 0.5:
                    dy = 1
        return (dx, dy)

    def handle_input(self) -> None:
        pressed = pygame.key.get_pressed()
        dx, dy = (0, 0)
        if pressed[pygame.K_LEFT] or pressed[pygame.K_z]:
            dx -= 1
        if pressed[pygame.K_RIGHT] or pressed[pygame.K_x]:
            dx += 1
        if pressed[pygame.K_UP] or pressed[pygame.K_QUOTE]:
            dy -= 1
        if pressed[pygame.K_DOWN] or pressed[pygame.K_SLASH]:
            dy += 1
        (jdx, jdy) = self.handle_joysticks()
        if (jdx, jdy) != (0, 0):
            (dx, dy) = (jdx, jdy)
        if dx != 0 and self.can_move(Vector2(dx, 0)):
            self.hero.velocity = Vector2(dx, 0)
        elif dy != 0 and self.can_move(Vector2(0, dy)):
            self.hero.velocity = Vector2(0, dy)
        if pressed[pygame.K_l]:
            flash_background()
            self.load_position()
        elif pressed[pygame.K_s]:
            flash_background()
            self.save_position()
        if pressed[pygame.K_r]:
            flash_background()
            self.restart_level()
        if pressed[pygame.K_q]:
            self.quit = True

    def can_move(self, velocity: Vector2) -> bool:
        newpos = self.hero.position + velocity
        block = self.get(newpos)
        if block in (
            Tile.GAP,
            Tile.EARTH,
            Tile.DIAMOND,
            Tile.KEY,
        ):
            return True
        if block == Tile.ROCK:
            new_rockpos = self.hero.position + velocity * 2
            return velocity.y == 0 and self.get(new_rockpos) == Tile.GAP
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
            new_rockpos = self.hero.position + (self.hero.velocity * 2)
            self.set(new_rockpos, Tile.ROCK)
        self.set(self.hero.position + self.hero.velocity, Tile.GAP)

    def can_roll(self, pos: Vector2) -> bool:
        side_block = self.get(pos)
        side_below_block = self.get(pos + Vector2(0, 1))
        return side_block == Tile.GAP and side_below_block == Tile.GAP

    def rockfall(self) -> None:
        new_fall = False

        def fall(oldpos: Vector2, newpos: Vector2) -> None:
            block_below = self.get(newpos + Vector2(0, 1))
            if block_below == Tile.WIN:
                self.dead = True
            self.set(oldpos, Tile.GAP)
            self.set(newpos, Tile.ROCK)
            nonlocal new_fall
            if self.falling is False:
                self.falling = True
                SLIDE_SOUND.play(-1)
            new_fall = True

        for row, blocks in reversed(list(enumerate(self.map_blocks))):
            for col, block in enumerate(blocks):
                if block == self.gids[Tile.ROCK]:
                    pos = Vector2(col, row)
                    pos_below = pos + Vector2(0, 1)
                    block_below = self.get(pos_below)
                    if block_below == Tile.GAP:
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

    def game_to_screen(self, x: int, y: int) -> Tuple[int, int]:
        origin = self.map_layer.get_center_offset()
        return (origin[0] + x * block_pixels, origin[1] + y * block_pixels)

    def splurge(self, sprite: pygame.Surface) -> None:
        """Fill the game area with one sprite."""
        for x in range(level_width):
            for y in range(level_height):
                self.game_surface.blit(sprite, self.game_to_screen(x, y))
        show_screen(self.game_surface)
        pygame.time.wait(3000)

    def show_status(self) -> None:
        print_screen(
            (0, 0),
            _("Level {}:").format(self.level)
            + " "
            + self.map_data.tmx.properties["Title"],
            width=screen.get_width(),
            align="center",
            color="grey",
        )
        screen.blit(DIAMOND_IMAGE, (2 * font_pixels, int(1.5 * font_pixels)))
        print_screen((0, 3), str(self.diamonds), width=window_pos[0], align="center")

    def run(self) -> None:
        clock = pygame.time.Clock()
        while not self.quit and self.level <= levels:
            self.start_level()
            self.show_status()
            show_screen(self.game_surface)
            while not self.quit and self.diamonds > 0:
                self.load_position()
                subframes = 4  # FIXME: global constant
                subframe = 0
                while not self.quit and not self.dead and self.diamonds > 0:
                    clock.tick(FRAMES_PER_SECOND)
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            quit_game()
                        elif event.type == pygame.KEYDOWN:
                            handle_global_keys(event)
                        elif event.type == pygame.JOYDEVICEADDED:
                            joy = pygame.joystick.Joystick(event.device_index)
                            self.joysticks[joy.get_instance_id()] = joy
                        elif event.type == pygame.JOYDEVICEREMOVED:
                            del self.joysticks[event.instance_id]
                    if self.hero.velocity == Vector2(0, 0):
                        self.handle_input()
                        if self.hero.velocity != Vector2(0, 0):
                            self.do_move()
                            subframe = 0
                    self.group.update(1 / subframes)
                    if subframe == subframes - 1:
                        # Put Win into the map data and run physics.
                        self.set(self.hero.position, Tile.WIN)
                        self.rockfall()
                        self.set(self.hero.position, Tile.GAP)
                    self.draw()
                    self.show_status()
                    show_screen(self.game_surface)
                    subframe = (subframe + 1) % subframes
                    if subframe == 0:
                        self.hero.velocity = Vector2(0, 0)
                SLIDE_SOUND.stop()
                if self.dead:
                    SPLAT_SOUND.play()
                    self.game_surface.blit(
                        SPLAT_IMAGE,
                        self.game_to_screen(
                            int(self.hero.position.x), int(self.hero.position.y)
                        ),
                    )
                    self.show_status()
                    show_screen(self.game_surface)
                    pygame.time.wait(1000)
                    self.dead = False
            if self.diamonds == 0:
                self.level += 1
        if self.level > levels:
            self.splurge(Hero().image)


class Hero(pygame.sprite.Sprite):  # pylint: disable=too-few-public-methods
    def __init__(self) -> None:
        pygame.sprite.Sprite.__init__(self)
        self.image = load_image("levels/Win.png")
        self.velocity = Vector2(0, 0)
        self.position = Vector2(0, 0)
        self.rect = self.image.get_rect()

    def update(self, dt: float) -> None:
        self.position += self.velocity * dt
        screen_pos = self.position * block_pixels
        self.rect.topleft = (int(screen_pos.x), int(screen_pos.y))


def clear_keys() -> None:
    for _event in pygame.event.get(pygame.KEYDOWN):
        pass


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
    # fmt: off
    # TRANSLATORS: Please keep this text wrapped to 40 characters. The font
    # used in-game is lacking many glyphs, so please test it with your
    # language and let me know if I need to add glyphs.
    instructions = _("""\
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
    )
    # fmt: on
    instructions_y = 14
    start_level_y = (
        instructions_y + len(instructions.split("\n\n\n")[0].split("\n")) + 1
    )
    play = False
    while not play:
        reinit_screen()
        screen.blit(
            scale_surface(TITLE_IMAGE.convert()),
            (110 * window_scale, 20 * window_scale),
        )
        print_screen((0, 14), instructions, color="grey")
        print_screen(
            (0, start_level_y),
            _("Start level: {}/{}").format(1 if level == 0 else level, levels),
            width=screen.get_width(),
            align="center",
        )
        pygame.display.flip()
        handle_quit_event()
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key == pygame.K_q:
                quit_game()
            elif event.key == pygame.K_SPACE:
                play = True
            elif event.key in (
                pygame.K_z,
                pygame.K_LEFT,
                pygame.K_SLASH,
                pygame.K_DOWN,
            ):
                level = max(1, level - 1)
            elif event.key in (pygame.K_x, pygame.K_RIGHT, pygame.K_QUOTE, pygame.K_UP):
                level = min(levels, level + 1)
            elif event.key in DIGIT_KEYS:
                level = min(levels, level * 10 + DIGIT_KEYS[event.key])
            else:
                level = 0
            handle_global_keys(event)
        clock.tick(FRAMES_PER_SECOND)
    return max(min(level, levels), 1)


def main(argv: List[str] = sys.argv[1:]) -> None:
    # Command-line arguments
    parser = argparse.ArgumentParser(
        description=_(
            "Collect all the diamonds while digging through earth dodging rocks."
        ),
    )
    parser.add_argument(
        "--levels",
        metavar="DIRECTORY",
        help=_("a directory of levels to use instead of the built-in ones"),
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
    args = parser.parse_args(argv)

    global levels, levels_files
    try:
        if args.levels is not None:
            levels_path: Path
            if zipfile.is_zipfile(args.levels):
                tmpdir = TemporaryDirectory()  # pylint: disable=consider-using-with
                levels_path = Path(tmpdir.name)
                with zipfile.ZipFile(args.levels) as z:
                    z.extractall(levels_path)
                atexit.register(lambda tmpdir: tmpdir.cleanup(), tmpdir)
            else:
                levels_path = Path(args.levels)
        else:
            ctx = importlib_resources.as_file(
                importlib_resources.files("wincoll.levels")
            )
            levels_path = ctx.__enter__()
            atexit.register(lambda ctx: ctx.__exit__(None, None, None), ctx)
        levels_files = sorted(
            [item for item in levels_path.iterdir() if item.suffix == ".tmx"]
        )
    except IOError as err:
        die(_("Error reading levels: {}").format(err.strerror))
    levels = len(levels_files)
    if levels == 0:
        die(_("Could not find any levels"))

    pygame.init()
    pygame.mouse.set_visible(False)
    pygame.font.init()
    pygame.key.set_repeat()
    pygame.joystick.init()
    pygame.display.set_caption("WinColl")
    init_screen()

    global COLLECT_SOUND, SLIDE_SOUND, UNLOCK_SOUND, SPLAT_SOUND
    with importlib_resources.as_file(importlib_resources.files()) as path:
        COLLECT_SOUND = pygame.mixer.Sound(path / "Collect.wav")
        COLLECT_SOUND.set_volume(DEFAULT_VOLUME)
        SLIDE_SOUND = pygame.mixer.Sound(path / "Slide.wav")
        SLIDE_SOUND.set_volume(DEFAULT_VOLUME)
        UNLOCK_SOUND = pygame.mixer.Sound(path / "Unlock.wav")
        UNLOCK_SOUND.set_volume(DEFAULT_VOLUME)
        SPLAT_SOUND = pygame.mixer.Sound(path / "Splat.wav")
        SPLAT_SOUND.set_volume(DEFAULT_VOLUME)

    try:
        while True:
            level = instructions()
            game = WincollGame(level)
            game.run()
    except KeyboardInterrupt:
        quit_game()


if __name__ == "__main__":
    main()
