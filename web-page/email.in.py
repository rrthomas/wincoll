#!/usr/bin/env python3

import sys
from typing import Optional


# Read command-line arguments
def maybe_argv(n: int) -> Optional[str]:
    return sys.argv[n] if len(sys.argv) > n else None


text = maybe_argv(1) or "$include{Email.in.txt}"

print(f'<a href="mailto:$include{{Email.in.txt}}">{text}</a>')
