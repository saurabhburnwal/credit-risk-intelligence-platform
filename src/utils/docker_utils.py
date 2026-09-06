"""
Docker environment utilities and container diagnostics.
"""

import os
from pathlib import Path


def is_running_in_docker() -> bool:
    """Detects if code is executing inside a Docker container."""
    return Path("/.dockerenv").exists() or os.getenv("DOCKER_CONTAINER") == "1"


def get_system_diagnostics() -> dict:
    """Returns basic system environment details."""
    in_docker = is_running_in_docker()
    return {
        "in_docker": in_docker,
        "env_data_dir": os.getenv("DATA_DIR", ""),
        "cpu_count": os.cpu_count() or 1,
    }
