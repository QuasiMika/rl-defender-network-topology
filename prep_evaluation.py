#!/usr/bin/env python3
"""
Bereitet die Wirksamkeits-Evaluation auf (evaluation_episodes.csv).

Kernabbildung ist die volle 4x6-Matrix: je Matchup drei Balken fuer die drei
Stufen (kein Verteidiger / zufaelliger Verteidiger / trainiertes Modell).
Ein Zeilenmittel ueber sechs so verschiedene Angreifer waere irrefuehrend --
der Chain-Angreifer kommt ausserhalb seiner Kette praktisch nie ans Ziel und
druecken den Schnitt, waehrend der jeweils topologieeigene Angreifer ihn hebt.

Aufruf:
    python prep_evaluation.py <experiment-dir> [ausgabe-verzeichnis]
"""
from __future__ import annotations

import csv
import json
import os
import statistics
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

DEFS = ["flat", "hub_and_spoke", "dmz", "micro_segmented"]
ATKS = ["chain", "flat", "hub_and_spoke", "dmz", "micro_segmented", "super"]
STUFEN = [("keiner", "kein Verteidiger", "#8A9199"),
          ("zufaellig", "zufälliger Verteidiger", "#C2A05A"),
          ("trainiert", "trainiertes Modell", "#2E9BC4")]

KURZ = {"flat": "Flat", "hub_and_spoke": "Hub & Spoke", "dmz": "DMZ",
        "micro_segmented": "Micro-Segmentation", "chain": "Chain", "super": "Super"}

DARK = "#1B1F26"
MUTED = "#6E7681"
GRID = "#333A44"


def lade(root):
    pfad = os.path.join(root, "evaluation_episodes.csv")
    rows = [r for r in csv.DictReader(open(pfad)) if r["agent"] == "attacker"]
    # (topologie, angreifer, stufe, run_id) -> Episodenliste
    je_seed = defaultdict(list)
    for r in rows:
        je_seed[(r["topology"], r["attacker_name"], r["stufe"], r["run_id"])].append(r)
    return je_seed


def kennzahl(eps, art):
    if art == "cj":
        v = [e for e in eps if e.get("atk_cj_reached") not in ("", None)]
        return 100.0 * sum(1 for e in v if e["atk_cj_reached"] == "1") / len(v) if v else None
    if art == "owned":
        v = [float(e["atk_max_owned"]) for e in eps if e.get("atk_max_owned")]
        return statistics.mean(v) if v else None
    return None


def werte(je_seed, topo, atk, stufe, art):
    """Rueckgabe: (Gesamtwert ueber alle Seeds, min, max ueber die Seeds)."""
    seeds = [v for (t, a, s, _rid), v in je_seed.items()
             if t == topo and a == atk and s == stufe]
    if not seeds:
        return None, None, None
    alle = [e for v in seeds for e in v]
    je = [kennzahl(v, art) for v in seeds]
    je = [x for x in je if x is not None]
    return kennzahl(alle, art), (min(je) if je else None), (max(je) if je else None)


