"""
Invarianten-Test fuer die Topologien.

Zusammengefasst aus den frueheren Einzeltests (13.08.2026). Geprueft werden
genau die Eigenschaften, die ueber alle Topologien hinweg gelten MUESSEN,
damit die Topologie die einzige manipulierte Groesse bleibt:

  1. Inventar   – jede Topologie enthaelt exakt dieselben zehn Knoten.
  2. Punktesumme – die Summe aller Knotenwerte ist ueberall 235. Das gilt
                   unabhaengig davon, ob der Angreifer sie erreichen kann;
                   genau diese Trennung ist der Untersuchungsgegenstand.
  3. Kernknoten – DatabaseServer (Crown Jewel) und DomainController sind in
                  jeder Topologie uebernehmbar. Sonst waere die Topologie
                  entweder unspielbar oder der Vergleich sinnlos.
  4. Lauffaehig – reset() und 20 step()-Aufrufe ohne Exception.

BEWUSST NICHT GEPRUEFT: dass alle zehn Knoten erreichbar sind. Bei
micro_segmented sind sechs davon strukturell unerreichbar (145 von 235
erreichbaren Punkten), und das ist der beabsichtigte Zustand. Der frueherere
test_reward_invariant hat genau das verlangt und widersprach damit dem
eigenen Design.

Aufruf:
    python -m pytest thesis_topology/test_smoke.py -v
"""

import numpy as np
import pytest

from cyberbattle._env.cyberbattle_env import AttackerGoal, DefenderGoal

from thesis_topology.topology_generator import PATTERNS, make_environment
from thesis_topology.validator import validate_reachability
from thesis_topology.envs import TOPOLOGY_CLASSES
from thesis_topology.inventory import (
    NODE_NAMES, NODE_VALUES, TOTAL_REWARD, TARGET_NODE,
)

# Knoten, die in JEDER Topologie uebernehmbar sein muessen.
PFLICHTKNOTEN = (TARGET_NODE, "DomainController")


@pytest.mark.parametrize("pattern", PATTERNS)
def test_inventar_identisch(pattern: str) -> None:
    """Jede Topologie enthaelt exakt dieselben zehn Knoten."""
    env = make_environment(pattern)
    vorhanden = sorted(dict(env.nodes()))
    assert vorhanden == sorted(NODE_NAMES), (
        f"[{pattern}] Knoteninventar weicht ab.\n"
        f"  erwartet: {sorted(NODE_NAMES)}\n"
        f"  gefunden: {vorhanden}"
    )


@pytest.mark.parametrize("pattern", PATTERNS)
def test_punktesumme_identisch(pattern: str) -> None:
    """
    Die im Netz vorhandene Punktesumme ist ueberall gleich.

    Nicht die *erreichbare* Summe: Wie viel davon der Angreifer holen kann,
    ist gerade der Effekt der Topologie und darf sich unterscheiden.
    """
    env = make_environment(pattern)
    summe = sum(NODE_VALUES[n] for n in dict(env.nodes()))
    assert summe == TOTAL_REWARD, (
        f"[{pattern}] Punktesumme {summe} != {TOTAL_REWARD}."
    )


@pytest.mark.parametrize("pattern", PATTERNS)
def test_kernknoten_uebernehmbar(pattern: str) -> None:
    """Crown Jewel und Domain-Controller muessen ueberall erreichbar sein."""
    env = make_environment(pattern)
    hops = validate_reachability(env, required=PFLICHTKNOTEN, pattern_name=pattern)
    assert hops[TARGET_NODE] >= 1, "Crown Jewel darf nicht der Einstiegsknoten sein"


@pytest.mark.parametrize("pattern", PATTERNS)
def test_env_laeuft(pattern: str) -> None:
    """Env muss reset und 20 step()-Aufrufe ohne Exception ueberstehen."""
    cls = TOPOLOGY_CLASSES[pattern]
    env = cls(
        attacker_goal=AttackerGoal(own_atleast_percent=1.0),
        defender_goal=DefenderGoal(eviction=True),
    )
    env.reset()
    for _ in range(20):
        action = env.sample_valid_action()
        env.step(action)
    env.close()
