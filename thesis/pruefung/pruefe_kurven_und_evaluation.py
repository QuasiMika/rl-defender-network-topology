# -*- coding: utf-8 -*-
"""Audit Teil 2: Kurvenwerte in 4.1, die SLA-Anomalien, 4.4 und die Evaluation."""
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
FELD = ["episode_reward", "atk_cj_reached", "atk_max_owned", "atk_eviction",
        "def_reimage", "def_block", "def_allow", "def_sla_break_steps",
        "episode_length"]


def zahl(x):
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
        roh[r["run_id"]][r["agent"]][int(r["episode"])] = {k: zahl(r.get(k)) for k in FELD}
        meta[r["run_id"]] = (r["topology"], r["attacker_name"])

S = defaultdict(lambda: defaultdict(dict))
for rid, ja in roh.items():
    for ag, eps in ja.items():
        ks = sorted(eps)[:-1]
        for k in FELD:
            S[rid][ag][k] = [eps[e][k] for e in ks]

zellen = defaultdict(list)
for rid in S:
    zellen[meta[rid]].append(rid)


def kurve(zelle, agent, feld, w=5):
    rids = zellen[zelle]
    n = min(len(S[rid][agent][feld]) for rid in rids)
    m = [st.mean([S[rid][agent][feld][i] for rid in rids]) for i in range(n)]
    h = w // 2
    return [st.mean(m[max(0, i - h):min(n, i + h + 1)]) for i in range(n)]


def bei(k, ep):
    return k[ep - 1] if 1 <= ep <= len(k) else None


print("=" * 78)
print("4.1 GEGLAETTETE KURVENWERTE (Mittel ueber 5 Seeds, Fenster 5)")
print("=" * 78)
kf = kurve(("flat", "flat"), "defender", "episode_reward")
print("flat/flat Verteidiger : Start %.0f  Ende %.0f" % (kf[0], kf[-1]))
print("flat uebrige Zellen Ende:",
      ", ".join("%s %.0f" % (a, kurve(("flat", a), "defender", "episode_reward")[-1])
                for a in ATT if a != "flat"))
kh = kurve(("hub_and_spoke", "hub_and_spoke"), "attacker", "episode_reward")
khd = kurve(("hub_and_spoke", "hub_and_spoke"), "defender", "episode_reward")
print("hs/hs Angreifer       : Start %.0f  Max %.0f (Ep %d)  Ende %.0f"
      % (kh[0], max(kh), kh.index(max(kh)) + 1, kh[-1]))
print("hs/hs Verteidiger     : Start %.0f  Ende %.0f" % (khd[0], khd[-1]))
print("hs uebrige Zellen Angreifer-Ende:",
      ", ".join("%s %.0f" % (a, kurve(("hub_and_spoke", a), "attacker", "episode_reward")[-1])
                for a in ATT if a != "hub_and_spoke"))
kd = kurve(("dmz", "dmz"), "attacker", "episode_reward")
kdd = kurve(("dmz", "dmz"), "defender", "episode_reward")
print("dmz/dmz Angreifer     : " + "  ".join("Ep%d %.0f" % (e, bei(kd, e))
                                             for e in (1, 25, 75, 100, 110, 250)))
print("dmz/dmz Verteidiger   : " + "  ".join("Ep%d %.0f" % (e, bei(kdd, e))
                                             for e in (1, 50, 250)))
km = kurve(("micro_segmented", "micro_segmented"), "attacker", "episode_reward")
kmd = kurve(("micro_segmented", "micro_segmented"), "defender", "episode_reward")
print("micro/micro Angreifer : " + "  ".join("Ep%d %.0f" % (e, bei(km, e))
                                             for e in (1, 25, 50, 250)))
print("micro/micro Verteidig.: " + "  ".join("Ep%d %.0f" % (e, bei(kmd, e))
                                             for e in (1, 250)))
print("schlechtester Startwert je Topologie (geglaettete Verteidigerkurve, Ep 1):")
for t in TOP:
    v = [(kurve((t, a), "defender", "episode_reward")[0], a) for a in ATT]
    print("   %-16s %.0f  (%s)" % (t, min(v)[0], min(v)[1]))

