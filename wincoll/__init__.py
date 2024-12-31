# © Reuben Thomas <rrt@sc3d.org> 2024
# Released under the GPL version 3, or (at your option) any later version.

import importlib.metadata
import os
import re
import sys
import argparse
import warnings
from typing import List, Callable
import locale
import gettext
from datetime import datetime

import i18nparse  # type: ignore
import importlib_resources

from .warnings_util import simple_warning
from .langdetect import language_code
from .event import quit_game
from .screen import Screen
from .wincoll_game import WincollGame, init_assets
from . import wincoll_game as wincoll_game_module
from . import game as game_module

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


VERSION = importlib.metadata.version("wincoll")

# Placeholder for gettext
_: Callable[[str], str] = lambda _: _


def main(argv: List[str] = sys.argv[1:]) -> None:
    global _

    with importlib_resources.as_file(importlib_resources.files()) as path:
        # Internationalise all modules that need it.
        cat = gettext.translation("wincoll", path / "locale", fallback=True)
        _ = cat.gettext
        game_module._ = cat.gettext
        wincoll_game_module._ = cat.gettext

        # Load assets.
        app_icon = pygame.image.load(path / "levels/Win.png")
        title_image = pygame.image.load(path / "title.png")

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

        pygame.init()
        pygame.display.set_icon(app_icon)
        pygame.mouse.set_visible(False)
        pygame.font.init()
        pygame.key.set_repeat()
        pygame.joystick.init()
        pygame.display.set_caption("WinColl")
        screen = Screen((640, 512), str(path / "acorn-mode-1.ttf"), 2)
        init_assets(path)
        game = WincollGame(screen, (240, 240), args.levels or str(path / "levels"))
        game.window_pos = (
            (screen.surface.get_width() - game.window_scaled_width) // 2,
            12 * game.screen.window_scale,
        )

    try:
        while True:
            level = game.instructions(
                title_image.convert(),
                # fmt: off
# TRANSLATORS: Please keep this text wrapped to 40 characters. The font
# used in-game is lacking many glyphs, so please test it with your
# language and let me know if I need to add glyphs.
                _("""\
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
                ),
                # fmt: on
            )
            game.run(level)
    except KeyboardInterrupt:
        quit_game()


if __name__ == "__main__":
    sys.argv[0] = re.sub(r"__main__.py$", "wincoll", sys.argv[0])
    main()
