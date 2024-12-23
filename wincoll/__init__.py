# © Reuben Thomas <rrt@sc3d.org> 2024
# Released under the GPL version 3, or (at your option) any later version.

import importlib.metadata
import os
import sys
import argparse
from enum import Enum
from pathlib import Path
import pickle
import warnings
from warnings import warn
from typing import Any, NoReturn, Tuple, List, Optional, Union, Iterator
from itertools import chain
import locale
import gettext
from datetime import datetime

import i18nparse  # type: ignore
import importlib_resources
from typing_extensions import Self
from platformdirs import user_data_dir

from .warnings_util import simple_warning
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
    import pygame_gui
    import pyscroll  # type: ignore
    import pytmx  # type: ignore


VERSION = importlib.metadata.version("wincoll")

with importlib_resources.as_file(importlib_resources.files()) as path:
    cat = gettext.translation("wincoll", path / "locale", fallback=True)
    _ = cat.gettext

CACHE_DIR = Path(user_data_dir("wincoll"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)
SAVED_POSITION_FILE = CACHE_DIR / "saved_position.pkl"


def die(code: int, msg: str) -> NoReturn:
    warn(msg)
    sys.exit(code)


with importlib_resources.as_file(importlib_resources.files()) as path:
    levels = len(list(Path(path / "levels").glob("*.tmx")))
level_size = 50  # length of side of world in blocks
block_pixels = 16  # size of (square) block sprites in pixels
window_blocks = 15
window_pixels = window_blocks * block_pixels
window_scale = 2
scaled_pixels = window_pixels * window_scale
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


DIAMOND_IMAGE = load_image("diamond.png")
SPLAT_IMAGE = load_image("splat.png")
TITLE_IMAGE = load_image("title.png")


COLLECT_SOUND: pygame.mixer.Sound
SLIDE_SOUND: pygame.mixer.Sound
UNLOCK_SOUND: pygame.mixer.Sound
SPLAT_SOUND: pygame.mixer.Sound


screen: pygame.Surface
manager: pygame_gui.UIManager

app_icon = load_image("levels/Win.png")


def init_screen(flags: int = pygame.SCALED) -> None:
    global screen, manager
    pygame.display.set_icon(app_icon)
    screen = pygame.display.set_mode((640, 512), flags)
    with importlib_resources.as_file(importlib_resources.files()) as path:
        manager = pygame_gui.UIManager(
            (screen.get_width(), screen.get_height()),
            theme_path=str(path / "style.json"),
        )
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


font_pixels = 8 * window_scale


def text_to_screen(pos: Tuple[int, int]) -> Tuple[int, int]:
    return (pos[0] * font_pixels, pos[1] * font_pixels)


def quit_game() -> NoReturn:
    pygame.quit()
    sys.exit()


def handle_global_keys(event: pygame.event.Event) -> None:
    if event.key == pygame.K_F11:
        pygame.display.toggle_fullscreen()


FRAMES_PER_SECOND = 50
SCROLL_FRAMES_PER_SECOND = 10


def scale_surface(surface: pygame.Surface) -> pygame.Surface:
    scaled_width = surface.get_width() * window_scale
    scaled_height = surface.get_height() * window_scale
    scaled_surface = pygame.Surface((scaled_width, scaled_height))
    pygame.transform.scale(surface, (scaled_width, scaled_height), scaled_surface)
    return scaled_surface


class WincollGame:
    def __init__(self, level: int = 1) -> None:
        self.game_surface = pygame.Surface((window_pixels, window_pixels))
        self.window_pos = ((screen.get_width() - scaled_pixels) // 2, 12 * window_scale)
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
        self.joysticks: dict[int, pygame.joystick.JoystickType] = {}
        self.diamonds_status: Optional[pygame_gui.elements.ui_text_box.UITextBox] = None
        self.level_status: Optional[pygame_gui.elements.ui_text_box.UITextBox] = None

    def restart_level(self) -> None:
        with importlib_resources.as_file(importlib_resources.files()) as path:
            filename = path / "levels" / f"{str(self.level).zfill(2)}.tmx"
        self.dead = False

        tmx_data = pytmx.load_pygame(filename)
        self.map_data = pyscroll.data.TiledMapData(tmx_data)
        self.map_blocks = self.map_data.tmx.layers[0].data

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

    def handle_joysticks(self) -> None:
        for joystick in self.joysticks.values():
            axes = joystick.get_numaxes()
            if axes >= 2:  # Hopefully 0=L/R and 1=U/D
                lr = joystick.get_axis(0)
                if lr < -0.5:
                    self.hero.velocity = pygame.Vector2(-1, 0)
                elif lr > 0.5:
                    self.hero.velocity = pygame.Vector2(1, 0)
                ud = joystick.get_axis(1)
                if ud < -0.5:
                    self.hero.velocity = pygame.Vector2(0, -1)
                elif ud > 0.5:
                    self.hero.velocity = pygame.Vector2(0, 1)

    def handle_input(self) -> None:
        pressed = pygame.key.get_pressed()
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
        self.handle_joysticks()

    def process_move(self) -> bool:
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
                return False
        else:
            self.hero.velocity = pygame.Vector2(0, 0)
            return False
        self.set(self.hero.position, self.gids[TilesetGids.GAP])
        self.set(
            self.hero.position + self.hero.velocity, self.gids[TilesetGids.WIN_PLACE]
        )
        return True

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
        screen.blit(scale_surface(surface or self.game_surface), self.window_pos)
        manager.draw_ui(screen)
        pygame.display.flip()
        screen.fill(BACKGROUND_COLOUR)
        fade_background()

    def show_status(self) -> None:
        if self.level_status is not None:
            self.level_status.kill()  # type: ignore
        self.level_status = pygame_gui.elements.ui_text_box.UITextBox(
            '<font color="#cccccc">'
            + _("Level {}:").format(self.level)
            + " "
            + self.map_data.tmx.properties["Title"]
            + "</font>",
            pygame.Rect(0, 0, screen.get_width(), font_pixels),
        )
        screen.blit(DIAMOND_IMAGE, (2 * font_pixels, int(1.5 * font_pixels)))
        if self.diamonds_status is not None:
            self.diamonds_status.kill()  # type: ignore
        self.diamonds_status = pygame_gui.elements.ui_text_box.UITextBox(
            str(self.diamonds),
            pygame.Rect(0, 3 * font_pixels, self.window_pos[0], font_pixels),
        )

    def run(self) -> None:
        clock = pygame.time.Clock()
        while not self.quit and self.level <= levels:
            self.start_level()
            self.show_status()
            self.show_screen()
            while not self.quit and self.diamonds > 0:
                self.load_position()
                subframes = 4  # FIXME: global constant
                subframe = 0
                while not self.quit and not self.dead and self.diamonds > 0:
                    dt = clock.tick(FRAMES_PER_SECOND)
                    manager.update(dt)
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
                        else:
                            manager.process_events(event)
                    if self.hero.velocity == pygame.Vector2(0, 0):
                        self.handle_input()
                        if self.hero.velocity != pygame.Vector2(0, 0):
                            if self.process_move():
                                subframe = 0
                    if subframe == subframes - 1:
                        self.rockfall()
                    self.group.update(1 / subframes)
                    self.draw()
                    self.show_status()
                    self.show_screen()
                    pygame.time.wait(1000 // SCROLL_FRAMES_PER_SECOND // subframes)
                    subframe = (subframe + 1) % subframes
                    if subframe == 0:
                        self.hero.velocity = pygame.Vector2(0, 0)
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
                    self.show_screen()
                    pygame.time.wait(1000)
                    self.dead = False
            self.level += 1
        if self.level > levels:
            self.splurge(Win().image)
        self.quit = False
        self.diamonds_status.kill()  # type: ignore
        self.level_status.kill()  # type: ignore


class Win(pygame.sprite.Sprite):  # pylint: disable=too-few-public-methods
    def __init__(self) -> None:
        pygame.sprite.Sprite.__init__(self)
        self.image: pygame.Surface = load_image("levels/Win.png")
        self.velocity = pygame.Vector2(0, 0)
        self.position = pygame.Vector2(0, 0)
        self.rect: pygame.Rect = self.image.get_rect()

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
    instructions = _(
        """\
<font color="#cccccc">Collect all the diamonds on each level.
Get a key to turn safes into diamonds.
Avoid falling rocks!

Z/X - Left/Right   '/? - Up/Down
or use the cursor keys to move
S/L - Save/load position
R - Restart level  Q - Quit game
F11 - toggle full screen


(choose with movement keys and digits)

Press the space bar to play!</font>
"""
    )
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
        inst_box = pygame_gui.elements.ui_text_box.UITextBox(
            instructions,
            pygame.Rect(
                0, instructions_y * font_pixels, screen.get_width(), screen.get_height()
            ),
        )
        level_box = pygame_gui.elements.ui_text_box.UITextBox(
            f'<font color="#ffffff">Start level: {1 if level == 0 else level}/{levels}</font>',
            pygame.Rect(
                0, start_level_y * font_pixels, screen.get_width(), font_pixels
            ),
        )
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_game()
            elif event.type == pygame.KEYDOWN:
                handle_global_keys(event)
                if event.key == pygame.K_ESCAPE:
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
                elif event.key in (
                    pygame.K_x,
                    pygame.K_RIGHT,
                    pygame.K_QUOTE,
                    pygame.K_UP,
                ):
                    level = min(levels, level + 1)
                elif event.key in DIGIT_KEYS:
                    level = min(levels, level * 10 + DIGIT_KEYS[event.key])
                else:
                    level = 0
            else:
                manager.process_events(event)
        dt = clock.tick(FRAMES_PER_SECOND)
        manager.update(dt)
        manager.draw_ui(screen)
        pygame.display.flip()
        inst_box.kill()  # type: ignore
        level_box.kill()  # type: ignore
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
    pygame.joystick.init()
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
