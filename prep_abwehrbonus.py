#!/usr/bin/env python3
"""
Verlauf des Abwehrbonus (Kantenbilanz) ueber die Trainingsepisoden, gemittelt
je verteidigter Topologie ueber alle sechs Angreifer und fuenf Seeds.

Der Abwehrbonus ist der Zustandsreward-Term aus der Kantenbilanz-Formel
(Kapitel 3, Beitrag(Z) = 0,00025 * Wert(Z) * (2f-1)), pro Episode aufsummiert
in der Spalte def_abwehr_reward. Anders als der Gesamtreward beruht dieser
Lauf durchgehend auf allen Seeds -- kein Auto-Stop, volles 500.000-Schritt-
Budget, also keine Fortschreibungs-/Ausstiegslogik noetig wie in
prep_curves.py.

Aufruf:
    python prep_abwehrbonus.py <experiment-dir> [ausgabe-verzeichnis]
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
KURZ = {"flat": "Flat", "hub_and_spoke": "Hub & Spoke", "dmz": "DMZ",
        "micro_segmented": "Micro-Segmentation"}
FARBE = {"flat": "#D9584A", "hub_and_spoke": "#2E9BC4",
         "dmz": "#D99A2B", "micro_segmented": "#6FBF8B"}

DARK = "#1B1F26"
MUTED = "#6E7681"
GRID = "#333A44"
GLAETTUNG = 5


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
    """topologie -> run_id -> [(episode, def_abwehr_reward)]"""
    je_topo = defaultdict(lambda: defaultdict(list))
    pfad = os.path.join(root, "combined_episodes.csv")
    with open(pfad, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["phase"] != "defender_matrix" or r["agent"] != "defender":
                continue
            v = r.get("def_abwehr_reward")
            if not v:
                continue
            t = r["topology"]
            if t not in DEFS:
                continue
            je_topo[t][r["run_id"]].append((int(r["episode"]), float(v)))
    return je_topo


def mittelkurve(reihen_je_run):
    """Mittel ueber alle Laeufe (Attacker x Seed) einer Topologie, Index = Episode."""
    laeufe = []
    for rid, reihe in reihen_je_run.items():
        reihe = sorted(reihe)
        laeufe.append([v for _ep, v in reihe])
    if not laeufe:
        return [], []
    max_ep = max(len(l) for l in laeufe)
    kurve, n = [], []
    for i in range(max_ep):
        werte = [l[i] for l in laeufe if i < len(l)]
        if not werte:
            break
        kurve.append(statistics.mean(werte))
        n.append(len(werte))
    return kurve, n


def zeichne(je_topo, out_dir):
    fig, ax = plt.subplots(figsize=(13.0, 6.0), facecolor=DARK)
    ax.set_facecolor(DARK)
    for sp in ax.spines.values():
        sp.set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=10)
    ax.grid(True, color=GRID, linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)
    ax.axhline(0, color=MUTED, linewidth=0.8, alpha=0.7)

    endwerte = {}
    for t in DEFS:
        kurve, n = mittelkurve(je_topo.get(t, {}))
        if not kurve:
            continue
        voll = max(n) if n else 0
        # Nur der Abschnitt, in dem noch alle Laeufe beitragen: sobald einzelne
        # (laengere) Episoden aus dem Budget herauslaufen, wird der Mittelwert
        # auf wenigen Laeufen berechnet und schlaegt unkontrolliert aus.
        bis = next((i for i, m in enumerate(n) if m < voll), len(n))
        kurve = glaetten(kurve)[:bis]
        if len(kurve) < 2:
            continue
        xs = list(range(1, len(kurve) + 1))
        ax.plot(xs, kurve, color=FARBE[t], linewidth=2.0, label=KURZ[t])
        endwerte[t] = statistics.mean(kurve[-20:])
        print("  %-17s Episode 1: %8.2f   letzte 20 im Mittel: %8.2f   volle Laenge bis Episode %d von %d Laeufen"
              % (t, kurve[0], endwerte[t], bis, voll))

    ax.set_xlabel("Episode", color=MUTED, fontsize=11)
    ax.set_ylabel("Abwehrbonus je Episode (Summe der Kantenbilanz-Beiträge)",
                  color=MUTED, fontsize=11)
    ax.legend(loc="lower right", frameon=False, labelcolor="#E6EAF0", fontsize=11)
    fig.suptitle("Verlauf des Abwehrbonus über das Training",
                 color="#FFFFFF", fontsize=17, x=0.06, ha="left", y=0.97)
    fig.text(0.06, 0.045,
             "Mittel über alle sechs Angreifer und fünf Seeds je verteidigter Topologie, geglättet (Fenster 5).",
             color="#8A929B", fontsize=9.5, ha="left")
    fig.text(0.06, 0.015,
             "Jede Linie endet dort, wo der erste der 30 Läufe sein Schrittbudget ausschöpft und aus dem Mittel fällt.",
             color="#8A929B", fontsize=9.5, ha="left")
    fig.subplots_adjust(left=0.06, right=0.985, top=0.90, bottom=0.16)
    pfad = os.path.join(out_dir, "abwehrbonus_verlauf.png")
    fig.savefig(pfad, dpi=170, facecolor=DARK)
    plt.close(fig)
    print("  " + pfad)
    return endwerte


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Nutzung: python prep_abwehrbonus.py <experiment-dir> [out-dir]")
    root = sys.argv[1].rstrip("/\\")
    out_dir = sys.argv[2] if len(sys.argv) > 2 else root
    os.makedirs(out_dir, exist_ok=True)
    je_topo = lade(root)
    print("Topologien mit Daten:", sorted(je_topo.keys()))
    zeichne(je_topo, out_dir)


if __name__ == "__main__":
    main()
