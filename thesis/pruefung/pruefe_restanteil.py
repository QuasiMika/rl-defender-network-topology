# -*- coding: utf-8 -*-
"""Audit Teil 3: Restanteil exakt nach 3.9 (Median je Seed, Median ueber Seeds,
dann erst das Verhaeltnis), plus Restdetails."""
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


def zahl(x):
    if x in (None, ""):
        return None
    try:
        return float(x)
    except ValueError:
        return {"True": 1.0, "False": 0.0}.get(x)


# (topo, att, stufe, run_id) -> liste
seed_a = defaultdict(list)
seed_d = defaultdict(list)
laengen = defaultdict(list)
with open(os.path.join(ROOT, "evaluation_episodes.csv"), encoding="utf-8") as f:
    for r in csv.DictReader(f):
        k = (r["topology"], r["attacker_name"], r["stufe"], r["run_id"])
        if r["agent"] == "attacker":
            seed_a[k].append(zahl(r["episode_reward"]))
            laengen[r["stufe"]].append(zahl(r["episode_length"]))
        else:
            seed_d[k].append(zahl(r["episode_reward"]))


def zellwert(t, a, stufe, quelle):
    """Median je Seed, dann Median ueber die Seeds."""
    med = [st.median(v) for (tt, aa, ss, _), v in quelle.items()
           if (tt, aa, ss) == (t, a, stufe)]
    return st.median(med) if med else None


print("RESTANTEIL nach 3.9 (Median je Seed -> Median ueber Seeds -> Verhaeltnis)")
tr_alle, zu_alle, diff = [], [], defaultdict(list)
for t in TOP:
    z = []
    for a in ATT:
        k = zellwert(t, a, "keiner", seed_a)
        tr = 100.0 * zellwert(t, a, "trainiert", seed_a) / k
        zu = 100.0 * zellwert(t, a, "zufaellig", seed_a) / k
        z.append("%4.1f (%2.0f)" % (tr, zu))
        tr_alle.append(tr)
        zu_alle.append(zu)
        diff[t].append(zu - tr)
    print("%-16s %s" % (t, "  ".join(z)))
print("  trainiert %.1f bis %.1f | zufaellig %.0f bis %.0f | trainiert ueberall besser: %s"
      % (min(tr_alle), max(tr_alle), min(zu_alle), max(zu_alle),
         all(tr_alle[i] < zu_alle[i] for i in range(24))))
for t in TOP:
    print("  Abstand %-16s Mittel %.1f pp" % (t, st.mean(diff[t])))

print()
print("Episodenlaenge in der Evaluation (Median je Stufe):")
for s in ("trainiert", "zufaellig", "keiner"):
    print("  %-11s %.0f Schritte" % (s, st.median(laengen[s])))

print()
print("Bester (hoechster) Verteidiger-Einzelreward:")
best_ev = max(x for v in seed_d.values() for x in v)
print("  Evaluation, alle Stufen: %.1f" % best_ev)
best_tr = max(x for (t, a, s, r), v in seed_d.items() if s == "trainiert" for x in v)
print("  Evaluation, nur trainiert: %.1f" % best_tr)

beste = []
with open(os.path.join(ROOT, "combined_episodes.csv"), encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["agent"] != "defender" or r["phase"] != "defender_matrix":
            continue
        v = zahl(r["episode_reward"])
        if v is not None:
            beste.append((v, r["topology"], r["attacker_name"], int(r["episode"])))
beste.sort(reverse=True)
print("  Training, beste fuenf Episoden: %s"
      % ", ".join("%.1f (%s/%s Ep%d)" % b for b in beste[:5]))

print()
print("hs/hs: SLA-Bruchepisoden NACH Episode 50, je Seed")
roh = defaultdict(dict)
metar = {}
with open(os.path.join(ROOT, "combined_episodes.csv"), encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["phase"] != "defender_matrix" or r["agent"] != "defender":
            continue
        roh[r["run_id"]][int(r["episode"])] = (zahl(r["def_sla_break_steps"]),
                                               zahl(r["def_block"]),
                                               zahl(r["def_reimage"]),
                                               zahl(r["def_allow"]))
        metar[r["run_id"]] = (r["topology"], r["attacker_name"])

for zelle in (("hub_and_spoke", "hub_and_spoke"),):
    for rid, eps in roh.items():
        if metar[rid] != zelle:
            continue
        ks = sorted(eps)[:-1]
        spaet = [(e, eps[e]) for e in ks if e > 50 and eps[e][0]]
        if not spaet:
            print("  %s: keine nach Ep 50" % rid[-12:])
            continue
        print("  %s: %d Episoden, von Ep %d bis %d, max %d Bruchschritte"
              % (rid[-12:], len(spaet), spaet[0][0], spaet[-1][0],
                 max(x[1][0] for x in spaet)))
        print("     Episoden: %s" % [e for e, _ in spaet])
        ruhig = [e for e in ks if e > 50 and not eps[e][0]]
        print("     Sperren dort %s | ruhig-Median %.0f ; Reimages dort %s | ruhig %.0f"
              % (sorted(int(x[1][1]) for x in spaet)[-5:],
                 st.median([eps[e][1] for e in ruhig]),
                 sorted(int(x[1][2]) for x in spaet)[-3:],
                 st.median([eps[e][2] for e in ruhig])))