print()
print("=" * 78)
print("4.1 SLA-ANOMALIEN")
print("=" * 78)
for zelle, name in ((("hub_and_spoke", "hub_and_spoke"), "hs/hs"),
                    (("hub_and_spoke", "micro_segmented"), "hs/micro")):
    print(name)
    for rid in zellen[zelle]:
        b = S[rid]["defender"]["def_sla_break_steps"]
        heftig = [(i + 1, int(b[i])) for i in range(len(b)) if b[i] and b[i] > 100]
        if heftig:
            print("   %s: %d Episoden mit >100 Bruchschritten, max %d in Ep %d"
                  % (rid[-12:], len(heftig), max(x[1] for x in heftig),
                     max(heftig, key=lambda x: x[1])[0]))
            spanne = [e for e, _ in heftig]
            print("      Episoden: %s" % (spanne if len(spanne) < 20 else
                                          "%d bis %d (%d Stueck)" % (min(spanne), max(spanne), len(spanne))))
        else:
            print("   %s: keine" % rid[-12:])

print()
print("Extremste Episode hs/micro: Vergleich mit ruhiger Episode desselben Laufs")
for rid in zellen[("hub_and_spoke", "micro_segmented")]:
    d = S[rid]["defender"]
    b = d["def_sla_break_steps"]
    if not any(x and x > 500 for x in b):
        continue
    i = max(range(len(b)), key=lambda k: b[k] or 0)
    ruhig = [k for k in range(len(b)) if (b[k] or 0) == 0 and k > 50]
    print("   Lauf %s  Episode %d: Bruchschritte %d von %d Schritten"
          % (rid[-12:], i + 1, b[i], d["episode_length"][i]))
    print("      dort   : Reimages %.0f  Sperren %.0f  Freigaben %.0f"
          % (d["def_reimage"][i], d["def_block"][i], d["def_allow"][i]))
    print("      ruhige : Reimages %.0f  Sperren %.0f  Freigaben %.0f  (Median ueber %d)"
          % (st.median([d["def_reimage"][k] for k in ruhig]),
             st.median([d["def_block"][k] for k in ruhig]),
             st.median([d["def_allow"][k] for k in ruhig]), len(ruhig)))
    print("      Reward dort %.0f   Median ruhig %.0f"
          % (S[rid]["defender"]["episode_reward"][i],
             st.median([S[rid]["defender"]["episode_reward"][k] for k in ruhig])))

print()
print("Sperren in den Bruch-Episoden von hs/hs (>100 Bruchschritte) vs ruhig:")
for rid in zellen[("hub_and_spoke", "hub_and_spoke")]:
    d = S[rid]["defender"]
    b = d["def_sla_break_steps"]
    heftig = [i for i in range(len(b)) if b[i] and b[i] > 100]
    if not heftig:
        continue
    ruhig = [i for i in range(len(b)) if (b[i] or 0) == 0 and i > 50]
    print("   %s  Sperren in Bruchepisoden: %s   ruhig-Median %.0f   Reimages %s / ruhig %.0f"
          % (rid[-12:],
             sorted(int(d["def_block"][i]) for i in heftig)[-6:],
             st.median([d["def_block"][i] for i in ruhig]),
             sorted(int(d["def_reimage"][i]) for i in heftig)[-3:],
             st.median([d["def_reimage"][i] for i in ruhig])))

print()
print("schlechtester Verteidiger-Einzelreward ueber alle 120 Laeufe:")
alle = [(min(x for x in S[rid]["defender"]["episode_reward"] if x is not None), meta[rid])
        for rid in S]
print("   %.0f in %s" % min(alle))
ruhige = [x for rid in S for x in S[rid]["defender"]["episode_reward"][-50:]]
print("   Median der letzten 50 Episoden aller Laeufe: %.0f" % st.median(ruhige))

print()
print("=" * 78)
print("4.2 dmz/dmz Eviction/Reward, verschiedene Fenster")
print("=" * 78)
for lo, hi, name in ((0, 10**9, "alle Episoden"), (149, 250, "Ep 150-250"),
                     (99, 10**9, "ab Ep 100")):
    me, oe, mr, orw = [], [], [], []
    for rid in zellen[("dmz", "dmz")]:
        a = S[rid]["attacker"]
        for i in range(len(a["atk_cj_reached"])):
            if not (lo <= i < hi) or a["atk_cj_reached"][i] is None:
                continue
            (me if a["atk_cj_reached"][i] else oe).append(a["atk_eviction"][i])
            (mr if a["atk_cj_reached"][i] else orw).append(a["episode_reward"][i])
    print("   %-14s mit CJ: Evict %6.0f Reward %5.0f (n=%4d) | ohne: Evict %6.0f Reward %5.0f (n=%4d)"
          % (name, st.median(me), st.median(mr), len(mr),
             st.median(oe), st.median(orw), len(orw)))

