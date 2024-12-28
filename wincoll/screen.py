# © Reuben Thomas <rrt@sc3d.org> 2024
# Released under the GPL version 3, or (at your option) any later version.

import os
import warnings
from typing import Any, Tuple

import importlib_resources


# Import pygame, suppressing extra messages that it prints on startup.
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import pygame
    from . import ptext


window_scale = 2
TEXT_COLOUR = (255, 255, 255)
BACKGROUND_COLOUR = (0, 0, 255)
_window_pos: Tuple[int, int]
font_pixels = 8 * window_scale

_screen: pygame.Surface

with importlib_resources.as_file(importlib_resources.files()) as path:
    app_icon = pygame.image.load(path / "levels/Win.png")


def init_screen(window_scaled_width: int) -> None:
    global _screen, _window_pos
    pygame.display.set_icon(app_icon)
    _screen = pygame.display.set_mode((640, 512), pygame.SCALED)
    _window_pos = ((_screen.get_width() - window_scaled_width) // 2, 12 * window_scale)
    reinit_screen()


def screen() -> pygame.Surface:
    return _screen


def window_pos() -> Tuple[int, int]:
    return _window_pos


def reinit_screen() -> None:
    _screen.fill(BACKGROUND_COLOUR)


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


def scale_surface(surface: pygame.Surface) -> pygame.Surface:
    scaled_width = surface.get_width() * window_scale
    scaled_height = surface.get_height() * window_scale
    scaled_surface = pygame.Surface((scaled_width, scaled_height))
    pygame.transform.scale(surface, (scaled_width, scaled_height), scaled_surface)
    return scaled_surface


def show_screen(surface: pygame.Surface) -> None:
    _screen.blit(scale_surface(surface), _window_pos)
    pygame.display.flip()
    _screen.fill(BACKGROUND_COLOUR)
    fade_background()


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
