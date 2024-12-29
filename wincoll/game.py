# © Reuben Thomas <rrt@sc3d.org> 2024
# Released under the GPL version 3, or (at your option) any later version.

import os
from pathlib import Path
import pickle
import warnings
from itertools import chain
from typing import List, Tuple, Callable
from enum import StrEnum, auto
import zipfile
from tempfile import TemporaryDirectory
import atexit

from platformdirs import user_data_dir

from .warnings_util import die
from .event import quit_game, handle_global_keys
from .screen import Screen


# Placeholder for gettext
_: Callable[[str], str] = lambda _: _

# Import pygame, suppressing extra messages that it prints on startup.
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import pygame
    from pygame import Vector2
    import pyscroll  # type: ignore
    import pytmx  # type: ignore


DATA_DIR = Path(user_data_dir("wincoll"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
SAVED_POSITION_FILE = DATA_DIR / "saved_position.pkl"


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


FRAMES_PER_SECOND = 30

_levels: int


def num_levels() -> int:
    return _levels


levels_files: List[Path]

DIAMOND_IMAGE: pygame.Surface
WIN_IMAGE: pygame.Surface
SPLAT_IMAGE: pygame.Surface

COLLECT_SOUND: pygame.mixer.Sound
SLIDE_SOUND: pygame.mixer.Sound
UNLOCK_SOUND: pygame.mixer.Sound
SPLAT_SOUND: pygame.mixer.Sound

DEFAULT_VOLUME = 0.6


def init_assets(path: Path) -> None:
    global DIAMOND_IMAGE, WIN_IMAGE, SPLAT_IMAGE
    global COLLECT_SOUND, SLIDE_SOUND, UNLOCK_SOUND, SPLAT_SOUND
    DIAMOND_IMAGE = pygame.image.load(path / "diamond.png")
    WIN_IMAGE = pygame.image.load(path / "levels/Win.png")
    SPLAT_IMAGE = pygame.image.load(path / "splat.png")
    COLLECT_SOUND = pygame.mixer.Sound(path / "Collect.wav")
    COLLECT_SOUND.set_volume(DEFAULT_VOLUME)
    SLIDE_SOUND = pygame.mixer.Sound(path / "Slide.wav")
    SLIDE_SOUND.set_volume(DEFAULT_VOLUME)
    UNLOCK_SOUND = pygame.mixer.Sound(path / "Unlock.wav")
    UNLOCK_SOUND.set_volume(DEFAULT_VOLUME)
    SPLAT_SOUND = pygame.mixer.Sound(path / "Splat.wav")
    SPLAT_SOUND.set_volume(DEFAULT_VOLUME)


def init_levels(levels_arg: str) -> None:
    global _levels, levels_files
    try:
        levels_path: Path
        if zipfile.is_zipfile(levels_arg):
            tmpdir = TemporaryDirectory()  # pylint: disable=consider-using-with
            levels_path = Path(tmpdir.name)
            with zipfile.ZipFile(levels_arg) as z:
                z.extractall(levels_path)
            atexit.register(lambda tmpdir: tmpdir.cleanup(), tmpdir)
        else:
            levels_path = Path(levels_arg)
        levels_files = sorted(
            [item for item in levels_path.iterdir() if item.suffix == ".tmx"]
        )
    except IOError as err:
        die(_("Error reading levels: {}").format(err.strerror))
    _levels = len(levels_files)
    if _levels == 0:
        die(_("Could not find any levels"))


class Game:
    def __init__(self, screen: Screen) -> None:
        (self.level_width, self.level_height) = (
            50,
            50,
        )  # dimensions of world in blocks
        self.block_pixels = 16  # size of (square) block sprites in pixels
        (self.window_width, self.window_height) = (15, 15)
        (self.window_pixel_width, self.window_pixel_height) = (
            self.window_width * self.block_pixels,
            self.window_height * self.block_pixels,
        )
        self.screen = screen
        self.window_scaled_width = self.window_pixel_width * self.screen.window_scale
        self.window_pos = (0, 0)
        self.game_surface = pygame.Surface(
            (self.window_pixel_width, self.window_pixel_height)
        )
        self.quit = False
        self.dead = False
        self.falling = False
        self.level = 1
        self.map_blocks: pytmx.TiledTileLayer
        self.gids: dict[Tile, int]
        self.map_layer: pyscroll.BufferedRenderer
        self.group: pyscroll.PyscrollGroup
        self.hero: Hero
        self.diamonds: int
        self.map_data: pyscroll.data.TiledMapData
        self.joysticks: dict[int, pygame.joystick.JoystickType] = {}

    def init_renderer(self) -> None:
        self.map_layer = pyscroll.BufferedRenderer(
            self.map_data, (self.window_pixel_width, self.window_pixel_height)
        )
        self.group = pyscroll.PyscrollGroup(map_layer=self.map_layer)
        self.group.add(self.hero)

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

        self.hero = Hero(self.block_pixels)
        self.hero.position = Vector2(0, 0)

        self.init_renderer()
        self.diamonds = 0
        self.survey()

    def start_level(self) -> None:
        self.restart_level()
        self.save_position()

    def get(self, pos: Vector2) -> Tile:
        # Anything outside the map is a brick
        x, y = int(pos.x), int(pos.y)
        if not ((0 <= x < self.level_width) and (0 <= y < self.level_height)):
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
            self.init_renderer()
            self.survey()

    def survey(self) -> None:
        """Count diamonds on level and find start position."""
        self.diamonds = 0
        for x in range(self.level_width):
            for y in range(self.level_height):
                block = self.get(Vector2(x, y))
                if block in (Tile.DIAMOND, Tile.SAFE):
                    self.diamonds += 1
                elif block == Tile.WIN:
                    self.hero.position = Vector2(x, y)
                    self.set(self.hero.position, Tile.GAP)

    def unlock(self) -> None:
        """Turn safes into diamonds"""
        for x in range(self.level_width):
            for y in range(self.level_height):
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
            self.screen.flash_background()
            self.load_position()
        elif pressed[pygame.K_s]:
            self.screen.flash_background()
            self.save_position()
        if pressed[pygame.K_r]:
            self.screen.flash_background()
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
        return (origin[0] + x * self.block_pixels, origin[1] + y * self.block_pixels)

    def splurge(self, sprite: pygame.Surface) -> None:
        """Fill the game area with one sprite."""
        for x in range(self.level_width):
            for y in range(self.level_height):
                self.game_surface.blit(sprite, self.game_to_screen(x, y))
        self.screen.surface.blit(
            self.screen.scale_surface(self.game_surface), self.window_pos
        )
        self.screen.show_screen()
        pygame.time.wait(3000)

    def show_status(self) -> None:
        self.screen.print_screen(
            (0, 0),
            _("Level {}:").format(self.level)
            + " "
            + self.map_data.tmx.properties["Title"],
            width=self.screen.surface.get_width(),
            align="center",
            color="grey",
        )
        self.screen.surface.blit(
            DIAMOND_IMAGE,
            (2 * self.screen.font_pixels, int(1.5 * self.screen.font_pixels)),
        )
        self.screen.print_screen(
            (0, 3),
            str(self.diamonds),
            width=self.window_pos[0],
            align="center",
        )

    def run(self, level: int) -> None:
        self.quit = False
        self.level = level
        clock = pygame.time.Clock()
        while not self.quit and self.level <= _levels:
            self.start_level()
            self.show_status()
            self.screen.surface.blit(
                self.screen.scale_surface(self.game_surface), self.window_pos
            )
            self.screen.show_screen()
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
                    self.screen.surface.blit(
                        self.screen.scale_surface(self.game_surface), self.window_pos
                    )
                    self.screen.show_screen()
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
                    self.screen.surface.blit(
                        self.screen.scale_surface(self.game_surface), self.window_pos
                    )
                    self.screen.show_screen()
                    pygame.time.wait(1000)
                    self.dead = False
            if self.diamonds == 0:
                self.level += 1
        if self.level > _levels:
            self.splurge(Hero(self.block_pixels).image)


class Hero(pygame.sprite.Sprite):  # pylint: disable=too-few-public-methods
    def __init__(self, block_pixels: int) -> None:
        pygame.sprite.Sprite.__init__(self)
        self.image = WIN_IMAGE
        self.velocity = Vector2(0, 0)
        self.position = Vector2(0, 0)
        self.rect = self.image.get_rect()
        self.block_pixels = block_pixels

    def update(self, dt: float) -> None:
        self.position += self.velocity * dt
        screen_pos = self.position * self.block_pixels
        self.rect.topleft = (int(screen_pos.x), int(screen_pos.y))
