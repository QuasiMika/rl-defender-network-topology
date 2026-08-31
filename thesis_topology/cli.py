#!/usr/bin/env python3
"""
CLI (Aufgabe 5): Alle Topologien erzeugen, validieren, Metrik-Tabelle ausgeben.

Aufruf:
    python -m thesis_topology.cli
    python -m thesis_topology.cli --pattern chain star
    python -m thesis_topology.cli --dot          # DOT-Dateien exportieren
"""

import argparse
import sys

from .inventory import TOTAL_REWARD, NODE_VALUES
from .topology_generator import make_environment, PATTERNS
from .validator import validate_reachability
from .metrics import compute_metrics, print_metric_table

import networkx as nx


def _check_reward_invariant(G: nx.DiGraph, pattern: str) -> None:
    """
    Stellt sicher, dass der erreichbare Gesamt-Reward über alle Topologien
    identisch ist. Das ist die wichtigste Kontrolle der unabhängigen Variable:
    Nur die Topologie variiert, nicht der erreichbare Reward.
    """
    from .inventory import ENTRY_NODE
    reachable = nx.descendants(G, ENTRY_NODE) | {ENTRY_NODE}
    reachable_reward = sum(NODE_VALUES.get(n, 0) for n in reachable)
    if reachable_reward != TOTAL_REWARD:
        raise RuntimeError(
            f"[{pattern}] Reward-Invariante verletzt! "
            f"Erreichbar: {reachable_reward}, Erwartet: {TOTAL_REWARD}. "
            f"Unerreichbare Knoten: {sorted(set(G.nodes) - reachable)}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Thesis-Topologien erzeugen, validieren und Metriken ausgeben.\n"
            "Alle Topologien teilen dasselbe Knoten-Inventar (Nodes, Werte,\n"
            "Vulnerabilities). Nur Firewall und Credential-Leaks variieren."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--pattern", nargs="+", choices=PATTERNS, default=PATTERNS,
        metavar="PATTERN",
        help=f"Zu verarbeitende Muster (default: alle). Wählbar: {PATTERNS}",
    )
    parser.add_argument(
        "--dot", action="store_true",
        help="Angriffsgraphen als DOT-Dateien exportieren (benötigt pygraphviz)",
    )
    args = parser.parse_args()

    all_metrics = []

    for pattern in args.pattern:
        print(f"\n[{pattern.upper()}] Erzeuge Environment ...", flush=True)
        env = make_environment(pattern)

        print(f"[{pattern.upper()}] Validiere Erreichbarkeit ...", flush=True)
        try:
            G = validate_reachability(env, pattern_name=pattern)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            sys.exit(1)

        print(f"[{pattern.upper()}] OK – Zielknoten erreichbar.", flush=True)

        print(f"[{pattern.upper()}] Prüfe Reward-Invariante ...", flush=True)
        try:
            _check_reward_invariant(G, pattern)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            sys.exit(1)
        print(f"[{pattern.upper()}] Reward-Invariante OK "
              f"(Gesamt-Reward = {TOTAL_REWARD}).", flush=True)

        metrics = compute_metrics(G, pattern)
        all_metrics.append(metrics)

        # Knotengrad-Verteilung ausgeben
        print(f"[{pattern.upper()}] Knotengrad-Verteilung:")
        for node in sorted(G.nodes):
            print(f"    {node:20s}  in={metrics.in_degree.get(node,0)}"
                  f"  out={metrics.out_degree.get(node,0)}")

        if args.dot:
            try:
                dot_path = f"attack_graph_{pattern}.dot"
                nx.drawing.nx_agraph.write_dot(G, dot_path)
                print(f"[{pattern.upper()}] DOT geschrieben: {dot_path}")
            except ImportError:
                print(f"[{pattern.upper()}] WARNUNG: pygraphviz nicht "
                      f"installiert, DOT-Export übersprungen.")

    print("\n" + "=" * 80)
    print("TOPOLOGIE-VERGLEICHSTABELLE")
    print("=" * 80)
    print_metric_table(all_metrics)
    print()


if __name__ == "__main__":
    main()
