#!/usr/bin/env python3
#
# © Reuben Thomas <rrt@sc3d.org> 2024-2025
# Released under the GPL version 3, or (at your option) any later version.

import os
import sys
import urllib.parse
from pathlib import Path


# Directory listing generator
def make_directory(
    path: Path, url: str, link_classes: str, dir_link_classes: str
) -> str:
    entries: list[Path] = []
    for entry in path.iterdir():
        if entry.is_dir() and os.access(entry, os.R_OK):
            entries.append(entry)
    pages = ""
    dirs = ""
    for entry in sorted(entries):
        quoted_entry = urllib.parse.quote(entry.name)
        link = f'<a href="$run(path-to-root.in.py,$path)/{url}{quoted_entry}/index.html">{entry.name}</a>'
        if any(subentry.is_dir() for subentry in entry.iterdir()):
            dirs += f'<li><span class="{dir_link_classes}">{link}</span></li>'
        else:
            pages += f'<li><span class="{link_classes}">{link}</span></li>'
    return dirs + pages


# Read command-line arguments
def maybe_argv(n: int) -> str | None:
    return sys.argv[n] if len(sys.argv) > n else None


page = Path(sys.argv[1])
realpath = Path(os.environ["NANCY_INPUT"]) / page
directory_str = maybe_argv(2)
directory = Path(directory_str) if directory_str is not None else page.parent
link_classes = maybe_argv(3) or "nav-link"
dir_link_classes = maybe_argv(4) or "nav-link nav-directory"

path = directory.parent
if directory == Path("."):
    parent_directory = realpath.parent
else:
    parent_directory = realpath.parent.parent

url = urllib.parse.quote(str(path))
if url == ".":
    url = ""
else:
    url += "/"
print(make_directory(parent_directory, url, link_classes, dir_link_classes))
