#!/usr/bin/env python3
"""Angreifer-Reward und Crown-Jewel-Quote im Trainingsverlauf.

Zeigt fuer ein Matchup, dass der Rueckgang des Angreifer-Rewards mit dem
Einbruch der Crown-Jewel-Quote zusammenfaellt. Erzeugt wird der Fall aus
Kapitel 4, dmz gegen dmz.

  oben   Angreifer-Reward, Mittel ueber die Seeds, gleitendes Mittel ueber
         fuenf Episoden.
  unten  Anteil der Episoden mit erreichtem Crown Jewel. Gebildet ueber ein
         gleitendes Fenster von elf Episoden und alle fuenf Seeds, also ueber
         55 Episoden je Punkt; ein Punktwert aus nur fuenf Episoden waere zu
         grob, er koennte nur Vielfache von 0,2 annehmen.

Aufruf:
    python3 gen_cj.py <experiment-dir> [ausgabe-ordner]
"""
import csv
import os
import statistics
import sys
from collections import defaultdict

# Die LETZTE Episode jedes Laufs wird verworfen. Sie bricht ab, sobald das
# Schrittbudget erschoepft ist, umfasst also nur einen Bruchteil der 2000
# Schritte, und ihre Aktionsstatistik wird nicht mehr vollstaendig
# fortgeschrieben -- atk_max_owned steht dort durchgaengig auf 0. Ohne diese
# Bereinigung faellt jede Kurve am rechten Rand kuenstlich ab.

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

MATCHUP = ("dmz", "dmz")
DIAGONALE = [("flat", "flat"), ("hub_and_spoke", "hub_and_spoke"),
             ("dmz", "dmz"), ("micro_segmented", "micro_segmented")]
TITEL = {"flat": "flat", "hub_and_spoke": "hub_and_spoke", "dmz": "dmz",
         "micro_segmented": "micro_segmented"}
TOPO_FARBEN = {"flat": "#C4342B", "hub_and_spoke": "#1F5FA9",
               "dmz": "#E08A1E", "micro_segmented": "#00857F"}
FENSTER_REWARD = 5
FENSTER_CJ = 11

ANGREIFER_FARBE = "#C4342B"
CJ_FARBE = "#1F5FA9"
GRID = "#D8D8D8"
TEXT = "#1A1A1A"
MUTED = "#5A5A5A"


def stil():
    plt.rcParams.update({
        "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.facecolor": "white", "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
        "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
        "axes.edgecolor": MUTED, "axes.labelcolor": TEXT, "text.color": TEXT,
        "xtick.color": MUTED, "ytick.color": MUTED,
        "xtick.labelsize": 8, "ytick.labelsize": 8,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
        "legend.frameon": False, "savefig.bbox": "tight",
    })


def glaetten(werte, fenster):
    h = fenster // 2
    return [statistics.mean(werte[max(0, i - h):min(len(werte), i + h + 1)])
            for i in range(len(werte))]


