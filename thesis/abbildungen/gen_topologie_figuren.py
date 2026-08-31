#!/usr/bin/env python3
"""
Erzeugt die TikZ-Abbildungen der Topologien fuer Kapitel 2.

Die Abbildungen werden NICHT von Hand gepflegt, sondern aus den echten
Datenstrukturen in thesis_topology/ generiert. Aendert sich dort eine
Topologie, erzeugt ein erneuter Lauf automatisch die passende Abbildung.

Aufruf (aus dem Projektwurzelverzeichnis, conda-Env cybersim):
    python thesis/abbildungen/gen_topologie_figuren.py

Ausgabe: thesis/abbildungen/topologie_<muster>.tex  (je ein tikzpicture)

Dargestellt werden zwei getrennte Kantenarten, weil das Modell beides
bewusst entkoppelt (siehe BA-Notizen 11.2):
    durchgezogen  Erreichbarkeit  (ADJACENCY  -> Firewall-Regeln)
    gestrichelt   Credential-Leak (CREDENTIAL_MAP -> wer haelt wessen Zugangsdaten)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from thesis_topology.inventory import (  # noqa: E402
    NODE_NAMES, NODE_VALUES, NODE_ACCESS_PORT, ENTRY_NODE, TARGET_NODE,
    TOTAL_REWARD,
)
from thesis_topology.topology_generator import (  # noqa: E402
    ADJACENCY, CREDENTIAL_MAP, POSITIONS,
)

OUT_DIR = Path(__file__).resolve().parent

# Kurzlabel fuer die Knoten; die vollen Namen sind zu breit fuer die Boxen.
SHORT = {
    "WebServer": "WebServer",
    "Workstation1": "WS1",
    "Workstation2": "WS2",
    "Workstation3": "WS3",
    "MailServer": "MailServer",
    "FileServer": "FileServer",
    "AppServer": "AppServer",
    "BackupServer": "BackupServer",
    "DomainController": "DomainCtrl",
    "DatabaseServer": "DatenbankSrv",
}

# Muster, die als Abbildung gebraucht werden, mit Skalierung und Bogenrichtung.
FIGURES = {
    "flat":            dict(scale=1.00, mesh=True),
    "hub_and_spoke":   dict(scale=1.15, mesh=False),
    "dmz":             dict(scale=0.95, mesh=False),
    "micro_segmented": dict(scale=0.88, mesh=False),
    "chain":           dict(scale=1.00, mesh=False),
}

# Die Positionen aus thesis_topology sind fuer die interaktive Plotly-Ansicht
# gedacht. Fuer den Satz taugt die Kette dort nicht: 1,3 Einheiten Abstand bei
# 17 mm Knotenbreite ueberlappen. Deshalb hier ein Schlangenlayout aus zwei
# Reihen zu fuenf Knoten. Reihenfolge und Kanten bleiben unveraendert.
POSITION_OVERRIDE: dict[str, dict[str, tuple]] = {
    # Flat: Kreisanordnung. Im urspruenglichen Spread-Layout lag der
    # Domain-Controller in der Mitte, sodass Kanten durch Knoten hindurchliefen.
    # Auf dem Kreis verlaufen alle Kanten als Sehnen durch die freie Mitte.
    # Die Reihenfolge ist so gewaehlt, dass haeufige Credential-Paare
    # (Web->App, App->DB, Mail->DC, WS1->FS, FS->Backup) benachbart liegen.
    "flat": {
        "WebServer":        ( 0.00,  4.00),
        "AppServer":        ( 2.35,  3.24),
        "DatabaseServer":   ( 3.80,  1.24),
        "DomainController": ( 3.80, -1.24),
        "MailServer":       ( 2.35, -3.24),
        "Workstation3":     ( 0.00, -4.00),
        "Workstation2":     (-2.35, -3.24),
        "Workstation1":     (-3.80, -1.24),
        "FileServer":       (-3.80,  1.24),
        "BackupServer":     (-2.35,  3.24),
    },
    # Hub-and-Spoke: Die acht Spokes lagen auf Vielfachen von 45 Grad, wodurch
    # Workstation3 genau zwischen Einstiegsknoten und Hub stand. Jetzt um
    # 22,5 Grad gedreht, sodass die waagerechte Achse links frei bleibt und die
    # Kante Einstieg -> Hub keinen Knoten kreuzt.
    "hub_and_spoke": {
        "WebServer":        (-6.60,  0.00),
        "AppServer":        ( 0.00,  0.00),
        "Workstation1":     ( 1.22,  2.96),
        "Workstation2":     (-1.22,  2.96),
        "Workstation3":     (-2.96,  1.22),
        "MailServer":       ( 2.96,  1.22),
        "DatabaseServer":   ( 2.96, -1.22),
        "BackupServer":     ( 1.22, -2.96),
        "FileServer":       (-1.22, -2.96),
        "DomainController": (-2.96, -1.22),
    },
    # Micro-Segmented: Die sechs unerreichbaren Knoten standen zu eng und der
    # BackupServer sprang aus der Spalte heraus -- Beschriftungen ueberlappten.
    # Jetzt eine saubere Spalte mit 1,3 Einheiten Abstand (bei 7 mm Knotenhoehe
    # und Skalierung 0,88 rund 11 mm Luft).
    "micro_segmented": {
        "WebServer":        ( 0.00,  3.20),
        "AppServer":        ( 3.60,  3.20),
        "DomainController": ( 7.20,  4.60),
        "DatabaseServer":   ( 7.20,  1.80),
        "MailServer":       (11.10,  6.50),
        "Workstation1":     (11.10,  5.20),
        "Workstation2":     (11.10,  3.90),
        "Workstation3":     (11.10,  2.60),
        "FileServer":       (11.10,  1.30),
        "BackupServer":     (11.10,  0.00),
    },
    # DMZ: Der BackupServer stand als einziger Intranet-Knoten ausserhalb der
    # rechten Spalte, wodurch die Kante FileServer -> BackupServer unsauber
    # wirkte. Jetzt alle Intranet-Endpunkte in einer Spalte, BackupServer
    # unmittelbar unter dem FileServer.
    "dmz": {
        "WebServer":        ( 0.00,  3.10),
        "MailServer":       ( 3.60,  4.40),
        "AppServer":        ( 3.60,  1.80),
        "DomainController": ( 7.20,  4.40),
        "DatabaseServer":   ( 7.20,  1.80),
        "Workstation1":     (10.80,  6.00),
        "Workstation2":     (10.80,  4.60),
        "Workstation3":     (10.80,  3.20),
        "FileServer":       (10.80,  1.80),
        "BackupServer":     (10.80,  0.40),
    },
    "chain": {
        "WebServer":        (0.0, 1.6),
        "Workstation1":     (2.4, 1.6),
        "Workstation2":     (4.8, 1.6),
        "Workstation3":     (7.2, 1.6),
        "MailServer":       (9.6, 1.6),
        "FileServer":       (9.6, 0.0),
        "AppServer":        (7.2, 0.0),
        "BackupServer":     (4.8, 0.0),
        "DomainController": (2.4, 0.0),
        "DatabaseServer":   (0.0, 0.0),
    },
}


def node_style(node: str) -> str:
    if node == ENTRY_NODE:
        return "entrynode"
    if node == TARGET_NODE:
        return "cjnode"
    if node == "DomainController":
        return "dcnode"
    return "netnode"


def reachable_from_entry(adj: dict[str, list[str]]) -> set[str]:
    """Knoten, die der Angreifer ueber Netzpfade ueberhaupt erreichen kann."""
    seen = {ENTRY_NODE}
    stack = [ENTRY_NODE]
    while stack:
        cur = stack.pop()
        for nb in adj.get(cur, []):
            if nb not in seen:
                seen.add(nb)
                stack.append(nb)
    return seen


def emit(pattern: str, cfg: dict) -> str:
    adj = ADJACENCY[pattern]
    creds = CREDENTIAL_MAP.get(pattern, adj)
    pos = POSITION_OVERRIDE.get(pattern, POSITIONS[pattern])
    reach = reachable_from_entry(adj)

    L: list[str] = []
    L.append("% AUTOMATISCH ERZEUGT von gen_topologie_figuren.py -- nicht von Hand aendern.")
    # max width statt festem \resizebox: schrumpft nur, wenn noetig, und blaeht
    # schmale Abbildungen nicht auf.
    L.append("\\begin{adjustbox}{max width=\\textwidth}")
    L.append(f"\\begin{{tikzpicture}}[topofig, scale={cfg['scale']}]")

    # ── Knoten ────────────────────────────────────────────────────────
    for n in NODE_NAMES:
        x, y = pos[n]
        style = node_style(n)
        if n not in reach:
            style += ",isolated"
        port = NODE_ACCESS_PORT.get(n, "--")
        val = NODE_VALUES[n]
        label = f"{SHORT[n]}\\\\[-1pt]{{\\tiny {val}\\,P \\textbar\\ {port}}}"
        L.append(f"  \\node[{style}] ({n}) at ({x},{y}) {{{label}}};")

    # ── Erreichbarkeitskanten ─────────────────────────────────────────
    if cfg["mesh"]:
        L.append("  % Vollstaendiger Graph: alle Kanten wuerden die Abbildung unlesbar")
        L.append("  % machen; stattdessen Hinweis in der Legende.")
    else:
        drawn = set()
        for src, dsts in adj.items():
            for dst in dsts:
                if (dst, src) in drawn:
                    continue          # Gegenrichtung schon gezeichnet
                drawn.add((src, dst))
                L.append(f"  \\draw[reach] ({src}) -- ({dst});")

    # ── Credential-Kanten ─────────────────────────────────────────────
    # Der DomainController haelt in jeder Topologie ALLE Credentials.
    # Acht zusaetzliche Pfeile waeren nur Rauschen, daher als Badge.
    dc_holds_all = set(creds.get("DomainController", [])) >= {
        n for n in NODE_NAMES if n not in ("DomainController", ENTRY_NODE)
    }
    for src, dsts in creds.items():
        if src == "DomainController" and dc_holds_all:
            continue
        for dst in dsts:
            L.append(f"  \\draw[cred] ({src}) to[bend right=14] ({dst});")

    if dc_holds_all:
        x, y = pos["DomainController"]
        L.append(
            f"  \\node[dcbadge, anchor=north] at ({x},{y - 0.62}) "
            f"{{h\\\"alt alle Zugangsdaten}};"
        )

    L.append("\\end{tikzpicture}")
    L.append("\\end{adjustbox}")
    L.append("")
    return "\n".join(L)


def main() -> None:
    for pattern, cfg in FIGURES.items():
        out = OUT_DIR / f"topologie_{pattern}.tex"
        out.write_text(emit(pattern, cfg), encoding="utf-8")
        adj = ADJACENCY[pattern]
        creds = CREDENTIAL_MAP.get(pattern, adj)
        n_reach = len(reachable_from_entry(adj))
        erreichbar = sum(NODE_VALUES[n] for n in reachable_from_entry(adj))
        print(
            f"{pattern:<16} -> {out.name:<32} "
            f"erreichbare Knoten: {n_reach:>2}/10, "
            f"erreichbarer Reward: {erreichbar:>3}/{TOTAL_REWARD}"
        )


if __name__ == "__main__":
    main()
