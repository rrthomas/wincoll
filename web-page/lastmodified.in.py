#!/usr/bin/env python3

import os
import sys
from datetime import datetime


# Get command-line arguments
file = sys.argv[1]

time = os.stat(file).st_mtime
dt = datetime.fromtimestamp(time)
print(dt.strftime("%Y/%m/%d"))
