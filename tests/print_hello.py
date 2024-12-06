#! /usr/bin/env python

import os
import sys

if os.environ.get("TEST_ENABLE_COLOR"):
    sys.stdout.write("\x1b[6;30;42m" + "Hello" + "\x1b[0m" + "\n")
else:
    sys.stdout.write("Hello" + "\n")
