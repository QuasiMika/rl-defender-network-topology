#!/usr/bin/env python3
"""Konvergenzpunkte beider Masse, je verteidigter Topologie ein Blatt.

Fuer jedes Matchup wird die Verteidigerkurve gezeichnet und darin markiert:

  * das Kriterium aus Abschnitt 3.7 (Streuung und Trend, jeweils <= 0,05 der
    Gesamtspanne, gehalten ueber zehn Episoden),
  * dasselbe Kriterium mit auf 0,01 verschaerftem Trendtest,
  * die 90-Prozent-Marke (Episode, ab der 90 % der Verbesserung des Laufs
    erreicht sind und zehn Episoden lang gehalten werden).

Alle drei Marken sind der Median ueber die fuenf Seeds, genau wie die Zahlen in
Kapitel 4. Der Median statt des Mittels, weil einzelne Seeds sehr spaet
konvergieren (flat gegen hub_and_spoke: 48, 49, 55, 63, 164) und das Mittel
eine Zelle dadurch langsamer erscheinen laesst, als sie ist.

Die LETZTE Episode jedes Laufs wird verworfen: Sie bricht ab, sobald das
Schrittbudget erschoepft ist, und ist deshalb nicht vergleichbar.

Aufruf:
    python3 gen_konvergenz.py <experiment-dir> [ausgabe-ordner]
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
ATT = ["chain", "flat", "hub_and_spoke", "dmz", "micro_segmented", "super"]
KURZ = {"flat": "flat", "hub_and_spoke": "h&s", "dmz": "dmz",
        "micro_segmented": "µseg", "chain": "chain", "super": "super"}

KURVE = "#1F5FA9"
MARKE_KRIT = "#C4342B"
MARKE_TREND = "#6B3FA0"
MARKE_90 = "#00857F"
GRID = "#D8D8D8"
TEXT = "#1A1A1A"
MUTED = "#5A5A5A"

W, PATIENCE = 15, 10
SCHWELLE_STREUUNG = 0.05
SCHWELLE_TREND_WEIT = 0.05    # Kriterium wie in Abschnitt 3.7
SCHWELLE_TREND_ENG = 0.01     # Gegenprobe mit getrenntem Trendtest
N, FENSTER = 10, 5


def stil():
    plt.rcParams.update({
        "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.facecolor": "white", "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
        "font.size": 9, "axes.labelsize": 9,
        "axes.edgecolor": MUTED, "axes.labelcolor": TEXT, "text.color": TEXT,
        "xtick.color": MUTED, "ytick.color": MUTED,
        "xtick.labelsize": 8, "ytick.labelsize": 8,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5,
        "legend.frameon": False, "savefig.bbox": "tight",
    })


def glaetten(w, f=FENSTER):
    h = f // 2
    return [statistics.mean(w[max(0, i - h):min(len(w), i + h + 1)])
            for i in range(len(w))]


def kriterium(rewards, s_trend=SCHWELLE_TREND_WEIT):
    """Streuungs- und Trendtest. Rueckgabe: bestaetigte Episode.

    s_trend trennt die beiden Faelle: 0,05 ist das Kriterium aus Abschnitt 3.7,
    0,01 die Gegenprobe mit strengerem Trendtest bei unveraenderter
    Streuungsschwelle.
    """
    n = len(rewards)
    if n < 2 * W:
        return None
    gehalten = 0
    for t in range(2 * W, n + 1):
        fenster = rewards[t - W:t]
        vor = rewards[t - 2 * W:t - W]
        spanne = max(max(rewards[:t]) - min(rewards[:t]), 1.0)
        streuung = statistics.pstdev(fenster) / spanne
        trend = abs(statistics.mean(fenster) - statistics.mean(vor)) / spanne
        if streuung <= SCHWELLE_STREUUNG and trend <= s_trend:
            gehalten += 1
            if gehalten >= PATIENCE:
                return t
        else:
            gehalten = 0
    return None


def marke90(rewards, q=0.90):
    """90-Prozent-Marke. Suche erst nach dem Startfenster."""
    g = glaetten(rewards)
    start = statistics.median(g[:N])
    ende = statistics.median(g[-N:])
    if ende <= start:
        return None
    ziel = start + q * (ende - start)
    n = len(g)
    for i in range(N, n):
        if all(g[j] >= ziel for j in range(i, min(n, i + PATIENCE))):
            return i + PATIENCE
    return None


def lade(pfad):
    roh = defaultdict(lambda: defaultdict(list))
    with open(pfad, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["phase"] != "defender_matrix" or r["agent"] != "defender":
                continue
            if not r["episode_reward"]:
                continue
            roh[(r["topology"], r["attacker_name"])][r["run_id"]].append(
                (int(r["episode"]), float(r["episode_reward"])))
    return {k: [[w for _, w in sorted(v)][:-1] for v in l.values()]
            for k, l in roh.items()}


def tafel(daten, topo, ziel):
    fig, achsen = plt.subplots(2, 3, figsize=(7.2, 4.6), sharex=True)
    for ax, angreifer in zip(achsen.flat, ATT):
        seeds = daten[(topo, angreifer)]
        laenge = max(len(s) for s in seeds)
        kurve = glaetten([statistics.mean([s[i] for s in seeds if i < len(s)])
                          for i in range(laenge)])
        ax.plot(range(1, laenge + 1), kurve, color=KURVE, linewidth=1.2,
                label="Verteidiger-Reward")

        for werte, farbe, stil_, name in (
                ([kriterium(s) for s in seeds], MARKE_KRIT, (0, (4, 2)),
                 "Kriterium aus Abschnitt 3.7"),
                ([kriterium(s, SCHWELLE_TREND_ENG) for s in seeds],
                 MARKE_TREND, (0, (5, 1, 1, 1)),
                 "mit Trendtest bis 0,01"),
                ([marke90(s) for s in seeds], MARKE_90, (0, (1, 1.6)),
                 "90-Prozent-Marke")):
            gueltig = [w for w in werte if w is not None]
            if gueltig:
                ax.axvline(statistics.median(gueltig), color=farbe, linewidth=1.2,
                           linestyle=stil_, zorder=3, label=name)

        ax.set_title(KURZ[angreifer], loc="left", fontsize=10,
                     fontweight="bold" if topo == angreifer else "normal")
        ax.tick_params(labelsize=9)
        for rand in ("top", "right"):
            ax.spines[rand].set_visible(False)
    for ax in achsen[:, 0]:
        ax.set_ylabel("Reward", fontsize=10)
    for ax in achsen[1, :]:
        ax.set_xlabel("Episode", fontsize=10)

    griffe, namen = achsen.flat[0].get_legend_handles_labels()
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    fig.legend(griffe, namen, loc="lower center", ncol=2, fontsize=9,
               bbox_to_anchor=(0.5, 0.0))
    fig.savefig(os.path.join(ziel, "konvergenz_%s.pdf" % topo))
    plt.close(fig)


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Nutzung: gen_konvergenz.py <experiment-dir> [ausgabe]")
    quelle = os.path.join(sys.argv[1], "combined_episodes.csv")
    ausgabe = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(
        os.path.abspath(__file__))
    stil()
    daten = lade(quelle)
    for topo in TOPOS:
        tafel(daten, topo, ausgabe)
    print("geschrieben nach", ausgabe)


if __name__ == "__main__":
    main()
