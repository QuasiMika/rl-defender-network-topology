#!/usr/bin/env python3
"""
Verlauf der Crown-Jewel-Quote ueber die Trainingsepisoden, ein 2x3-Raster je
verteidigter Topologie (Zeile/Spalte wie in prep_curves.py: eine Kachel je
Angreifer).

Je Episode wird ueber die fuenf Seeds gemittelt, ob der Angreifer den Crown
Jewel erreicht hat (atk_cj_reached, 0/1), dann geglaettet. Anders als beim
Reward ist das je Episode nur eine binaere Groesse ueber 5 Seeds, deshalb ein
breiteres Glaettungsfenster als bei den Reward-Kurven.

Aufruf:
    python prep_cj_verlauf.py <experiment-dir> [ausgabe-verzeichnis]
"""
import csv
import os
import statistics
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFS = ["flat", "hub_and_spoke", "dmz", "micro_segmented"]
ATKS = ["chain", "flat", "hub_and_spoke", "dmz", "micro_segmented", "super"]
KURZ = {"flat": "Flat", "hub_and_spoke": "Hub & Spoke", "dmz": "DMZ",
        "micro_segmented": "Micro-Segmentation", "chain": "Chain", "super": "Super"}

DARK = "#1B1F26"
MUTED = "#6E7681"
GRID = "#333A44"
CJ_C = "#D99A2B"
GLAETTUNG = 15


def glaetten(werte, w=GLAETTUNG):
    if len(werte) < w:
        return list(werte)
    out = []
    for i in range(len(werte)):
        a = max(0, i - w // 2)
        b = min(len(werte), i + w // 2 + 1)
        out.append(sum(werte[a:b]) / (b - a))
    return out


def lade(root):
    """(topologie, angreifer) -> run_id -> [(episode, cj_reached 0/1)]"""
    je_matchup = defaultdict(lambda: defaultdict(list))
    pfad = os.path.join(root, "combined_episodes.csv")
    with open(pfad, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["phase"] != "defender_matrix" or r["agent"] != "attacker":
                continue
            v = r.get("atk_cj_reached")
            if v in (None, ""):
                continue
            t, a = r["topology"], r["attacker_name"]
            if t not in DEFS or a not in ATKS:
                continue
            je_matchup[(t, a)][r["run_id"]].append((int(r["episode"]), float(v)))
    return je_matchup


def mittelkurve(reihen_je_run):
    laeufe = []
    for rid, reihe in reihen_je_run.items():
        reihe = sorted(reihe)
        laeufe.append([v for _ep, v in reihe])
    if not laeufe:
        return [], [], 0
    voll = len(laeufe)
    max_ep = max(len(l) for l in laeufe)
    kurve, n = [], []
    for i in range(max_ep):
        werte = [l[i] for l in laeufe if i < len(l)]
        if not werte:
            break
        kurve.append(100.0 * statistics.mean(werte))
        n.append(len(werte))
    return kurve, n, voll


def zeichne(je_matchup, out_dir):
    for topo in DEFS:
        fig, achsen = plt.subplots(2, 3, figsize=(13.0, 6.1), facecolor=DARK,
                                   sharey=True)
        fig.subplots_adjust(left=0.055, right=0.985, top=0.90, bottom=0.16,
                            wspace=0.16, hspace=0.42)
        for k, atk in enumerate(ATKS):
            ax = achsen[k // 3][k % 3]
            ax.set_facecolor(DARK)
            for sp in ax.spines.values():
                sp.set_color(GRID)
            ax.tick_params(colors=MUTED, labelsize=7.5)
            ax.grid(True, color=GRID, linewidth=0.6, alpha=0.7)
            ax.set_axisbelow(True)
            ax.set_ylim(0, 100)

            kurve, n, voll = mittelkurve(je_matchup.get((topo, atk), {}))
            if not kurve:
                ax.text(0.5, 0.5, "keine Daten", color=MUTED, ha="center",
                        transform=ax.transAxes, fontsize=9)
                ax.set_title(KURZ[atk], color=MUTED, fontsize=10, pad=6)
                continue

            bis = next((i for i, m in enumerate(n) if m < voll), len(n))
            kurve = glaetten(kurve)[:bis]
            if len(kurve) < 2:
                ax.text(0.5, 0.5, "zu wenig Daten", color=MUTED, ha="center",
                        transform=ax.transAxes, fontsize=9)
                ax.set_title(KURZ[atk], color=MUTED, fontsize=10, pad=6)
                continue
            xs = list(range(1, len(kurve) + 1))
            ax.plot(xs, kurve, color=CJ_C, linewidth=1.8)

            eigen = (topo == atk)
            ax.set_title(KURZ[atk] + ("  ★" if eigen else ""),
                         color="#E6EAF0" if eigen else "#9AA4AE", fontsize=9.5,
                         pad=6, loc="left", fontweight="bold" if eigen else "normal")
            if k // 3 == 1:
                ax.set_xlabel("Episode", color=MUTED, fontsize=8)
            if k % 3 == 0:
                ax.set_ylabel("Crown Jewel erreicht (%)", color=MUTED, fontsize=8)

        fig.suptitle("Crown-Jewel-Quote im Trainingsverlauf — Verteidiger auf %s" % KURZ[topo],
                     color="#FFFFFF", fontsize=15, x=0.055, ha="left", y=0.975)
        fig.text(0.055, 0.045,
                 "Anteil der 5 Seeds, die den Crown Jewel in dieser Episode erreicht haben, geglättet (Fenster 15). ★ = Angreifer auf dieser Topologie trainiert.",
                 color="#8A929B", fontsize=8.5, ha="left")
        fig.text(0.055, 0.02,
                 "Kurve endet, sobald der erste der 5 Seeds sein Schrittbudget ausschöpft und aus dem Mittel fällt.",
                 color="#8A929B", fontsize=8.5, ha="left")
        pfad = os.path.join(out_dir, "cj_verlauf_%s.png" % topo)
        fig.savefig(pfad, dpi=170, facecolor=DARK)
        plt.close(fig)
        print("  " + pfad)


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Nutzung: python prep_cj_verlauf.py <experiment-dir> [out-dir]")
    root = sys.argv[1].rstrip("/\\")
    out_dir = sys.argv[2] if len(sys.argv) > 2 else root
    os.makedirs(out_dir, exist_ok=True)
    je_matchup = lade(root)
    print("%d Matchups mit Daten" % len(je_matchup))
    zeichne(je_matchup, out_dir)


if __name__ == "__main__":
    main()
