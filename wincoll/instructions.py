# © Reuben Thomas <rrt@sc3d.org> 2024
# Released under the GPL version 3, or (at your option) any later version.

import os
import warnings
from typing import Callable

import importlib_resources

from .game import num_levels
from .screen import Screen
from .event import handle_quit_event, quit_game, handle_global_keys


# Placeholder for gettext
_: Callable[[str], str] = lambda _: _

# Import pygame, suppressing extra messages that it prints on startup.
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import pygame

with importlib_resources.as_file(importlib_resources.files()) as path:
    TITLE_IMAGE = pygame.image.load(path / "title.png")


FRAMES_PER_SECOND = 30


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


def instructions(screen: Screen) -> int:
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
        instructions_y + len(instructions.split("\n\n\n", maxsplit=1)[0].split("\n")) + 1
    )
    play = False
    while not play:
        screen.reinit_screen()
        screen.screen().blit(
            screen.scale_surface(TITLE_IMAGE.convert()),
            (110 * screen.window_scale, 20 * screen.window_scale),
        )
        screen.print_screen((0, 14), instructions, color="grey")
        screen.print_screen(
            (0, start_level_y),
            _("Start level: {}/{}").format(1 if level == 0 else level, num_levels()),
            width=screen.screen().get_width(),
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
                level = min(num_levels(), level + 1)
            elif event.key in DIGIT_KEYS:
                level = min(num_levels(), level * 10 + DIGIT_KEYS[event.key])
            else:
                level = 0
            handle_global_keys(event)
        clock.tick(FRAMES_PER_SECOND)
    return max(min(level, num_levels()), 1)
