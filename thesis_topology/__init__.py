"""
thesis_topology – Topologie-Generator für CyberBattleSim (Bachelorarbeit).

Schnellstart:
    from thesis_topology.envs import make_env
    env = make_env("chain")           # oder "star", "tree", "mesh"
    obs, _ = env.reset()
"""

from .envs import make_env, TOPOLOGY_CLASSES, ENV_IDS, register_all
from .topology_generator import make_environment, PATTERNS
from .validator import validate_reachability, compromisable_nodes
from .metrics import compute_metrics, print_metric_table
from .inventory import (
    NODE_COUNT, NODE_NAMES, NODE_VALUES, TOTAL_REWARD,
    ENTRY_NODE, TARGET_NODE, ENV_IDENTIFIERS,
)

__all__ = [
    "make_env", "make_environment", "register_all",
    "TOPOLOGY_CLASSES", "ENV_IDS", "PATTERNS",
    "validate_reachability", "compromisable_nodes",
    "compute_metrics", "print_metric_table",
    "NODE_COUNT", "NODE_NAMES", "NODE_VALUES", "TOTAL_REWARD",
    "ENTRY_NODE", "TARGET_NODE", "ENV_IDENTIFIERS",
]
