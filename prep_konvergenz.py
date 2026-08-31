#!/usr/bin/env python3
"""Echte, nachtraegliche Konvergenz nach dem Kapitel-3-Kriterium.

Ersetzt die "autostop"-Zaehlung aus prep_analysis.py, die auf einem Live-
Abbruch waehrend des Trainings beruht. Die Matrix in 20260820_005936 lief
bewusst ohne Auto-Stop; jeder Lauf hat das volle 500.000er-Budget. Konvergenz
wird deshalb nachtraeglich auf der vollstaendigen Episodenreihe bestimmt:

    sigma(letzte W) / Spanne <= 0,05   UND
    |Mittel(letzte W) - Mittel(W davor)| / Spanne <= 0,05

ueber W = 15 Episoden, gehalten fuer 10 aufeinanderfolgende Episoden
(Patience). Spanne = max - min aller bisherigen Rewards des Laufs (min. 1,0).

Aufruf:
    python prep_konvergenz.py <experiment-dir> [analysis.json]

Schreibt "convergence" in die uebergebene analysis.json neu (autostop wird zur
Zahl konvergierter Seeds, mean_episodes zur mittleren Konvergenzepisode).
"""
import csv
import json
import os
import statistics
import sys
from collections import defaultdict

TOPOS = ["flat", "hub_and_spoke", "dmz", "micro_segmented"]
ATTACKERS = ["chain", "flat", "hub_and_spoke", "dmz", "micro_segmented", "super"]
W = 15
SCHWELLE = 0.05
PATIENCE = 10


def konvergenz_episode(rewards):
    """Episode, in der beide Bedingungen PATIENCE Episoden lang gehalten haben.

    Zurueckgegeben wird t, also die Episode, in der die Strecke vollstaendig
    ist -- nicht deren Beginn. Erst dort ist die Konvergenz bestaetigt; der
    Beginn allein ist von einem Schein-Plateau nicht zu unterscheiden. Daraus
    folgt der fruehestmoegliche Wert 2*W + PATIENCE - 1 = 39.

    Frueher wurde t - PATIENCE + 1 zurueckgegeben; das ergab scheinbar
    Konvergenz ab Episode 30 und widersprach der Definition in Kapitel 3.

    None, wenn der Lauf innerhalb seiner Laenge nicht konvergiert.
    """
    n = len(rewards)
    if n < 2 * W:
        return None
    gehalten = 0
    for t in range(2 * W, n + 1):
        fenster = rewards[t - W:t]
        vorfenster = rewards[t - 2 * W:t - W]
        spanne = max(max(rewards[:t]) - min(rewards[:t]), 1.0)
        sigma = statistics.pstdev(fenster)
        trend = abs(statistics.mean(fenster) - statistics.mean(vorfenster))
        if sigma / spanne <= SCHWELLE and trend / spanne <= SCHWELLE:
            gehalten += 1
            if gehalten >= PATIENCE:
                return t   # Episode, in der die Strecke bestaetigt ist
        else:
            gehalten = 0
    return None


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Nutzung: python prep_konvergenz.py <experiment-dir> [analysis.json]")
    root = sys.argv[1].rstrip("/\\")
    out_path = sys.argv[2] if len(sys.argv) > 2 else "analysis.json"

    rows = list(csv.DictReader(open(os.path.join(root, "combined_episodes.csv"), encoding="utf-8")))
    dm = [r for r in rows if r["phase"] == "defender_matrix" and r["episode_reward"] not in ("", None)]

    runs = defaultdict(list)
    meta = {}
    for r in dm:
        if r["agent"] != "defender":
            continue
        runs[r["run_id"]].append((int(r["episode"]), float(r["episode_reward"])))
        meta[r["run_id"]] = (r["topology"], r["attacker_name"])
    for rid in runs:
        runs[rid].sort()

    matchup_runs = defaultdict(list)
    for rid, (t, a) in meta.items():
        matchup_runs[(t, a)].append(rid)

    convergence = {t: {} for t in TOPOS}
    gesamt_konvergiert = 0
    gesamt_laeufe = 0
    for t in TOPOS:
        for a in ATTACKERS:
            rids = sorted(matchup_runs.get((t, a), []))
            if not rids:
                convergence[t][a] = None
                continue
            episoden = []
            for rid in rids:
                reihe = [v for _ep, v in runs[rid]]
                ep = konvergenz_episode(reihe)
                gesamt_laeufe += 1
                if ep is not None:
                    episoden.append(ep)
                    gesamt_konvergiert += 1
            convergence[t][a] = dict(
                autostop=len(episoden),   # Feldname beibehalten: hier "Anzahl konvergierter Seeds"
                n_seeds=len(rids),
                mean_episodes=round(statistics.mean(episoden), 1) if episoden else None,
            )

    with open(out_path, encoding="utf-8") as f:
        analysis = json.load(f)
    analysis["convergence"] = convergence
    analysis["meta"]["autostop"] = gesamt_konvergiert
    analysis["meta"]["autostop_pct"] = round(100 * gesamt_konvergiert / gesamt_laeufe, 1) if gesamt_laeufe else 0
    analysis["meta"]["konvergenz_kriterium"] = "post-hoc, W=15, Schwelle 0.05, Patience 10 (Kapitel 3)"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f)

    print("%d von %d Laeufen konvergieren nachtraeglich (%.1f %%)"
          % (gesamt_konvergiert, gesamt_laeufe, analysis["meta"]["autostop_pct"]))
    for t in TOPOS:
        zeile = []
        for a in ATTACKERS:
            v = convergence[t][a]
            zeile.append("%s:%d/%d" % (a[:4], v["autostop"], v["n_seeds"]) if v else "%s:--" % a[:4])
        print("  %-16s " % t + "  ".join(zeile))


if __name__ == "__main__":
    main()
