#!/usr/bin/env python3
"""Verteidiger-Reward und SLA-Brueche je Seed fuer die auffaelligen Matchups.

Zweck: zeigen, dass die Einbrueche der Mittelkurven aus gen_lernkurven.py
genau dort liegen, wo einzelne Laeufe die Verfuegbarkeitsschwelle reissen.
Deshalb bewusst NICHT ueber die Seeds gemittelt -- das Mittel verwischt gerade
den Befund, dass jeweils nur ein oder zwei Laeufe betroffen sind.

  oben   Verteidiger-Reward je Seed, gleitendes Mittel ueber fuenf Episoden.
  unten  Schritte je Episode, in denen die Verfuegbarkeit unter der Schwelle
         lag, ungeglaettet.

Aufruf:
    python3 gen_sla.py <experiment-dir> [ausgabe-ordner]
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

# Die beiden in Kapitel 4 besprochenen Faelle.
MATCHUPS = [("hub_and_spoke", "hub_and_spoke"),
            ("hub_and_spoke", "micro_segmented")]
TITEL = {"hub_and_spoke": "hub_and_spoke", "micro_segmented": "micro_segmented"}

SEED_FARBEN = ["#1F5FA9", "#C4342B", "#00857F", "#E08A1E", "#6B3FA0"]
GRID = "#D8D8D8"
TEXT = "#1A1A1A"
MUTED = "#5A5A5A"
FENSTER = 5


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


def glaetten(werte, fenster=FENSTER):
    h = fenster // 2
    return [statistics.mean(werte[max(0, i - h):min(len(werte), i + h + 1)])
            for i in range(len(werte))]


def lade(pfad):
    """(topologie, angreifer) -> Liste je Seed von (rewards, bruchschritte)."""
    roh = defaultdict(lambda: defaultdict(list))
    with open(pfad, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["phase"] != "defender_matrix" or r["agent"] != "defender":
                continue
            if not r["episode_reward"]:
                continue
            roh[(r["topology"], r["attacker_name"])][r["run_id"]].append(
                (int(r["episode"]), float(r["episode_reward"]),
                 float(r["def_sla_break_steps"] or 0)))
    daten = {}
    for schluessel, laeufe in roh.items():
        seeds = []
        for reihe in laeufe.values():
            reihe.sort()
            seeds.append(([w for _, w, _ in reihe][:-1],
                          [b for _, _, b in reihe][:-1]))
        daten[schluessel] = seeds
    return daten


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Nutzung: gen_sla.py <experiment-dir> [ausgabe]")
    quelle = os.path.join(sys.argv[1], "combined_episodes.csv")
    ziel = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(
        os.path.abspath(__file__))
    stil()
    daten = lade(quelle)

    fig, achsen = plt.subplots(2, 2, figsize=(7.2, 4.6), sharex="col")
    for spalte, schluessel in enumerate(MATCHUPS):
        seeds = daten[schluessel]
        oben, unten = achsen[0][spalte], achsen[1][spalte]
        for i, (rewards, brueche) in enumerate(seeds):
            farbe = SEED_FARBEN[i % len(SEED_FARBEN)]
            x = range(1, len(rewards) + 1)
            oben.plot(x, glaetten(rewards), color=farbe, linewidth=1.2,
                      label="Seed %d" % (i + 1))
            unten.plot(x, brueche, color=farbe, linewidth=1.0)
        oben.set_title("%s gegen %s" % (TITEL[schluessel[0]],
                                        TITEL[schluessel[1]]),
                       loc="left", fontweight="bold")
        oben.axhline(0, color=MUTED, linewidth=0.8, zorder=1)
        unten.set_xlabel("Episode")
        for ax in (oben, unten):
            for rand in ("top", "right"):
                ax.spines[rand].set_visible(False)
    achsen[0][0].set_ylabel("Verteidiger-Reward")
    achsen[1][0].set_ylabel("Schritte mit SLA-Bruch")

    griffe, namen = achsen[0][0].get_legend_handles_labels()
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.legend(griffe, namen, loc="lower center", ncol=5, fontsize=9,
               bbox_to_anchor=(0.5, 0.0))
    fig.savefig(os.path.join(ziel, "sla_einbrueche.pdf"))
    plt.close(fig)
    print("geschrieben nach", ziel)


if __name__ == "__main__":
    main()
