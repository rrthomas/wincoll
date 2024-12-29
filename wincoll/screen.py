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


with importlib_resources.as_file(importlib_resources.files()) as path:
    app_icon = pygame.image.load(path / "levels/Win.png")


class Screen:
    def __init__(self) -> None:
        pygame.display.set_icon(app_icon)
        self.window_scale = 2
        self.text_colour = (255, 255, 255)
        self.background_colour = (0, 0, 255)
        self.font_pixels = 8 * self.window_scale
        self._screen = pygame.display.set_mode((640, 512), pygame.SCALED)
        self.reinit_screen()

    def screen(self) -> pygame.Surface:
        return self._screen

    def reinit_screen(self) -> None:
        self._screen.fill(self.background_colour)

    def flash_background(self) -> None:
        self.background_colour = (160, 160, 255)

    def fade_background(self) -> None:
        self.background_colour = (
            max(self.background_colour[0] - 10, 0),
            max(self.background_colour[0] - 10, 0),
            255,
        )

    def scale_surface(self, surface: pygame.Surface) -> pygame.Surface:
        scaled_width = surface.get_width() * self.window_scale
        scaled_height = surface.get_height() * self.window_scale
        scaled_surface = pygame.Surface((scaled_width, scaled_height))
        pygame.transform.scale(surface, (scaled_width, scaled_height), scaled_surface)
        return scaled_surface

    def show_screen(self) -> None:
        pygame.display.flip()
        self._screen.fill(self.background_colour)
        self.fade_background()

    def text_to_screen(self, pos: Tuple[int, int]) -> Tuple[int, int]:
        return (pos[0] * self.font_pixels, pos[1] * self.font_pixels)

    def print_screen(self, pos: Tuple[int, int], msg: str, **kwargs: Any) -> None:
        with importlib_resources.as_file(importlib_resources.files()) as path:
            ptext.draw(  # type: ignore[no-untyped-call]
                msg,
                self.text_to_screen(pos),
                fontname=str(path / "acorn-mode-1.ttf"),
                fontsize=self.font_pixels,
                **kwargs,
            )
