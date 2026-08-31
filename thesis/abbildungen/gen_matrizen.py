#!/usr/bin/env python3
"""Vollstaendige Matrizen fuer den Anhang: Crown-Jewel-Quote, SLA-Brueche,
gehaltene Knoten und Abwehrbonus.

  cj_<topologie>.pdf      Anteil der Episoden mit erreichtem Crown Jewel, je
                          verteidigter Topologie ein Blatt mit sechs Feldern.
                          Gemeinsame Skala 0 bis 100 Prozent.
  sla_<topologie>.pdf     Schritte je Episode unterhalb der
                          Verfuegbarkeitsschwelle. Eigene Skala je Feld, weil
                          die Werte weit auseinanderliegen; die Summe ueber
                          alle fuenf Seeds steht deshalb in der
                          Feldueberschrift.
  knoten_<topologie>.pdf  Groesste Zahl gleichzeitig gehaltener Knoten je
                          Episode, gemittelt ueber die Seeds und geglaettet
                          ueber fuenf Episoden. Gemeinsame Skala 0 bis 10.
  abwehr_<topologie>.pdf  Abwehrbonus je Episode, gemittelt ueber die Seeds
                          und geglaettet ueber fuenf Episoden. Gemeinsame
                          Skala, Nulllinie eingezeichnet.

Bewusst je Topologie ein Blatt im Hochformat statt einer 4x6-Matrix quer: So
bleibt die Anordnung dieselbe wie bei den Lernkurven im Hauptteil, und die
Felder bleiben lesbar. Das Feld des auf dieser Topologie trainierten Angreifers
ist fett ueberschrieben.

Aufruf:
    python3 gen_matrizen.py <experiment-dir> [ausgabe-ordner]
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
ATT = ["chain", "flat", "hub_and_spoke", "dmz", "micro_segmented", "super"]
KURZ = {"flat": "flat", "hub_and_spoke": "h&s", "dmz": "dmz",
        "micro_segmented": "µseg", "chain": "chain", "super": "super"}

CJ_FARBE = "#E0A020"
SLA_FARBE = "#C4342B"
KNOTEN_FARBE = "#1F5FA9"
ABWEHR_FARBE = "#00857F"
GRID = "#D8D8D8"
TEXT = "#1A1A1A"
MUTED = "#5A5A5A"
FENSTER_CJ = 11
FENSTER = 5


def stil():
    plt.rcParams.update({
        "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.facecolor": "white", "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
        "font.size": 8, "axes.labelsize": 8,
        "axes.edgecolor": MUTED, "axes.labelcolor": TEXT, "text.color": TEXT,
        "xtick.color": MUTED, "ytick.color": MUTED,
        "xtick.labelsize": 7, "ytick.labelsize": 7,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5,
        "legend.frameon": False, "savefig.bbox": "tight",
    })


def lade(pfad):
    """(topologie, angreifer) -> (cj, sla, knoten, abwehr) je Seed."""
    cj = defaultdict(lambda: defaultdict(list))
    sla = defaultdict(lambda: defaultdict(list))
    kno = defaultdict(lambda: defaultdict(list))
    abw = defaultdict(lambda: defaultdict(list))
    with open(pfad, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["phase"] != "defender_matrix" or not r["episode_reward"]:
                continue
            schluessel = (r["topology"], r["attacker_name"])
            if r["agent"] == "attacker":
                cj[schluessel][r["run_id"]].append(
                    (int(r["episode"]), float(r["atk_cj_reached"] or 0)))
                kno[schluessel][r["run_id"]].append(
                    (int(r["episode"]), float(r["atk_max_owned"] or 0)))
            elif r["agent"] == "defender":
                sla[schluessel][r["run_id"]].append(
                    (int(r["episode"]), float(r["def_sla_break_steps"] or 0)))
                abw[schluessel][r["run_id"]].append(
                    (int(r["episode"]), float(r["def_abwehr_reward"] or 0)))

    def reihen(topf, schluessel):
        return [[v for _, v in sorted(topf[schluessel][rid])][:-1]
                for rid in sorted(topf[schluessel])]

    daten = {}
    for schluessel in cj:
        daten[schluessel] = (reihen(cj, schluessel), reihen(sla, schluessel),
                             reihen(kno, schluessel), reihen(abw, schluessel))
    return daten


def cj_quote(seeds):
    laenge = max(len(s) for s in seeds)
    h = FENSTER_CJ // 2
    return [100.0 * statistics.mean(
        [s[j] for s in seeds for j in range(max(0, i - h), min(len(s), i + h + 1))])
        for i in range(laenge)]


def mittel(seeds):
    laenge = max(len(s) for s in seeds)
    return [statistics.mean([s[i] for s in seeds if i < len(s)])
            for i in range(laenge)]


def glaetten(werte, fenster=FENSTER):
    h = fenster // 2
    return [statistics.mean(werte[max(0, i - h):min(len(werte), i + h + 1)])
            for i in range(len(werte))]


def tafel(daten, ziel, art, topo):
    """2x3 fuer eine verteidigte Topologie, ein Feld je Angreifer.

    Aufbau wie die Lernkurven im Hauptteil, damit der Leser dieselbe Anordnung
    wiedererkennt: sechs Felder, oben chain bis h&s, unten dmz bis super.
    """
    fig, achsen = plt.subplots(2, 3, figsize=(7.2, 4.6), sharex=True,
                               sharey=(art in ("cj", "knoten", "abwehr")))
    for ax, angreifer in zip(achsen.flat, ATT):
        cj_seeds, sla_seeds, kno_seeds, abw_seeds = daten[(topo, angreifer)]
        zusatz = ""
        if art == "cj":
            y = cj_quote(cj_seeds)
            ax.plot(range(1, len(y) + 1), y, color=CJ_FARBE, linewidth=1.4)
            ax.set_ylim(0, 105)
        elif art == "sla":
            y = mittel(sla_seeds)
            x = range(1, len(y) + 1)
            ax.plot(x, y, color=SLA_FARBE, linewidth=1.1)
            ax.fill_between(x, y, color=SLA_FARBE, alpha=0.25, linewidth=0)
            summe = int(sum(sum(s) for s in sla_seeds))
            zusatz = "   $\\Sigma$%s" % format(summe, ",d").replace(",", ".")
        elif art == "knoten":
            y = glaetten(mittel(kno_seeds))
            ax.plot(range(1, len(y) + 1), y, color=KNOTEN_FARBE, linewidth=1.4)
            ax.set_ylim(0, 10.5)
        else:
            y = glaetten(mittel(abw_seeds))
            ax.axhline(0, color=MUTED, linewidth=0.7, zorder=1)
            ax.plot(range(1, len(y) + 1), y, color=ABWEHR_FARBE, linewidth=1.4)
        ax.set_title("%s%s" % (KURZ[angreifer], zusatz), loc="left",
                     fontsize=10,
                     fontweight="bold" if topo == angreifer else "normal")
        ax.tick_params(labelsize=9)
        for rand in ("top", "right"):
            ax.spines[rand].set_visible(False)
    beschriftung = {"cj": "Crown Jewel [%]", "sla": "Schritte",
                    "knoten": "gehaltene Knoten", "abwehr": "Bonus je Episode"}
    for ax in achsen[:, 0]:
        ax.set_ylabel(beschriftung[art], fontsize=10)
    for ax in achsen[1, :]:
        ax.set_xlabel("Episode", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(ziel, "%s_%s.pdf" % (art, topo)))
    plt.close(fig)


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Nutzung: gen_matrizen.py <experiment-dir> [ausgabe]")
    quelle = os.path.join(sys.argv[1], "combined_episodes.csv")
    ziel = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(
        os.path.abspath(__file__))
    stil()
    daten = lade(quelle)
    for art in ("cj", "sla", "knoten", "abwehr"):
        for topo in TOPOS:
            tafel(daten, ziel, art, topo)
    print("geschrieben nach", ziel)


if __name__ == "__main__":
    main()
