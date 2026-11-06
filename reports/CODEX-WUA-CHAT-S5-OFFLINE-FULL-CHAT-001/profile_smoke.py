"""Use the canonical launcher implementation with an automated fixture exit."""
from dataclasses import replace
from pathlib import Path
import sys

from web_alarm.launcher import CONFIG_PATH, load_launch, run_script

profile = load_launch(Path(__file__).with_name("launch_stage5.json"))
assert not profile.standard and load_launch(CONFIG_PATH).standard
raise SystemExit(run_script(replace(profile, args=("--smoke",)), out=sys.stdout, colors=False))
