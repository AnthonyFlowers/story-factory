from __future__ import annotations

import os
import sys

TESTS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TESTS)
sys.path.insert(0, os.path.join(REPO, "scripts"))
FIX = os.path.join(TESTS, "fixtures")
STORIES = os.path.join(FIX, "stories")
TEST_CONFIG = os.path.join(FIX, "factory.config.test.json")
NOREPOS_CONFIG = os.path.join(FIX, "factory.config.norepos.json")  # no repos and no team docs: source checks are SKIPPED
SF = os.path.join(REPO, "scripts", "sf.py")
