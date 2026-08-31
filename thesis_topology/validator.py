"""
Erreichbarkeits-Validator.

MODELL (wichtig, hier lag der alte Validator falsch):
Eine Uebernahme von Knoten B braucht ZWEI voneinander unabhaengige Dinge:

  1. Netzpfad   – irgendein bereits uebernommener Knoten A darf B ueber
                  dessen Zugangsport erreichen (Firewall outgoing bei A,
                  incoming bei B).
  2. Credential – irgendein bereits uebernommener Knoten C haelt B's
                  Zugangsdaten.

A und C duerfen VERSCHIEDENE Knoten sein. Genau das war der Kern des
Topologie-Redesigns: Erreichbarkeit und Credential-Besitz sind entkoppelt
(siehe topology_generator.ADJACENCY vs. CREDENTIAL_MAP).

Der frueherere Validator baute einen Angriffsgraphen mit Kanten A→B und
verlangte damit implizit A == C. Er meldete deshalb micro_segmented als
kaputt ("DatabaseServer nicht erreichbar"), obwohl der Angreifer die
Datenbank in den Messlaeufen in 100 % der Episoden uebernahm: Er kombiniert
die Reichweite des AppServers mit den Zugangsdaten vom DomainController.

Statt eines Graphen wird deshalb eine Fixpunkt-Iteration ueber die Menge der
uebernehmbaren Knoten gerechnet.
"""

from __future__ import annotations

from typing import Dict, Set, Tuple

from cyberbattle.simulation import model as m

from .inventory import ENTRY_NODE


def _firewall_allows(node_info: m.NodeInfo, port: str, direction: str) -> bool:
    """
    True, wenn die Firewall des Knotens den Port in der angegebenen Richtung
    explizit ALLOW enthält.

    CBS-Semantik: erste passende Regel gewinnt; nicht aufgelistet = BLOCKED.
    """
    rules = (
        node_info.firewall.incoming if direction == "incoming"
        else node_info.firewall.outgoing
    )
    for rule in rules:
        if rule.port == port:
            return rule.permission == m.RulePermission.ALLOW
    return False  # default: BLOCK


def _leaked_credentials(node_info: m.NodeInfo) -> Set[Tuple[str, str, str]]:
    """Alle (Zielknoten, Port, Credential)-Tripel, die dieser Knoten preisgibt."""
    out: Set[Tuple[str, str, str]] = set()
    for vuln in node_info.vulnerabilities.values():
        if vuln.type != m.VulnerabilityType.LOCAL:
            continue
        if not isinstance(vuln.outcome, m.LeakedCredentials):
            continue
        for cc in vuln.outcome.credentials:
            out.add((cc.node, cc.port, cc.credential))
    return out


def compromisable_nodes(environment: m.Environment) -> Dict[str, int]:
    """
    Menge der vom Einstiegsknoten aus uebernehmbaren Knoten, mit Hop-Distanz.

    Returns
    -------
    dict NodeID -> Anzahl Hops ab ENTRY_NODE (Einstieg selbst = 0).
    """
    nodes = dict(environment.nodes())
    owned: Dict[str, int] = {ENTRY_NODE: 0}

    changed = True
    while changed:
        changed = False
        for tgt_id, tgt_info in nodes.items():
            if tgt_id in owned:
                continue

            # (2) Haelt ein uebernommener Knoten die Zugangsdaten fuer tgt?
            key_holders = []
            for src_id in owned:
                for node, port, cred in _leaked_credentials(nodes[src_id]):
                    if node != tgt_id:
                        continue
                    accepted = any(
                        svc.name == port and cred in svc.allowedCredentials
                        for svc in tgt_info.services
                    )
                    if accepted and _firewall_allows(tgt_info, port, "incoming"):
                        key_holders.append((src_id, port))
            if not key_holders:
                continue

            # (1) Erreicht ein uebernommener Knoten tgt ueber diesen Port?
            reachers = [
                src_id for src_id in owned
                for _, port in key_holders
                if _firewall_allows(nodes[src_id], port, "outgoing")
            ]
            if not reachers:
                continue

            owned[tgt_id] = 1 + max(
                min(owned[s] for s in reachers),
                min(owned[s] for s, _ in key_holders),
            )
            changed = True

    return owned


def validate_reachability(
    environment: m.Environment,
    required: Tuple[str, ...],
    pattern_name: str = "",
) -> Dict[str, int]:
    """
    Prueft, dass alle Knoten aus *required* uebernehmbar sind.

    Bewusst NICHT "alle Knoten erreichbar": Bei micro_segmented sind sechs
    Knoten strukturell unerreichbar, und das ist der beabsichtigte Zustand.

    Returns die Hop-Distanzen; wirft RuntimeError bei Verletzung.
    """
    owned = compromisable_nodes(environment)
    fehlend = [n for n in required if n not in owned]
    if fehlend:
        alle = sorted(dict(environment.nodes()))
        raise RuntimeError(
            f"\n{'=' * 60}\n"
            f"VALIDIERUNG FEHLGESCHLAGEN für Topologie '{pattern_name}':\n"
            f"  Nicht übernehmbar: {fehlend}\n"
            f"  Übernehmbar:       {sorted(owned)}\n"
            f"  Alle Knoten:       {alle}\n"
            f"{'=' * 60}"
        )
    return owned