def lade(pfad):
    """(topologie, angreifer) -> (Reward je Seed, CJ-Marker je Seed)."""
    reward = defaultdict(lambda: defaultdict(list))
    cj = defaultdict(lambda: defaultdict(list))
    owned = defaultdict(lambda: defaultdict(list))
    with open(pfad, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["phase"] != "defender_matrix" or r["agent"] != "attacker":
                continue
            if not r["episode_reward"]:
                continue
            schluessel = (r["topology"], r["attacker_name"])
            reward[schluessel][r["run_id"]].append(
                (int(r["episode"]), float(r["episode_reward"])))
            cj[schluessel][r["run_id"]].append(
                (int(r["episode"]), float(r["atk_cj_reached"] or 0)))
            owned[schluessel][r["run_id"]].append(
                (int(r["episode"]), float(r["atk_max_owned"] or 0)))
    daten = {}
    for schluessel in reward:
        daten[schluessel] = (
            [[w for _, w in sorted(reward[schluessel][rid])][:-1]
             for rid in sorted(reward[schluessel])],
            [[w for _, w in sorted(cj[schluessel][rid])][:-1]
             for rid in sorted(cj[schluessel])],
            [[w for _, w in sorted(owned[schluessel][rid])][:-1]
             for rid in sorted(owned[schluessel])])
    return daten


def mittel(seeds):
    laenge = max(len(s) for s in seeds)
    return [statistics.mean([s[i] for s in seeds if i < len(s)])
            for i in range(laenge)]


def cj_quote(seeds):
    """Anteil erreichter Crown Jewels ueber ein Fenster und alle Seeds."""
    laenge = max(len(s) for s in seeds)
    h = FENSTER_CJ // 2
    quote = []
    for i in range(laenge):
        werte = [s[j] for s in seeds
                 for j in range(max(0, i - h), min(len(s), i + h + 1))]
        quote.append(100.0 * statistics.mean(werte) if werte else 0.0)
    return quote


def knoten_diagonale(daten, ziel):
    """Gehaltene Knoten der vier Selbst-Matchups in einer Abbildung."""
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    grenzen = []
    for schluessel in DIAGONALE:
        seeds = daten[schluessel][2]
        laenge = max(len(s) for s in seeds)
        kurve = [statistics.mean([s[i] for s in seeds if i < len(s)])
                 for i in range(laenge)]
        ax.plot(range(1, laenge + 1), glaetten(kurve, FENSTER_REWARD),
                linewidth=1.5, color=TOPO_FARBEN[schluessel[0]],
                label=TITEL[schluessel[0]])
        grenzen.append(min(len(s) for s in seeds))
    # zorder ueber dem Gitter, sonst faellt die Marke mit einer
    # Gitterlinie zusammen und ist nicht mehr zu erkennen.
    ax.axvline(min(grenzen), color=TEXT, linewidth=1.0,
               linestyle=(0, (3, 3)), zorder=3,
               label="ab hier weniger als fünf Läufe")
    ax.set_ylim(0, 10.5)
    ax.set_xlabel("Episode")
    ax.set_ylabel("gehaltene Knoten")
    for rand in ("top", "right"):
        ax.spines[rand].set_visible(False)
    griffe, namen = ax.get_legend_handles_labels()
    fig.tight_layout(rect=(0, 0.10, 1, 1))
    fig.legend(griffe, namen, loc="lower center", ncol=3, fontsize=9,
               bbox_to_anchor=(0.5, 0.0))
    fig.savefig(os.path.join(ziel, "knoten_verlauf_diagonale.pdf"))
    plt.close(fig)


def diagonale(daten, ziel):
    """Crown-Jewel-Quote der vier Selbst-Matchups in einer Abbildung."""
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    grenzen = []
    for schluessel in DIAGONALE:
        cj_seeds = daten[schluessel][1]
        q = cj_quote(cj_seeds)
        ax.plot(range(1, len(q) + 1), q, linewidth=1.5,
                color=TOPO_FARBEN[schluessel[0]], label=TITEL[schluessel[0]])
        grenzen.append(min(len(s) for s in cj_seeds))
    # Ab der kuerzesten Reihe beruhen einzelne Kurven auf weniger Laeufen.
    # zorder ueber dem Gitter, sonst faellt die Marke mit einer
    # Gitterlinie zusammen und ist nicht mehr zu erkennen.
    ax.axvline(min(grenzen), color=TEXT, linewidth=1.0,
               linestyle=(0, (3, 3)), zorder=3,
               label="ab hier weniger als fünf Läufe")
    ax.set_xlim(1, max(len(cj_quote(daten[s][1])) for s in DIAGONALE))
    ax.set_ylim(0, 105)
    ax.set_xlabel("Episode")
    ax.set_ylabel("Crown Jewel erreicht [%]")
    for rand in ("top", "right"):
        ax.spines[rand].set_visible(False)
    griffe, namen = ax.get_legend_handles_labels()
    fig.tight_layout(rect=(0, 0.10, 1, 1))
    fig.legend(griffe, namen, loc="lower center", ncol=3, fontsize=9,
               bbox_to_anchor=(0.5, 0.0))
    fig.savefig(os.path.join(ziel, "cj_verlauf_diagonale.pdf"))
    plt.close(fig)


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Nutzung: gen_cj.py <experiment-dir> [ausgabe]")
    quelle = os.path.join(sys.argv[1], "combined_episodes.csv")
    ziel = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(
        os.path.abspath(__file__))
    stil()
    daten = lade(quelle)
    diagonale(daten, ziel)
    knoten_diagonale(daten, ziel)
    reward_seeds, cj_seeds, _ = daten[MATCHUP]

    fig, (oben, unten) = plt.subplots(2, 1, figsize=(7.2, 3.8), sharex=True)
    r = glaetten(mittel(reward_seeds), FENSTER_REWARD)
    oben.plot(range(1, len(r) + 1), r, color=ANGREIFER_FARBE, linewidth=1.5)
    oben.axhline(0, color=MUTED, linewidth=0.8, zorder=1)
    oben.set_ylabel("Angreifer-Reward")

    q = cj_quote(cj_seeds)
    unten.plot(range(1, len(q) + 1), q, color=CJ_FARBE, linewidth=1.5)
    unten.set_ylabel("Crown Jewel erreicht [\\%]".replace("\\", ""))
    unten.set_ylim(0, 105)
    unten.set_xlabel("Episode")

    # Wie in den Lernkurven: markieren, ab wo nicht mehr alle Seeds beitragen.
    grenze = min(len(s) for s in reward_seeds)
    for ax in (oben, unten):
        ax.set_xlim(1, len(r))
        if grenze < len(r):
            ax.axvline(grenze, color=TEXT, linewidth=1.0,
                       linestyle=(0, (3, 3)), zorder=3,
                       label="ab hier weniger als fünf Läufe")
        for rand in ("top", "right"):
            ax.spines[rand].set_visible(False)
    griffe, namen = oben.get_legend_handles_labels()
    if griffe:
        fig.legend(griffe, namen, loc="lower center", fontsize=9,
                   bbox_to_anchor=(0.5, -0.02))

    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(os.path.join(ziel, "cj_verlauf_dmz.pdf"))
    plt.close(fig)

    # Kontrollausgabe fuer den Text
    for e in (1, 25, 50, 75, 100, 110, 120, 150, 200, 250):
        if e <= len(q):
            print("Episode %3d  Reward %7.0f  CJ %5.1f %%" % (e, r[e - 1], q[e - 1]))


if __name__ == "__main__":
    main()
