#!/usr/bin/env python3

import os
import sys
from datetime import datetime
from pathlib import Path


# Get command-line arguments
page = Path(sys.argv[1])
basename = sys.argv[2]
file = Path(os.environ["NANCY_INPUT"]) / page.parent / basename

time = os.stat(file).st_mtime
dt = datetime.fromtimestamp(time)
print(dt.strftime("%Y/%m/%d"), end="")
