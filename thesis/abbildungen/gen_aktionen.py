#!/usr/bin/env python3
"""Aktionsverhalten des Verteidigers im Trainingsverlauf.

  aktionen_verlauf.pdf   Zwei Felder nebeneinander: Reimages je Episode und
                         Sperren je Episode, je verteidigter Topologie eine
                         Kurve. Gemittelt ueber die sechs Angreifer und fuenf
                         Seeds.
  abwehrbonus_verlauf.pdf  Abwehrbonus je Episode, ebenso je Topologie eine
                         Kurve. Der Bonus ist die Summe der Kantenbilanz-
                         Beitraege einer Episode und kann negativ werden.

Die LETZTE Episode jedes Laufs wird verworfen: Sie bricht ab, sobald das
Schrittbudget erschoepft ist, und ist deshalb nicht vergleichbar.

Aufruf:
    python3 gen_aktionen.py <experiment-dir> [ausgabe-ordner]
"""
import csv
import os
import statistics
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TOPOS = ["flat", "hub_and_spoke", "dmz", "micro_segmented"]
TITEL = {"flat": "flat", "hub_and_spoke": "hub_and_spoke", "dmz": "dmz",
         "micro_segmented": "micro_segmented"}
FARBEN = {"flat": "#C4342B", "hub_and_spoke": "#1F5FA9",
          "dmz": "#E08A1E", "micro_segmented": "#00857F"}
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


def glaetten(w, f=FENSTER):
    h = f // 2
    return [statistics.mean(w[max(0, i - h):min(len(w), i + h + 1)])
            for i in range(len(w))]


def lade(pfad):
    """topologie -> Feld -> Liste je Lauf (alle sechs Angreifer, fuenf Seeds)."""
    roh = defaultdict(lambda: defaultdict(list))
    with open(pfad, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["phase"] != "defender_matrix" or r["agent"] != "defender":
                continue
            if not r["episode_reward"]:
                continue
            roh[r["topology"]][r["run_id"]].append((
                int(r["episode"]),
                float(r["def_reimage"] or 0),
                float(r["def_block"] or 0),
                float(r["def_abwehr_reward"] or 0)))
    daten = {}
    for topo, laeufe in roh.items():
        daten[topo] = [sorted(v)[:-1] for v in laeufe.values()]
    return daten


def kurve(laeufe, spalte):
    """Mittel ueber die 30 Laeufe einer Topologie, gekuerzt auf den kuerzesten.

    Anders als bei den Kurven eines einzelnen Matchups wird hier gekuerzt: Das
    Mittel laeuft ueber 30 Laeufe aus sechs verschiedenen Matchups, und jenseits
    des kuerzesten Laufs beruht es nur noch auf denjenigen Matchups, deren
    Episoden laenger sind. Die Zusammensetzung des Mittels wuerde sich dort also
    aendern, was einen Sprung erzeugt, der nichts mit dem Lernverlauf zu tun hat.
    """
    laenge = min(len(l) for l in laeufe)
    return [statistics.mean([l[i][spalte] for l in laeufe])
            for i in range(laenge)], laenge


def zeichne(daten, ziel, felder, datei, ylabels, hoehe):
    fig, achsen = plt.subplots(1, len(felder), figsize=(7.2, hoehe))
    if len(felder) == 1:
        achsen = [achsen]
    grenzen = []
    for ax, (spalte, titel) in zip(achsen, felder):
        for topo in TOPOS:
            y, grenze = kurve(daten[topo], spalte)
            ax.plot(range(1, len(y) + 1), glaetten(y), color=FARBEN[topo],
                    linewidth=1.4, label=TITEL[topo])
            grenzen.append(grenze)
        ax.set_title(titel, loc="left", fontweight="bold")
        ax.set_xlabel("Episode")
        for rand in ("top", "right"):
            ax.spines[rand].set_visible(False)
    for ax, y in zip(achsen, ylabels):
        ax.set_ylabel(y)
    griffe, namen = achsen[0].get_legend_handles_labels()
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    fig.legend(griffe, namen, loc="lower center", ncol=3, fontsize=9,
               bbox_to_anchor=(0.5, 0.0))
    fig.savefig(os.path.join(ziel, datei))
    plt.close(fig)


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Nutzung: gen_aktionen.py <experiment-dir> [ausgabe]")
    quelle = os.path.join(sys.argv[1], "combined_episodes.csv")
    ziel = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(
        os.path.abspath(__file__))
    stil()
    daten = lade(quelle)
    zeichne(daten, ziel, [(1, "Reimages"), (2, "Sperren")],
            "aktionen_verlauf.pdf", ["Aktionen je Episode", ""], 3.4)
    zeichne(daten, ziel, [(3, "Abwehrbonus")],
            "abwehrbonus_verlauf.pdf", ["Bonus je Episode"], 3.2)

    print("Endwerte (Mittel der letzten zehn Episoden je Lauf):")
    for topo in TOPOS:
        werte = []
        for spalte in (1, 2, 3):
            werte.append(statistics.mean(
                [statistics.mean([e[spalte] for e in l[-10:]])
                 for l in daten[topo]]))
        print("  %-16s Reimages %6.1f   Sperren %6.1f   Abwehrbonus %7.2f"
              % (topo, werte[0], werte[1], werte[2]))


if __name__ == "__main__":
    main()
