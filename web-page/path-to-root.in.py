#!/usr/bin/env python3
# Output the path from the first argument to the root of the directory

import os
import re
import sys


# Read command-line arguments
page = sys.argv[1]
directory = os.path.dirname(page)

path_to_root = re.sub("[^ ./][^/]*", "..", directory)
if path_to_root == "":
    path_to_root = "."

print(path_to_root)