def zeichne(je_seed, out_dir, art, titel, ylabel, ymax):
    fig, achsen = plt.subplots(4, 6, figsize=(13.0, 7.0), facecolor=DARK,
                               sharey=True)
    fig.subplots_adjust(left=0.085, right=0.985, top=0.885, bottom=0.145,
                        wspace=0.16, hspace=0.50)

    for i, topo in enumerate(DEFS):
        for j, atk in enumerate(ATKS):
            ax = achsen[i][j]
            ax.set_facecolor(DARK)
            for sp in ax.spines.values():
                sp.set_color(GRID)
            ax.tick_params(colors=MUTED, labelsize=7)
            ax.grid(True, axis="y", color=GRID, linewidth=0.5, alpha=0.6)
            ax.set_axisbelow(True)
            ax.set_ylim(0, ymax)
            ax.set_xticks([])

            for k, (stufe, _lbl, farbe) in enumerate(STUFEN):
                w, lo, hi = werte(je_seed, topo, atk, stufe, art)
                if w is None:
                    continue
                ax.bar(k, w, width=0.72, color=farbe, zorder=2)
                if lo is not None and hi is not None and hi > lo:
                    ax.plot([k, k], [lo, hi], color="#E6EAF0", linewidth=0.9,
                            alpha=0.75, zorder=3)
                ax.text(k, min(w + ymax * 0.035, ymax * 0.94),
                        ("%.0f" % w) if art == "cj" else ("%.1f" % w),
                        ha="center", va="bottom", color="#C6CDD6", fontsize=6.5,
                        zorder=4)

            eigen = (topo == atk)
            ax.set_title(KURZ[atk] + ("  ★" if eigen else ""),
                         color="#E6EAF0" if eigen else "#9AA4AE",
                         fontsize=8.0, pad=4, loc="left",
                         fontweight="bold" if eigen else "normal")
            if j == 0:
                ax.set_ylabel(KURZ[topo], color="#E6EAF0", fontsize=9,
                              labelpad=8, fontweight="bold")

    fig.suptitle(titel, color="#FFFFFF", fontsize=15, x=0.085, ha="left", y=0.965)
    fig.text(0.085, 0.915,
             "Zeile = verteidigte Topologie, Spalte = Angreifer.  ★ = Angreifer "
             "wurde auf genau dieser Topologie trainiert.  "
             "Senkrechter Strich = Spannweite über die fünf Seeds.",
             color="#8A929B", fontsize=8.0, ha="left")
    fig.text(0.085, 0.055, ylabel, color=MUTED, fontsize=8.5, ha="left")

    legende = [Patch(facecolor=c, label=l) for _s, l, c in STUFEN]
    fig.legend(handles=legende, loc="lower center", ncol=3, frameon=False,
               labelcolor="#B8C0C9", fontsize=9, bbox_to_anchor=(0.55, 0.01))

    pfad = os.path.join(out_dir, "wirksamkeit_%s.png" % art)
    fig.savefig(pfad, dpi=170, facecolor=DARK)
    plt.close(fig)
    print("  " + pfad)


def tabelle(je_seed, out_dir):
    """Kennzahlen je Matchup und Stufe als JSON fuer den Foliensatz."""
    out = {}
    for topo in DEFS:
        out[topo] = {}
        for atk in ATKS:
            out[topo][atk] = {}
            for stufe, _l, _c in STUFEN:
                cj, _lo, _hi = werte(je_seed, topo, atk, stufe, "cj")
                ow, _lo2, _hi2 = werte(je_seed, topo, atk, stufe, "owned")
                out[topo][atk][stufe] = {
                    "cj_pct": round(cj, 1) if cj is not None else None,
                    "max_owned": round(ow, 2) if ow is not None else None,
                }
    pfad = os.path.join(out_dir, "wirksamkeit_table.json")
    json.dump(out, open(pfad, "w"), indent=1)
    print("  " + pfad)


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Nutzung: python prep_evaluation.py <experiment-dir> [out-dir]")
    root = sys.argv[1].rstrip("/\\")
    out_dir = sys.argv[2] if len(sys.argv) > 2 else root
    os.makedirs(out_dir, exist_ok=True)

    je_seed = lade(root)
    print("%d Zellen geladen" % len(je_seed))
    zeichne(je_seed, out_dir, "cj",
            "Wirksamkeit: erreicht der Angreifer den Crown Jewel?",
            "Anteil der Episoden mit erreichtem Crown Jewel (%)", 100)
    zeichne(je_seed, out_dir, "owned",
            "Wirksamkeit: wie viele Knoten übernimmt der Angreifer?",
            "Übernommene Knoten im Mittel (von 10)", 10)
    tabelle(je_seed, out_dir)


if __name__ == "__main__":
    main()
