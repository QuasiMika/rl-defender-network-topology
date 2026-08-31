"""
CBS-kompatible Gym-Environments für alle Topologie-Muster.

Vier Vergleichsfälle (unabhängige Variable = Netzwerktopologie):
  flat             – keine Segmentierung, viele direkte Pfade
  hub_and_spoke    – DC als einziger Chokepoint / Hub
  dmz              – zonenbasierte Segmentierung (Internet | DMZ | Intranet)
  micro_segmented  – Zero-Trust, minimale Kommunikationspfade

Zwei neutrale Pretraining-Topologien (kein Vergleichsfall):
  defense_in_depth – hierarchischer Baum, alle 10 Nodes erreichbar (verworfen)
  chain            – strikt linearer Pfad über alle 10 Nodes (9 Hops)

Alle sechs Envs teilen identische EnvironmentBounds → identischer
Observation-Space → vergleichbare RL-Trainingsläufe.
"""

from __future__ import annotations

import gymnasium as gym
from gymnasium.envs.registration import registry

from cyberbattle._env.cyberbattle_env import (
    CyberBattleEnv,
    AttackerGoal,
    DefenderGoal,
    DefenderConstraint,
)

from .inventory import MAX_NODE_COUNT, MAX_TOTAL_CREDS, MAX_CREDS_PER_ACT
from .topology_generator import make_environment, PATTERNS

# ── Gemeinsame Bound-Parameter ────────────────────────────────────────────────
_BOUNDS = dict(
    maximum_node_count=MAX_NODE_COUNT,
    maximum_total_credentials=MAX_TOTAL_CREDS,
    maximum_discoverable_credentials_per_action=MAX_CREDS_PER_ACT,
)


class CyberBattleFlatTopology(CyberBattleEnv):
    """Keine Segmentierung – viele direkte Pfade, maximale Angriffsfläche."""

    def __init__(self, **kwargs):
        super().__init__(
            initial_environment=make_environment("flat"),
            **_BOUNDS,
            **kwargs,
        )

    @property
    def name(self) -> str:
        return "CyberBattleFlatTopology"


class CyberBattleHubSpokeTopology(CyberBattleEnv):
    """Hub-and-Spoke – DC als einziger Chokepoint, alle Spokes hängen am DC."""

    def __init__(self, **kwargs):
        super().__init__(
            initial_environment=make_environment("hub_and_spoke"),
            **_BOUNDS,
            **kwargs,
        )

    @property
    def name(self) -> str:
        return "CyberBattleHubSpokeTopology"


class CyberBattleDMZTopology(CyberBattleEnv):
    """DMZ – zonenbasierte Segmentierung (Internet-Edge | DMZ | Intranet)."""

    def __init__(self, **kwargs):
        super().__init__(
            initial_environment=make_environment("dmz"),
            **_BOUNDS,
            **kwargs,
        )

    @property
    def name(self) -> str:
        return "CyberBattleDMZTopology"


class CyberBattleMicroSegTopology(CyberBattleEnv):
    """Micro-segmented – Zero-Trust, nur explizit erlaubte Verbindungen."""

    def __init__(self, **kwargs):
        super().__init__(
            initial_environment=make_environment("micro_segmented"),
            **_BOUNDS,
            **kwargs,
        )

    @property
    def name(self) -> str:
        return "CyberBattleMicroSegTopology"


class CyberBattleDefenseInDepthTopology(CyberBattleEnv):
    """Defense-in-Depth – hierarchischer Baum, alle 10 Nodes erreichbar (Pretraining)."""

    def __init__(self, **kwargs):
        super().__init__(
            initial_environment=make_environment("defense_in_depth"),
            **_BOUNDS,
            **kwargs,
        )

    @property
    def name(self) -> str:
        return "CyberBattleDefenseInDepthTopology"


class CyberBattleChainTopology(CyberBattleEnv):
    """Chain – strikt linearer Pfad über alle 10 Nodes (Attacker-Pretraining)."""

    def __init__(self, **kwargs):
        super().__init__(
            initial_environment=make_environment("chain"),
            **_BOUNDS,
            **kwargs,
        )

    @property
    def name(self) -> str:
        return "CyberBattleChainTopology"


# ── Lookup-Tabellen ───────────────────────────────────────────────────────────
TOPOLOGY_CLASSES: dict[str, type[CyberBattleEnv]] = {
    "flat":             CyberBattleFlatTopology,
    "hub_and_spoke":    CyberBattleHubSpokeTopology,
    "dmz":              CyberBattleDMZTopology,
    "micro_segmented":  CyberBattleMicroSegTopology,
    "defense_in_depth": CyberBattleDefenseInDepthTopology,
    "chain":            CyberBattleChainTopology,
}

ENV_IDS: dict[str, str] = {
    "flat":             "CyberBattleFlat-thesis-v0",
    "hub_and_spoke":    "CyberBattleHubSpoke-thesis-v0",
    "dmz":              "CyberBattleDMZ-thesis-v0",
    "micro_segmented":  "CyberBattleMicroSeg-thesis-v0",
    "defense_in_depth": "CyberBattleDefenseInDepth-thesis-v0",
    "chain":            "CyberBattleChain-thesis-v0",
}

_ENTRY_POINTS: dict[str, str] = {
    "flat":             "thesis_topology.envs:CyberBattleFlatTopology",
    "hub_and_spoke":    "thesis_topology.envs:CyberBattleHubSpokeTopology",
    "dmz":              "thesis_topology.envs:CyberBattleDMZTopology",
    "micro_segmented":  "thesis_topology.envs:CyberBattleMicroSegTopology",
    "defense_in_depth": "thesis_topology.envs:CyberBattleDefenseInDepthTopology",
    "chain":            "thesis_topology.envs:CyberBattleChainTopology",
}


def register_all() -> None:
    """
    Registriert alle fünf Topologie-Envs bei gymnasium.
    Danach per gym.make(ENV_IDS["flat"]) nutzbar.
    """
    import cyberbattle  # noqa: F401  stellt sicher, dass CBS-Envs zuerst registriert sind
    for pattern, env_id in ENV_IDS.items():
        if env_id in registry:
            del registry[env_id]
        gym.register(id=env_id, entry_point=_ENTRY_POINTS[pattern])


def make_env(pattern: str, **kwargs) -> CyberBattleEnv:
    """
    Factory-Funktion: erzeugt direkt ein CyberBattleEnv ohne gym.make().
    Nützlich für MARLon-Wrapper (kein gym.register nötig).

    Parameters
    ----------
    pattern : str
        Eines von "flat", "hub_and_spoke", "dmz", "micro_segmented",
        "defense_in_depth", "chain".
    **kwargs
        Werden an den CyberBattleEnv-Konstruktor weitergereicht,
        z.B. attacker_goal, defender_goal, defender_constraint.
    """
    cls = TOPOLOGY_CLASSES.get(pattern)
    if cls is None:
        raise ValueError(
            f"Unbekanntes Muster '{pattern}'. Verfügbar: {PATTERNS}"
        )
    return cls(**kwargs)
