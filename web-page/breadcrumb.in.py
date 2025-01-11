#!/usr/bin/env python3

import os.path
import sys


# Get command-line arguments
page = sys.argv[1]

# Extract page name and normalize path
path = os.path.dirname(page)
if path == ".":
    path = ""
parents = path.removesuffix("$")

# Generate and print breadcrumb
desc = os.path.basename(parents)
tree = ""
classes = "breadcrumb-item breadcrumb-active"
while parents not in ("", ".", "/"):
    tree = f'<li class="{classes}">' + \
        f'<a href="$include{{path-to-root.in.py,$path}}{parents}">{desc}</a>' + \
        f'</li>{tree}'
    classes = "breadcrumb-item"
    parents = os.path.dirname(parents)
    desc = os.path.basename(parents)
print(
    '<li class="breadcrumb-item">' + \
    '<a href="$include{path-to-root.in.py,$path}">$include{Title.in.txt}</a>' + \
    f'</li>{tree}'
)
