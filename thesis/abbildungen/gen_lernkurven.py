#!/usr/bin/env python3
"""Lernkurven-Abbildungen fuer Kapitel 4 der Bachelorarbeit.

Erzeugt aus combined_episodes.csv eines Matrix-Laufs:

  lernkurven_uebersicht.pdf   2x2, je Feld eine verteidigte Topologie mit den
                              Kurven aller sechs Angreifer (nur Verteidiger-
                              Reward). Fuer den Hauptteil.
  lernkurven_<topologie>.pdf  2x3, je Feld ein Matchup mit Verteidiger- UND
                              Angreiferkurve. Fuer den Anhang.

Bewusst helles Thema, serifenlose Schrift und HTWG-Petrol als Leitfarbe,
passend zum Satz der Arbeit. Anders als die Folien des Auswertungsdecks, aus
dem diese Abbildungen NICHT uebernommen werden.

Aufruf:
    python3 gen_lernkurven.py <experiment-dir> [ausgabe-ordner]
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

TOPOS = ["flat", "hub_and_spoke", "dmz", "micro_segmented"]
ATTACKERS = ["chain", "flat", "hub_and_spoke", "dmz", "micro_segmented", "super"]

KURZ = {"flat": "flat", "hub_and_spoke": "hub\\_and\\_spoke", "dmz": "dmz",
        "micro_segmented": "micro\\_segmented", "chain": "chain", "super": "super"}
TITEL = {"flat": "flat", "hub_and_spoke": "hub_and_spoke", "dmz": "dmz",
         "micro_segmented": "micro_segmented", "chain": "chain", "super": "super"}

# ── Farben ───────────────────────────────────────────────────────────────────
# htwg-teal (cmyk 1,0,0.5,0) als Leitfarbe, dazu fuenf gut unterscheidbare
# Toene fuer die uebrigen Angreifer. Auf ausreichenden Hell-Dunkel-Abstand
# geachtet, damit die Abbildung auch im Graustufendruck lesbar bleibt.
TEAL = "#00857F"
FARBEN = {
    "chain":            "#8C8C8C",
    "flat":             "#C4342B",
    "hub_and_spoke":    "#1F5FA9",
    "dmz":              "#E08A1E",
    "micro_segmented":  TEAL,
    "super":            "#6B3FA0",
}
GRID = "#D8D8D8"
TEXT = "#1A1A1A"
MUTED = "#5A5A5A"
ANGREIFER_FARBE = "#C4342B"
VERTEIDIGER_FARBE = "#1F5FA9"

# Gleitendes Mittel ueber fuenf Episoden, zentriert. Bewusst ein Mittel und
# kein Median: Der Median eines breiteren Fensters entfernt einzelne
# Ausreisser vollstaendig, und gerade die sind hier von Interesse -- ein
# spaeter Einbruch der Verteidigerkurve steht fuer eine Episode mit
# SLA-Bruechen und soll sichtbar bleiben. Fuenf Episoden entsprechen der
# Glaettung der begleitenden Auswertung.
FENSTER = 5

# JE_SEED: eine Markierung je Lauf statt nur beim ersten Ende.
# Ueber die Umgebungsvariable JE_SEED=1 zum Vergleich einschaltbar.
JE_SEED = bool(os.environ.get("JE_SEED"))


def stil():
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "axes.edgecolor": MUTED,
        "axes.labelcolor": TEXT,
        "text.color": TEXT,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "legend.frameon": False,
        "legend.fontsize": 8.5,
        "savefig.bbox": "tight",
    })


def glaetten(werte, fenster=FENSTER):
    """Zentriertes gleitendes Mittel. Randwerte ueber ein verkuerztes Fenster."""
    n = len(werte)
    halb = fenster // 2
    return [statistics.mean(werte[max(0, i - halb):min(n, i + halb + 1)])
            for i in range(n)]


def lade(pfad):
    """(topologie, angreifer, agent) -> Liste von Kurven, eine je Seed."""
    roh = defaultdict(lambda: defaultdict(list))
    with open(pfad, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["phase"] != "defender_matrix":
                continue
            if not r["episode_reward"]:
                continue
            schluessel = (r["topology"], r["attacker_name"], r["agent"])
            roh[schluessel][r["run_id"]].append(
                (int(r["episode"]), float(r["episode_reward"])))
    kurven = {}
    for schluessel, laeufe in roh.items():
        kurven[schluessel] = [[w for _, w in sorted(reihe)][:-1]
                              for reihe in laeufe.values()]
    return kurven


def mittelkurve(seeds):
    """Punktweises Mittel ueber alle Seeds, die bis dorthin reichen.

    Rueckgabe: (Kurve, Episode, ab der nicht mehr alle Seeds beitragen).

    Die Laeufe unterscheiden sich in der Episodenzahl, weil das Budget in
    Schritten und nicht in Episoden vergeben ist. Bei der kuerzesten Reihe
    abzuschneiden waere irrefuehrend: Die laengeren Laeufe verbessern sich
    danach weiter, und die Abbildung endete auf einem schlechteren Wert als die
    Tabellen, die je Seed dessen eigene letzten Episoden verwenden. Statt zu
    kuerzen wird die Stelle markiert, ab der das Mittel auf weniger Laeufen
    beruht.
    """
    if not seeds:
        return [], []
    laenge = max(len(s) for s in seeds)
    kurve = []
    for i in range(laenge):
        werte = [s[i] for s in seeds if i < len(s)]
        kurve.append(statistics.mean(werte))
    enden = sorted(len(s) for s in seeds)
    # Nur die Enden vor dem letzten sind interessant; das letzte ist das
    # Ende der Kurve selbst.
    return kurve, [e for e in enden[:-1] if e < laenge]


def uebersicht(kurven, ziel):
    """2x2: je Feld eine verteidigte Topologie, sechs Angreiferkurven."""
    fig, achsen = plt.subplots(2, 2, figsize=(7.2, 5.2), sharex=True)
    for ax, topo in zip(achsen.flat, TOPOS):
        for angreifer in ATTACKERS:
            reihe, _ = mittelkurve(kurven.get((topo, angreifer, "defender"), []))
            if not reihe:
                continue
            ax.plot(range(1, len(reihe) + 1), glaetten(reihe),
                    color=FARBEN[angreifer], linewidth=1.3,
                    label=TITEL[angreifer])
        ax.axhline(0, color=MUTED, linewidth=0.8, zorder=1)
        ax.set_title(TITEL[topo], loc="left", fontweight="bold")
        ax.set_ylim(-2600, 250)
        ax.set_xlim(1, 250)
        for rand in ("top", "right"):
            ax.spines[rand].set_visible(False)
    for ax in achsen[:, 0]:
        ax.set_ylabel("Verteidiger-Reward")
    for ax in achsen[1, :]:
        ax.set_xlabel("Episode")
    griffe, namen = achsen.flat[0].get_legend_handles_labels()
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.legend(griffe, namen, loc="lower center", ncol=6,
               bbox_to_anchor=(0.5, 0.0))
    fig.savefig(os.path.join(ziel, "lernkurven_uebersicht.pdf"))
    plt.close(fig)


def detail(kurven, topo, ziel):
    """2x3 fuer eine verteidigte Topologie: Verteidiger und Angreifer.

    Groesser gesetzt als die Uebersicht, weil diese Abbildungen im Hauptteil
    einzeln besprochen werden und die Achsenbeschriftung dort lesbar sein muss.
    """
    fig, achsen = plt.subplots(2, 3, figsize=(7.2, 5.0), sharex=True)
    # Gemeinsame x-Achse ueber die laengste Reihe dieser Topologie, damit auch
    # die drei Matchups mit ueberlangen Laeufen vollstaendig sichtbar sind.
    breite = max((len(s) for a in ATTACKERS
                  for s in kurven.get((topo, a, "defender"), [])), default=250)
    markiert = False
    for ax, angreifer in zip(achsen.flat, ATTACKERS):
        v, enden = mittelkurve(kurven.get((topo, angreifer, "defender"), []))
        a, _ = mittelkurve(kurven.get((topo, angreifer, "attacker"), []))
        if a:
            ax.plot(range(1, len(a) + 1), glaetten(a),
                    color=ANGREIFER_FARBE, linewidth=1.5, label="Angreifer")
        if v:
            ax.plot(range(1, len(v) + 1), glaetten(v),
                    color=VERTEIDIGER_FARBE, linewidth=1.5, label="Verteidiger")
        stellen = enden if JE_SEED else enden[:1]
        for x in stellen:
            ax.axvline(x, color=MUTED, linewidth=0.8, linestyle=(0, (2, 2)),
                       zorder=1,
                       label=("Ende eines Laufs" if not markiert else None))
            markiert = True
        ax.axhline(0, color=MUTED, linewidth=0.8, zorder=1)
        ax.set_title(TITEL[angreifer], loc="left", fontsize=10,
                     fontweight="bold")
        ax.set_xlim(1, breite)
        ax.tick_params(labelsize=9)
        for rand in ("top", "right"):
            ax.spines[rand].set_visible(False)
    for ax in achsen[:, 0]:
        ax.set_ylabel("Reward", fontsize=10)
    for ax in achsen[1, :]:
        ax.set_xlabel("Episode", fontsize=10)
    griffe, namen = [], []
    for ax in achsen.flat:
        for g, n in zip(*ax.get_legend_handles_labels()):
            if n not in namen:
                griffe.append(g)
                namen.append(n)
    if "Ende eines Laufs" in namen:
        i = namen.index("Ende eines Laufs")
        namen[i] = ("ab hier weniger als fünf Läufe im Mittel"
                    if not JE_SEED else "Ende eines der fünf Läufe")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.legend(griffe, namen, loc="lower center", ncol=3, fontsize=9,
               bbox_to_anchor=(0.5, 0.0))
    fig.savefig(os.path.join(ziel, "lernkurven_%s.pdf" % topo))
    plt.close(fig)


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Nutzung: gen_lernkurven.py <experiment-dir> [ausgabe]")
    quelle = os.path.join(sys.argv[1], "combined_episodes.csv")
    ziel = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(
        os.path.abspath(__file__))
    stil()
    kurven = lade(quelle)
    uebersicht(kurven, ziel)
    for topo in TOPOS:
        detail(kurven, topo, ziel)
    print("geschrieben nach", ziel)


if __name__ == "__main__":
    main()
