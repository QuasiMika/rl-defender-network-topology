# -*- coding: utf-8 -*-
"""Audit Teil 4: Konvergenz bei 0,05 auf Medianen, damit 4.4 durchgaengig
dieselbe Statistik verwendet wie seine zweite Haelfte."""
import csv, os, statistics as st
from collections import defaultdict

import sys

# Lauf-Ordner relativ zur Lage dieser Datei (<repo>/thesis/pruefung/).
# Ueberschreibbar per Argument: python3 <skript>.py <anderer-lauf-ordner>
ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "experiments", "20260820_005936")
W, PATIENCE = 15, 10
TOP = ["flat", "hub_and_spoke", "dmz", "micro_segmented"]
ATT = ["chain", "flat", "hub_and_spoke", "dmz", "micro_segmented", "super"]


def konv(r, ss, stt):
    g = 0
    for t in range(2 * W, len(r) + 1):
        f, v = r[t - W:t], r[t - 2 * W:t - W]
        sp = max(max(r[:t]) - min(r[:t]), 1.0)
        if st.pstdev(f) / sp <= ss and abs(st.mean(f) - st.mean(v)) / sp <= stt:
            g += 1
            if g >= PATIENCE:
                return t
        else:
            g = 0
    return None


runs, meta = defaultdict(list), {}
with open(os.path.join(ROOT, "combined_episodes.csv"), encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["phase"] != "defender_matrix" or r["agent"] != "defender" \
           or not r["episode_reward"]:
            continue
        runs[r["run_id"]].append((int(r["episode"]), float(r["episode_reward"])))
        meta[r["run_id"]] = (r["topology"], r["attacker_name"])
reihen = {k: [w for _, w in sorted(v)][:-1] for k, v in runs.items()}

for schwelle in (0.05, 0.01):
    je_m, je_t, alle = defaultdict(list), defaultdict(list), []
    for rid, r in reihen.items():
        e = konv(r, 0.05, schwelle)
        if e is None:
            continue
        je_m[meta[rid]].append(e)
        je_t[meta[rid][0]].append(e)
        alle.append(e)
    print("=" * 74)
    print("Trend <= %.2f :  %d/120   Median %.1f   Min %d   Max %d"
          % (schwelle, len(alle), st.median(alle), min(alle), max(alle)))
    print("  Median je Topologie: " + "  ".join("%s %.0f" % (t, st.median(je_t[t]))
                                                for t in TOP))
    q = {t: (st.median(sorted(je_t[t])[:15]), st.median(sorted(je_t[t])[15:]))
         for t in TOP}
    print("  Quartile je Topologie: " + "  ".join("%s %.0f-%.0f" % (t, q[t][0], q[t][1])
                                                  for t in TOP))
    print("  Zellenmediane:")
    for t in TOP:
        z = ["%s%3.0f" % ("*" if a == t else " ", st.median(je_m[(t, a)])) for a in ATT]
        d = st.median(je_m[(t, t)])
        rest = [st.median(je_m[(t, a)]) for a in ATT if a != t]
        print("    %-16s %s   Diagonale %s"
              % (t, " ".join(z),
                 "hoechste" if d > max(rest) else
                 ("gleichauf" if d == max(rest) else "Platz %d"
                  % (1 + sum(1 for x in rest if x > d)))))
    dg = [st.median(je_m[(t, t)]) for t in TOP]
    off = [st.median(je_m[(t, a)]) for t in TOP for a in ATT if a != t]
    print("  Diagonale %.0f-%.0f   uebrige %.0f-%.0f"
          % (min(dg), max(dg), min(off), max(off)))
