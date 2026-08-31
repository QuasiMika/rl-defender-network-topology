# -*- coding: utf-8 -*-
"""Audit Teil 1: jede nachrechenbare Zahl aus 4.1 bis 4.5 gegen die Rohdaten.

Konvention wie im Kapitel: je Seed der Median seiner ersten bzw. letzten zehn
Episoden, darueber das Mittel ueber die fuenf Seeds. Die LETZTE Episode jedes
Laufs wird immer verworfen.
"""
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
N = 10

FELD = ["episode_reward", "atk_cj_reached", "atk_max_owned", "atk_eviction",
        "def_reimage", "def_block", "def_allow", "def_invalid",
        "def_sla_break_steps", "def_abwehr_reward", "def_abgeschirmt",
        "episode_length", "atk_valid", "atk_invalid"]


def zahl(x):
    if x is None or x == "":
        return None
    try:
        return float(x)
    except ValueError:
        return {"True": 1.0, "False": 0.0}.get(x)


# run_id -> agent -> episode -> dict
roh = defaultdict(lambda: defaultdict(dict))
meta = {}
with open(os.path.join(ROOT, "combined_episodes.csv"), encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["phase"] != "defender_matrix":
            continue
        rid, ep = r["run_id"], int(r["episode"])
        roh[rid][r["agent"]][ep] = {k: zahl(r.get(k)) for k in FELD}
        meta[rid] = (r["topology"], r["attacker_name"])

# Reihen ohne letzte Episode
S = defaultdict(lambda: defaultdict(dict))   # rid -> agent -> feld -> liste
for rid, je_agent in roh.items():
    for agent, eps in je_agent.items():
        keys = sorted(eps)[:-1]
        for k in FELD:
            S[rid][agent][k] = [eps[e][k] for e in keys]

zellen = defaultdict(list)
for rid in S:
    zellen[meta[rid]].append(rid)


def stufe(zelle, agent, feld, wo):
    """Median je Seed ueber erste/letzte N, dann Mittel ueber Seeds."""
    w = []
    for rid in zellen[zelle]:
        v = [x for x in S[rid][agent][feld] if x is not None]
        if not v:
            continue
        w.append(st.median(v[:N] if wo == "start" else v[-N:]))
    return st.mean(w) if w else None


def p(t):
    print(t)


p("=" * 78)
p("4.1  TABELLE 4.1  Angreifer-Reward Start -> Ende")
p("=" * 78)
for t in TOP:
    z = []
    for a in ATT:
        s, e = stufe((t, a), "attacker", "episode_reward", "start"), \
               stufe((t, a), "attacker", "episode_reward", "ende")
        z.append("%5.0f->%4.0f" % (s, e))
    p("%-16s %s" % (t, "  ".join(z)))

p("")
p("4.1  TABELLE 4.2  Verteidiger-Reward Ende")
for t in TOP:
    p("%-16s %s" % (t, "  ".join("%7.0f" % stufe((t, a), "defender",
                                                 "episode_reward", "ende")
                                 for a in ATT)))

p("")
p("Verteidiger-Reward Start (fuer -8381 flat/flat und -25800 / -8700):")
for t in TOP:
    p("%-16s %s" % (t, "  ".join("%8.0f" % stufe((t, a), "defender",
                                                 "episode_reward", "start")
                                 for a in ATT)))

p("")
p("Steigt der Verteidiger-Reward in ALLEN 120 Laeufen? (Ende > Start je Lauf)")
schlecht = []
for rid in S:
    v = [x for x in S[rid]["defender"]["episode_reward"] if x is not None]
    if st.median(v[-N:]) <= st.median(v[:N]):
        schlecht.append((meta[rid], rid))
p("  Laeufe ohne Verbesserung: %d %s" % (len(schlecht), schlecht[:3]))

p("")
p("Restanteil Ende/Start des Angreifer-Rewards in Prozent:")
diag_q, off_q = [], []
for t in TOP:
    z = []
    for a in ATT:
        q = 100.0 * stufe((t, a), "attacker", "episode_reward", "ende") \
            / stufe((t, a), "attacker", "episode_reward", "start")
        z.append("%5.1f" % q)
        (diag_q if a == t else off_q).append(q)
    p("%-16s %s" % (t, "  ".join(z)))
p("  Diagonale : %.1f bis %.1f" % (min(diag_q), max(diag_q)))
p("  uebrige   : %.1f bis %.1f   Mittel %.1f  Median %.1f"
  % (min(off_q), max(off_q), st.mean(off_q), st.median(off_q)))

p("")
p("Episodenzahl je Zelle (min-max ueber die 5 Seeds, ohne letzte Episode):")
for t in TOP:
    z = []
    for a in ATT:
        laengen = [len(S[rid]["defender"]["episode_reward"]) for rid in zellen[(t, a)]]
        z.append("%3d-%3d" % (min(laengen), max(laengen)))
    p("%-16s %s" % (t, "  ".join(z)))

p("")
p("Startwert-Rangfolge Angreifer je Zeile (Faktor Diagonale / Zweitbester):")
for t in TOP:
    paare = sorted(((stufe((t, a), "attacker", "episode_reward", "start"), a)
                    for a in ATT), reverse=True)
    p("%-16s  1. %s %.0f   2. %s %.0f   Faktor %.2f"
      % (t, paare[0][1], paare[0][0], paare[1][1], paare[1][0],
         paare[0][0] / paare[1][0]))

p("")
p("=" * 78)
p("4.2  CROWN-JEWEL-QUOTE")
p("=" * 78)
for t in TOP:
    rids = zellen[(t, t)]
    alle = [x for rid in rids for x in S[rid]["attacker"]["atk_cj_reached"]
            if x is not None]
    letzte20 = [x for rid in rids
                for x in S[rid]["attacker"]["atk_cj_reached"][-20:] if x is not None]
    p("%-16s Episoden %4d   CJ erreicht %4d   ohne CJ %d   letzte 20 Ep: %.1f %%"
      % (t, len(alle), int(sum(alle)), int(len(alle) - sum(alle)),
         100.0 * st.mean(letzte20)))

p("")
p("micro_segmented Quote im Fenster um Episode 150 und 230 (11 Ep, 5 Seeds):")


def fenster_quote(zelle, mitte, breite=11):
    h = breite // 2
    v = []
    for rid in zellen[zelle]:
        r = S[rid]["attacker"]["atk_cj_reached"]
        v += [x for x in r[max(0, mitte - 1 - h):mitte + h] if x is not None]
    return 100.0 * st.mean(v) if v else None


for mitte in (150, 190, 230):
    p("  micro Episode %3d: %.1f %%" % (mitte, fenster_quote(("micro_segmented",
                                                             "micro_segmented"), mitte)))
for mitte in (55, 100, 145, 190):
    p("  dmz   Episode %3d: %.1f %%" % (mitte, fenster_quote(("dmz", "dmz"), mitte)))
for mitte in (150, 190, 230):
    p("  flat  Episode %3d: %.1f %%" % (mitte, fenster_quote(("flat", "flat"), mitte)))

p("")
p("dmz/dmz: CJ-Quote je Seed ueber Episoden 150-250, und Reward-Median dazu:")
paare = []
for rid in zellen[("dmz", "dmz")]:
    cj = [x for x in S[rid]["attacker"]["atk_cj_reached"][149:250] if x is not None]
    rw = [x for x in S[rid]["attacker"]["episode_reward"][149:250] if x is not None]
    paare.append((100.0 * st.mean(cj), st.median(rw)))
for q, r in sorted(paare):
    p("   Quote %5.1f %%   Reward-Median %6.0f" % (q, r))

p("")
p("dmz/dmz: Eviction und Reward, Episoden MIT gegen OHNE CJ (Median):")
mit_e, ohne_e, mit_r, ohne_r = [], [], [], []
for rid in zellen[("dmz", "dmz")]:
    cj = S[rid]["attacker"]["atk_cj_reached"]
    ev = S[rid]["attacker"]["atk_eviction"]
    rw = S[rid]["attacker"]["episode_reward"]
    for i in range(len(cj)):
        if cj[i] is None:
            continue
        (mit_e if cj[i] else ohne_e).append(ev[i])
        (mit_r if cj[i] else ohne_r).append(rw[i])
p("   mit CJ : Eviction %6.0f  Reward %5.0f   (n=%d)"
  % (st.median(mit_e), st.median(mit_r), len(mit_r)))
p("   ohne CJ: Eviction %6.0f  Reward %5.0f   (n=%d)"
  % (st.median(ohne_e), st.median(ohne_r), len(ohne_r)))

p("")
p("=" * 78)
p("4.3  GEHALTENE KNOTEN  (max gleichzeitig, Mittel letzte 10 Ep ueber Seeds)")
p("=" * 78)
werte = {}
for t in TOP:
    z = []
    for a in ATT:
        v = stufe((t, a), "attacker", "atk_max_owned", "ende")
        werte[(t, a)] = v
        z.append("%4.1f" % v)
    p("%-16s %s" % (t, "  ".join(z)))
inn = [v for k, v in werte.items() if 1.8 <= v <= 2.5]
aus = sorted(((v, k) for k, v in werte.items() if not (1.8 <= v <= 2.5)), reverse=True)
p("  in 1,8-2,5: %d von 24    ausserhalb: %s"
  % (len(inn), ", ".join("%s/%s %.1f" % (k[0], k[1], v) for v, k in aus)))

p("")
p("Diagonale: Maximum der geglaetteten Kurve und Start/Ende:")
for t in TOP:
    rids = zellen[(t, t)]
    laenge = min(len(S[rid]["attacker"]["atk_max_owned"]) for rid in rids)
    kurve = [st.mean([S[rid]["attacker"]["atk_max_owned"][i] for rid in rids])
             for i in range(laenge)]
    g = [st.mean(kurve[max(0, i - 2):i + 3]) for i in range(laenge)]
    p("%-16s Start %.1f   Max %.1f (Ep %d)   Ende %.1f"
      % (t, g[0], max(g), g.index(max(g)) + 1, g[-1]))

p("")
p("=" * 78)
p("4.5  AKTIONSVERHALTEN")
p("=" * 78)
p("Sperren und Reimages je Episode, Mittel letzte 10 Ep ueber alle 30 Laeufe:")
for t in TOP:
    sp, ri, ab = [], [], []
    for a in ATT:
        for rid in zellen[(t, a)]:
            sp.append(st.mean([x for x in S[rid]["defender"]["def_block"][-N:]]))
            ri.append(st.mean([x for x in S[rid]["defender"]["def_reimage"][-N:]]))
            ab.append(st.mean([x for x in S[rid]["defender"]["def_abwehr_reward"][-N:]]))
    p("%-16s Sperren %6.1f   Reimages %6.1f   Abwehrbonus %7.2f"
      % (t, st.mean(sp), st.mean(ri), st.mean(ab)))
p("")
p("dieselben Groessen am Anfang (erste 10 Episoden):")
for t in TOP:
    sp, ri, ab = [], [], []
    for a in ATT:
        for rid in zellen[(t, a)]:
            sp.append(st.mean([x for x in S[rid]["defender"]["def_block"][:N]]))
            ri.append(st.mean([x for x in S[rid]["defender"]["def_reimage"][:N]]))
            ab.append(st.mean([x for x in S[rid]["defender"]["def_abwehr_reward"][:N]]))
    p("%-16s Sperren %6.1f   Reimages %6.1f   Abwehrbonus %7.2f"
      % (t, st.mean(sp), st.mean(ri), st.mean(ab)))

p("")
p("Aktionsanteile ueber ALLE 120 Laeufe (Summen, ohne letzte Episode):")


def anteile(bereich):
    s = defaultdict(float)
    for rid in S:
        d = S[rid]["defender"]
        idx = range(len(d["def_block"]))
        if bereich == "erste25":
            idx = range(min(25, len(d["def_block"])))
        elif bereich == "ab101":
            idx = range(100, len(d["def_block"]))
        for k in ("def_block", "def_reimage", "def_allow", "def_invalid"):
            s[k] += sum(d[k][i] for i in idx if d[k][i] is not None)
    ges = sum(s.values())
    return {k: 100.0 * v / ges for k, v in s.items()}, ges


for b in ("erste25", "ab101", "alle"):
    a, ges = anteile(b)
    p("  %-8s  Sperren %5.1f %%   Reimages %5.1f %%   Freigaben %5.1f %%   ungueltig %5.1f %%   (n=%.0f)"
      % (b, a["def_block"], a["def_reimage"], a["def_allow"], a["def_invalid"], ges))

p("")
p("Anteil Episoden mit durchgehend >= 1 abgeschirmtem Knoten:")
ja = ges = 0
for rid in S:
    for x in S[rid]["defender"]["def_abgeschirmt"]:
        if x is None:
            continue
        ges += 1
        ja += 1 if x > 0 else 0
p("  %.1f %% von %d Episoden   (Spalte def_abgeschirmt > 0)" % (100.0 * ja / ges, ges))
