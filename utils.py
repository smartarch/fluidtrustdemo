#!/usr/bin/env python3
import logging
import logging.config
import yaml
import os
from dataclasses import dataclass
from dataclass_wizard import YAMLWizard


def setup_logging(default_path='logging.yaml', default_level=logging.WARN, env_key='LOG_CFG') -> None:
    """Setup logging configuration.

    :param default_path:
    :param default_level:
    :param env_key:
    """
    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = yaml.safe_load(f.read())
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)


@dataclass()
class ConfigAnalysis:
    model_path: str
    fake: bool


@dataclass()
class Simulation:
    lazy_agents: int


@dataclass
class Config(YAMLWizard):
    analysis: ConfigAnalysis
    simulation: Simulation


default_config = Config(analysis=ConfigAnalysis('CaseStudies/bundles/fluidTrustCaseStudy-Simplified/', False),
                        simulation=Simulation(0))


def get_config(default_path='config.yaml', env_key='FLUIDTRUST_CFG') -> Config:
    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        return Config.from_yaml_file(path)
    else:
        return default_config


CONFIG = get_config()
