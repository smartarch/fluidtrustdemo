#!/usr/bin/env python3
import subprocess
import shlex
from utils import CONFIG
from random import getrandbits


def actual_execute_analysis(scenario: str, variable_name: str, variable_value: str) -> bool:
    args = shlex.split("analysis/eclipse -f " + CONFIG.analysis.model_path + " -u " + scenario + " -c " + variable_name + ":" + variable_value)
    decision = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if decision.returncode == 10:
        return True
    return False


def fake_execute_analysis(scenario: str, variable_name: str, variable_value: str) -> bool:
    return not getrandbits(1)


execute_analysis = fake_execute_analysis
if not CONFIG.analysis.fake:
    execute_analysis = actual_execute_analysis
