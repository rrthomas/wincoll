#!/usr/bin/env python3
# Convert given Markdown file to HTML fragment on stdout

import sys

import mistletoe


sys.stdout.write(mistletoe.markdown(sys.stdin))
