"""
Struktur-Metriken (Aufgabe 4).

Berechnet für jeden Angriffsgraphen (nx.DiGraph aus validator.py):
  - Anzahl distinkter einfacher Pfade ENTRY → TARGET
  - Cut-Vertices / Chokepoints (Engstellen)
  - Durchschnittliche kürzeste Pfadlänge zu allen erreichbaren Knoten
  - Graph-Durchmesser (im erreichbaren Teilgraphen)
  - Knotengrad-Verteilung (In-/Out-Degree)

Diese Metriken erlauben die spätere Korrelation mit der Lerneffizienz
des RL-Agenten (Forschungsfrage der Bachelorarbeit).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import networkx as nx

from .inventory import ENTRY_NODE, TARGET_NODE


@dataclass
class TopologyMetrics:
    pattern: str
    node_count: int
    edge_count: int
    distinct_paths_to_target: int
    cut_vertices: List[str]
    avg_sp_from_entry: float     # Ø kürzeste Pfadlänge von Entry zu allen anderen
    sp_to_target: int            # Kürzester Pfad Entry → Target
    diameter: int                # Längster kürzester Pfad im erreichbaren Teilgraph
    in_degree: Dict[str, int] = field(default_factory=dict)
    out_degree: Dict[str, int] = field(default_factory=dict)

    def as_row(self) -> dict:
        return {
            "Muster":            self.pattern,
            "Knoten":            self.node_count,
            "Kanten":            self.edge_count,
            "Pfade→Ziel":        self.distinct_paths_to_target,
            "Chokepoints":       len(self.cut_vertices),
            "Chokepoint-Namen":  ", ".join(self.cut_vertices) or "-",
            "Ø-KP-Länge":        f"{self.avg_sp_from_entry:.2f}",
            "KP→Ziel":           self.sp_to_target,
            "Durchmesser":       self.diameter,
        }


def compute_metrics(G: nx.DiGraph, pattern: str) -> TopologyMetrics:
    """
    Berechnet Struktur-Metriken auf dem Angriffsgraphen G.
    Betrachtet nur den von ENTRY_NODE erreichbaren Teilgraphen.
    """
    reachable = nx.descendants(G, ENTRY_NODE) | {ENTRY_NODE}
    H = G.subgraph(reachable).copy()

    # ── Distinkte einfache Pfade Entry → Target ───────────────────────────────
    if TARGET_NODE in reachable:
        all_paths = list(nx.all_simple_paths(H, ENTRY_NODE, TARGET_NODE))
        n_paths = len(all_paths)
    else:
        n_paths = 0

    # ── Cut-Vertices (Chokepoints) ────────────────────────────────────────────
    # Ein Knoten v ist Chokepoint, wenn seine Entfernung den TARGET_NODE
    # vom ENTRY_NODE trennt (kein Pfad mehr Entry→Target ohne v).
    cut_vertices = []
    for node in list(H.nodes):
        if node in (ENTRY_NODE, TARGET_NODE):
            continue
        H_minus = H.copy()
        H_minus.remove_node(node)
        still_reachable = nx.descendants(H_minus, ENTRY_NODE) | {ENTRY_NODE}
        if TARGET_NODE not in still_reachable:
            cut_vertices.append(node)

    # ── Kürzeste Pfade von Entry ──────────────────────────────────────────────
    sp_lengths = nx.single_source_shortest_path_length(H, ENTRY_NODE)

    # Ø Pfadlänge zu allen erreichbaren Knoten außer Entry selbst
    other_lengths = [v for k, v in sp_lengths.items() if k != ENTRY_NODE]
    avg_sp = sum(other_lengths) / len(other_lengths) if other_lengths else 0.0

    sp_to_target = sp_lengths.get(TARGET_NODE, -1)

    # ── Graph-Durchmesser ─────────────────────────────────────────────────────
    # Längster kürzester Pfad im erreichbaren Teilgraphen (undirektiert).
    # Fallback: max der BFS-Distanzen falls der undirektierte Graph nicht
    # zusammenhängend ist.
    if len(H) > 1:
        try:
            diameter = nx.diameter(H.to_undirected())
        except nx.NetworkXError:
            diameter = max(sp_lengths.values()) if sp_lengths else 0
    else:
        diameter = 0

    return TopologyMetrics(
        pattern=pattern,
        node_count=len(H),
        edge_count=H.number_of_edges(),
        distinct_paths_to_target=n_paths,
        cut_vertices=sorted(cut_vertices),
        avg_sp_from_entry=avg_sp,
        sp_to_target=sp_to_target,
        diameter=diameter,
        in_degree=dict(H.in_degree()),
        out_degree=dict(H.out_degree()),
    )


def print_metric_table(metrics_list: List[TopologyMetrics]) -> None:
    """Gibt eine ausgerichtete Vergleichstabelle aller Topologie-Metriken aus."""
    if not metrics_list:
        print("Keine Metriken vorhanden.")
        return

    rows = [m.as_row() for m in metrics_list]
    cols = list(rows[0].keys())
    widths = {
        col: max(len(col), max(len(str(r[col])) for r in rows))
        for col in cols
    }

    header = " | ".join(col.ljust(widths[col]) for col in cols)
    sep    = "-+-".join("-" * widths[col] for col in cols)
    print(header)
    print(sep)
    for row in rows:
        print(" | ".join(str(row[col]).ljust(widths[col]) for col in cols))
