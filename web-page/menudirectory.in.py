#!/usr/bin/env python3
#
# © Reuben Thomas <rrt@sc3d.org> 2024
# Released under the GPL version 3, or (at your option) any later version.

import os
import sys
import urllib.parse
from typing import Optional


# Directory listing generator
def make_directory(
    path: str, url: str, link_classes: str, dir_link_classes: str
) -> str:
    entries = []
    for entry in os.listdir(path):
        entry_path = os.path.join(path, entry)
        if os.path.isdir(entry_path) and os.access(entry_path, os.R_OK):
            entries.append(entry)
    pages = ""
    dirs = ""
    for entry in sorted(entries):
        quoted_entry = urllib.parse.quote(entry)
        link = f'<a href="$include{{path-to-root.in.py,$path}}/{url}{quoted_entry}/">{entry}</a>'
        entry_path = os.path.join(path, entry)
        add_directory = False
        for subentry in os.listdir(entry_path):
            subentry_path = os.path.join(entry_path, subentry)
            if os.path.isdir(subentry_path):
                add_directory = True
                break
        if add_directory:
            dirs += f'<li><span class="{dir_link_classes}">{link}</span></li>'
        else:
            pages += f'<li><span class="{link_classes}">{link}</span></li>'
    return dirs + pages


# Read command-line arguments
def maybe_argv(n: int) -> Optional[str]:
    return sys.argv[n] if len(sys.argv) > n else None


page = sys.argv[1]
directory = maybe_argv(2) or os.path.dirname(page)
link_classes = maybe_argv(3) or "nav-link"
dir_link_classes = maybe_argv(4) or "nav-link nav-directory"

# Get globals from environment variables
DocumentRoot = os.environ["LINTON_DOCUMENT_ROOT"]

path = os.path.dirname(directory)
if path == "./":
    path = ""
directory = os.path.join(DocumentRoot, path)
url = urllib.parse.quote(path)
if url != "":
    url += "/"
print(
    make_directory(directory, url, link_classes, dir_link_classes)
)
