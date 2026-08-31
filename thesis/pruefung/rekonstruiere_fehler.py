# -*- coding: utf-8 -*-
"""Lassen sich die falschen Zahlen aus einem anderen Rechenweg rekonstruieren?"""
import csv, os, statistics as st
from collections import defaultdict

import sys

# Lauf-Ordner relativ zur Lage dieser Datei (<repo>/thesis/pruefung/).
# Ueberschreibbar per Argument: python3 <skript>.py <anderer-lauf-ordner>
ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "experiments", "20260820_005936")
TOP = ["flat", "hub_and_spoke", "dmz", "micro_segmented"]
ATT = ["chain", "flat", "hub_and_spoke", "dmz", "micro_segmented", "super"]
F = ["episode_reward", "def_block", "def_abwehr_reward", "atk_cj_reached",
     "atk_max_owned", "def_abgeschirmt"]


def z(x):
    if x in (None, ""):
        return None
    try:
        return float(x)
    except ValueError:
        return {"True": 1.0, "False": 0.0}.get(x)


roh = defaultdict(lambda: defaultdict(dict))
meta = {}
with open(os.path.join(ROOT, "combined_episodes.csv"), encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["phase"] != "defender_matrix":
            continue
        roh[r["run_id"]][r["agent"]][int(r["episode"])] = {k: z(r.get(k)) for k in F}
        meta[r["run_id"]] = (r["topology"], r["attacker_name"])

MIT, OHNE = {}, {}
for rid, ja in roh.items():
    for ag, eps in ja.items():
        ks = sorted(eps)
        MIT.setdefault(rid, {})[ag] = {k: [eps[e][k] for e in ks] for k in F}
        OHNE.setdefault(rid, {})[ag] = {k: [eps[e][k] for e in ks[:-1]] for k in F}

zellen = defaultdict(list)
for rid in roh:
    zellen[meta[rid]].append(rid)

print("=" * 76)
print("A) 'Sperren zu Beginn rund 580' - welcher Rechenweg ergibt 580?")
for name, wie in (("nur Episode 1", lambda v: v[0]),
                  ("Mittel Ep 1-5", lambda v: st.mean(v[:5])),
                  ("Mittel Ep 1-10", lambda v: st.mean(v[:10])),
                  ("Mittel Ep 1-25", lambda v: st.mean(v[:25]))):
    w = [wie([x for x in OHNE[rid]["defender"]["def_block"]]) for rid in roh]
    print("   %-16s ueber alle 120 Laeufe: %.0f" % (name, st.mean(w)))

print()
print("B) 'Abwehrbonus beginnt bei rund -30'")
for name, wie in (("nur Episode 1", lambda v: v[0]),
                  ("Mittel Ep 1-5", lambda v: st.mean(v[:5])),
                  ("Mittel Ep 1-10", lambda v: st.mean(v[:10]))):
    for t in TOP:
        w = [wie(OHNE[rid]["defender"]["def_abwehr_reward"])
             for a in ATT for rid in zellen[(t, a)]]
        print("   %-14s %-16s %.1f" % (name, t, st.mean(w)))
    print()

print("=" * 76)
print("C) '88,1 Prozent abgeschirmt' - mit letzter Episode statt ohne?")
for name, Q in (("ohne letzte Ep", OHNE), ("MIT letzter Ep", MIT)):
    ja = ges = 0
    for rid in Q:
        for x in Q[rid]["defender"]["def_abgeschirmt"]:
            if x is None:
                continue
            ges += 1
            ja += 1 if x > 0 else 0
    print("   %-16s %.1f %%  (n=%d)" % (name, 100.0 * ja / ges, ges))

print()
print("=" * 76)
print("D) 'CJ-Quote hs 26 / dmz 44' - anderes Fenster oder letzte Episode?")
for name, Q in (("ohne letzte Ep", OHNE), ("MIT letzter Ep", MIT)):
    for t in ("hub_and_spoke", "dmz", "micro_segmented"):
        rids = zellen[(t, t)]
        l20 = [x for rid in rids for x in Q[rid]["attacker"]["atk_cj_reached"][-20:]
               if x is not None]
        # letzter Punkt einer Fensterkurve ueber 11 Episoden
        n = min(len(Q[rid]["attacker"]["atk_cj_reached"]) for rid in rids)
        f11 = [Q[rid]["attacker"]["atk_cj_reached"][j]
               for rid in rids for j in range(n - 11, n)]
        print("   %-16s %-16s letzte20 %.1f %%   Fenster11 am Ende %.1f %%"
              % (name, t, 100.0 * st.mean(l20), 100.0 * st.mean(f11)))
    print()

print("=" * 76)
print("E) 'flat/flat Knoten sinkt von 8,7 auf 7,7'")
rids = zellen[("flat", "flat")]
for name, Q in (("ohne letzte Ep", OHNE), ("MIT letzter Ep", MIT)):
    n = min(len(Q[rid]["attacker"]["atk_max_owned"]) for rid in rids)
    m = [st.mean([Q[rid]["attacker"]["atk_max_owned"][i] for rid in rids])
         for i in range(n)]
    g = [st.mean(m[max(0, i - 2):i + 3]) for i in range(n)]
    print("   %-16s Ep1 %.1f  Max %.1f (Ep %d)  Ep250 %.1f  letzter Punkt %.1f"
          % (name, g[0], max(g), g.index(max(g)) + 1,
             g[249] if len(g) > 249 else float("nan"), g[-1]))
print("   Mittel der ersten 10 Episoden (ungeglaettet): %.1f"
      % st.mean([x for rid in rids for x in MIT[rid]["attacker"]["atk_max_owned"][:10]]))
print("   Median der ersten 10, je Seed dann Mittel: %.1f"
      % st.mean([st.median(MIT[rid]["attacker"]["atk_max_owned"][:10]) for rid in rids]))