print()
print("dmz/dmz CJ-Quote: Tiefstwert der Fensterkurve (11 Ep, 5 Seeds)")
rids = zellen[("dmz", "dmz")]
n = min(len(S[rid]["attacker"]["atk_cj_reached"]) for rid in rids)
q = []
for i in range(n):
    v = [S[rid]["attacker"]["atk_cj_reached"][j]
         for rid in rids for j in range(max(0, i - 5), min(n, i + 6))]
    q.append(100.0 * st.mean(v))
print("   Minimum %.1f %% in Episode %d" % (min(q), q.index(min(q)) + 1))
print("   ab Episode 150: min %.1f  max %.1f" % (min(q[149:]), max(q[149:])))
print("   Ep 100: %.1f   Ep 55: %.1f" % (q[99], q[54]))

print()
print("=" * 78)
print("EVALUATION 4.6 bis 4.8")
print("=" * 78)
ev = defaultdict(lambda: defaultdict(list))
with open(os.path.join(ROOT, "evaluation_episodes.csv"), encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["agent"] != "attacker":
            continue
        k = (r["topology"], r["attacker_name"], r["stufe"])
        ev[k]["reward"].append(zahl(r["episode_reward"]))
        ev[k]["cj"].append(zahl(r["atk_cj_reached"]))
        ev[k]["owned"].append(zahl(r["atk_max_owned"]))

print("Restanteil trainiert (Zufall) in Prozent, Median-basiert:")
rest_tr, rest_zu, diffs = [], [], defaultdict(list)
for t in TOP:
    z = []
    for a in ATT:
        keiner = st.median(ev[(t, a, "keiner")]["reward"])
        tr = 100.0 * st.median(ev[(t, a, "trainiert")]["reward"]) / keiner
        zu = 100.0 * st.median(ev[(t, a, "zufaellig")]["reward"]) / keiner
        z.append("%4.1f (%2.0f)" % (tr, zu))
        rest_tr.append(tr)
        rest_zu.append(zu)
        diffs[t].append(zu - tr)
    print("%-16s %s" % (t, "  ".join(z)))
print("   trainiert %.1f bis %.1f   zufaellig %.0f bis %.0f   trainiert immer besser: %s"
      % (min(rest_tr), max(rest_tr), min(rest_zu), max(rest_zu),
         all(rest_tr[i] < rest_zu[i] for i in range(24))))
for t in TOP:
    print("   mittlerer Abstand %-16s %.1f Prozentpunkte" % (t, st.mean(diffs[t])))

print()
print("Crown-Jewel-Quote trainiert, in Prozent:")
for t in TOP:
    print("%-16s %s" % (t, "  ".join("%5.1f" % (100.0 * st.mean(ev[(t, a, "trainiert")]["cj"]))
                                     for a in ATT)))
print()
print("Gehaltene Knoten, Median je Zelle:")
for stufe_ in ("trainiert", "zufaellig", "keiner"):
    w = [st.median(ev[(t, a, stufe_)]["owned"]) for t in TOP for a in ATT]
    print("   %-11s Median ueber alle %.1f   Spanne %.0f bis %.0f"
          % (stufe_, st.median(w), min(w), max(w)))
print("   flat/flat trainiert: %.1f" % st.median(ev[("flat", "flat", "trainiert")]["owned"]))

print()
print("Aufwand je Evaluationsepisode (Mediane), Verteidigerzeilen:")
kost = defaultdict(lambda: defaultdict(list))
with open(os.path.join(ROOT, "evaluation_episodes.csv"), encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["agent"] != "defender":
            continue
        k = (r["topology"], r["stufe"])
        kost[k]["block"].append(zahl(r["def_block"]))
        kost[k]["reimage"].append(zahl(r["def_reimage"]))
        kost[k]["sla"].append(1.0 if zahl(r["def_sla_break_steps"]) else 0.0)
        kost[k]["reward"].append(zahl(r["episode_reward"]))
for t in TOP:
    a, b = kost[(t, "trainiert")], kost[(t, "zufaellig")]
    print("%-16s Sperren %5.0f (%3.0f)  Reimages %5.1f (%4.1f)  SLA %5.1f%% (%5.1f%%)  Reward %6.0f (%6.0f)"
          % (t, st.median(a["block"]), st.median(b["block"]),
             st.median(a["reimage"]), st.median(b["reimage"]),
             100.0 * st.mean(a["sla"]), 100.0 * st.mean(b["sla"]),
             st.median(a["reward"]), st.median(b["reward"])))
print()
bester = max(x for t in TOP for x in kost[(t, "trainiert")]["reward"])
print("bester Verteidiger-Einzelreward in der Evaluation: %.1f" % bester)
