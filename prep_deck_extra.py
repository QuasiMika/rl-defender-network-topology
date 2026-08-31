#!/usr/bin/env python3
"""Zusatzdaten fuer zwei Folien der Ergebnispraesentation.

1. Wirksamkeit: Was erreicht der Angreifer ohne Verteidiger, gegen einen
   Zufallsagenten und gegen das trainierte Modell? Quelle sind die
   evaluation_*.csv, in denen beide Agenten eingefroren nur noch spielen.

2. Gehaltene Knoten: Wie viele Knoten nimmt der Angreifer, und wie entwickelt
   sich das ueber das Training? Quelle sind die Trainings-Logs.

ZUR AGGREGATION (hier wurde zweimal falsch gerechnet, deshalb ausfuehrlich)
Nicht alle Episoden einer Topologie in einen Topf werfen. Die sechs Angreifer
erreichen voellig verschiedene Niveaus, in micro_segmented von 36 (chain) bis
638 (micro_segmented). Ein Median ueber den gemischten Topf springt zwischen
diesen Baendern hin und her und ist keine sinnvolle Kennzahl.

Stattdessen in drei Stufen:
  1. je Zelle (Stufe, Topologie, Angreifer, Seed) der Median ueber die
     Episoden,
  2. je Matchup der Median ueber die fuenf Seeds,
  3. je Matchup der Restanteil als Verhaeltnis zum ungeschuetzten Netz,
     erst danach ueber die sechs Angreifer gemittelt.

Schritt 3 normiert jedes Matchup an seiner eigenen Obergrenze. Ohne das
bestimmen die Angreifer mit hohem Niveau den Zeilenwert allein.

Aufruf:  python prep_deck_extra.py experiments/<lauf> [ausgabe.json]
"""
import csv
import glob
import json
import os
import re
import statistics
import sys

TOPOS = ["flat", "hub_and_spoke", "dmz", "micro_segmented"]
ATKS = ["chain", "flat", "hub_and_spoke", "dmz", "micro_segmented", "super"]
STUFEN = ["keiner", "zufaellig", "trainiert"]
BAENDER = [(1, 5), (6, 15), (16, 30), (31, 60), (61, 10 ** 9)]


def zahl(r, feld):
    try:
        return float(r[feld])
    except (KeyError, TypeError, ValueError):
        return None


def evaluation(root):
    dateien = sorted(glob.glob(os.path.join(root, "evaluation_*.csv")))
    if not dateien:
        return None

    reward, owned, cj = {}, {}, {}
    seeds = set()
    for pfad in dateien:
        with open(pfad, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r.get("agent") != "attacker":
                    continue
                m = re.search(r"seed\d+", r.get("run_id", "") or "")
                seed = m.group(0) if m else "seed?"
                seeds.add(seed)
                k = (r["stufe"], r["topology"], r["attacker_name"], seed)
                v = zahl(r, "episode_reward")
                if v is not None:
                    reward.setdefault(k, []).append(v)
                o = zahl(r, "atk_max_owned")
                if o is not None:
                    owned.setdefault(k, []).append(o)
                if r.get("atk_cj_reached") not in (None, ""):
                    cj.setdefault(k, []).append(r["atk_cj_reached"] == "1")

    def wert(quelle, stufe, topo, atk):
        """Schritt 1 und 2: Zellmedian, dann Median ueber die Seeds."""
        zellen = [statistics.median(v)
                  for (st, t, a, _s), v in quelle.items()
                  if st == stufe and t == topo and a == atk and v]
        return statistics.median(zellen) if zellen else None

    aus = {"seeds": sorted(seeds), "dateien": [os.path.basename(p) for p in dateien],
           "je_topologie": {}, "je_matchup": {}, "je_matchup_stufe": {},
           "je_matchup_knoten": {}, "je_matchup_cj": {}}

    for topo in TOPOS:
        aus["je_matchup"][topo] = {}
        aus["je_matchup_stufe"][topo] = {}
        aus["je_matchup_knoten"][topo] = {}
        aus["je_matchup_cj"][topo] = {}
        anteile = {st: [] for st in STUFEN}
        rewards = {st: [] for st in STUFEN}
        knoten = {st: [] for st in STUFEN}
        cjq = {st: [] for st in STUFEN}

        for atk in ATKS:
            werte = {st: wert(reward, st, topo, atk) for st in STUFEN}
            aus["je_matchup_stufe"][topo][atk] = {
                st: (round(werte[st], 1) if werte[st] is not None else None)
                for st in STUFEN
            }
            ohne = werte["keiner"]
            aus["je_matchup_knoten"][topo][atk] = {}
            aus["je_matchup_cj"][topo][atk] = {}
            for st in STUFEN:
                if werte[st] is not None:
                    rewards[st].append(werte[st])
                if ohne and werte[st] is not None:
                    anteile[st].append(100.0 * werte[st] / ohne)
                k = wert(owned, st, topo, atk)
                aus["je_matchup_knoten"][topo][atk][st] = (
                    round(k, 2) if k is not None else None)
                if k is not None:
                    knoten[st].append(k)
                treffer = [x for (s2, t2, a2, _s), v in cj.items()
                           if s2 == st and t2 == topo and a2 == atk for x in v]
                q = 100.0 * sum(treffer) / len(treffer) if treffer else None
                aus["je_matchup_cj"][topo][atk][st] = (
                    round(q, 1) if q is not None else None)
                if treffer:
                    cjq[st].append(q)

            aus["je_matchup"][topo][atk] = (
                round(100.0 * werte["trainiert"] / ohne, 1)
                if ohne and werte["trainiert"] is not None else None
            )

        eintrag = {}
        for st in STUFEN:
            eintrag[st] = {
                "reward": round(statistics.mean(rewards[st]), 1) if rewards[st] else None,
                "owned": round(statistics.mean(knoten[st]), 2) if knoten[st] else None,
                "cj_pct": round(statistics.mean(cjq[st]), 1) if cjq[st] else None,
                "restanteil": round(statistics.mean(anteile[st]), 1) if anteile[st] else None,
                "n_matchups": len(rewards[st]),
            }
        aus["je_topologie"][topo] = eintrag

    return aus


def verteidiger(root):
    """Was die jeweilige Verteidigerpolitik kostet.

    Der Restanteil misst nur die Angreiferseite. Fuer die Frage, ob ein
    Zufallsagent gleichwertig ist, braucht es die Gegenseite: Aktivitaet,
    Verfuegbarkeit und der eigene Reward.
    """
    dateien = sorted(glob.glob(os.path.join(root, "evaluation_*.csv")))
    if not dateien:
        return None

    rows = {}
    for pfad in dateien:
        with open(pfad, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r.get("agent") != "defender":
                    continue
                rows.setdefault((r["stufe"], r["topology"]), []).append(r)

    aus = {}
    for topo in TOPOS:
        aus[topo] = {}
        for st in ("zufaellig", "trainiert"):
            rs = rows.get((st, topo), [])
            if not rs:
                continue

            def med(feld):
                w = [zahl(r, feld) for r in rs]
                w = [x for x in w if x is not None]
                return round(statistics.median(w), 1) if w else None

            sla_ep = sum(1 for r in rs if (zahl(r, "def_sla_break_steps") or 0) > 0)
            aus[topo][st] = {
                "reward": med("episode_reward"),
                "reimage": med("def_reimage"),
                "stop_svc": med("def_stop_svc"),
                "stop_svc_clean": med("def_stop_svc_clean"),
                "block": med("def_block"),
                "sla_ep_pct": round(100.0 * sla_ep / len(rs), 1),
                "n": len(rs),
            }
    return aus


def knotenverlauf(root):
    """Gehaltene Knoten des Angreifers ueber die Trainingsepisoden."""
    je_band = {t: {} for t in TOPOS}
    je_matchup = {t: {} for t in TOPOS}
    laeufe_je_band = {t: {} for t in TOPOS}

    for pfad in glob.glob(os.path.join(root, "defenders", "*", "*", "seed*", "training_log_*.csv")):
        teile = pfad.split(os.sep)
        topo, atk = teile[-4], teile[-3].replace("vs_", "")
        if topo not in je_band:
            continue
        with open(pfad, newline="", encoding="utf-8") as fh:
            rows = [r for r in csv.DictReader(fh) if r.get("agent") == "attacker"]
        letzte_ep = max((int(r["episode"]) for r in rows if r.get("episode")), default=0)
        for lo, hi in BAENDER:
            if letzte_ep >= lo:
                laeufe_je_band[topo][(lo, hi)] = laeufe_je_band[topo].get((lo, hi), 0) + 1
        for r in rows:
            v = zahl(r, "atk_max_owned")
            if v is None:
                continue
            try:
                ep = int(r["episode"])
            except (KeyError, ValueError):
                continue
            for lo, hi in BAENDER:
                if lo <= ep <= hi:
                    je_band[topo].setdefault((lo, hi), []).append(v)
                    break
            je_matchup[topo].setdefault(atk, []).append(v)

    aus = {"baender": [], "je_topologie": {}, "je_matchup": {}, "n_laeufe": {}}
    for lo, hi in BAENDER:
        aus["baender"].append("%d-%d" % (lo, hi) if hi < 10 ** 9 else "ab %d" % lo)
    for topo in TOPOS:
        aus["je_topologie"][topo] = [
            round(statistics.median(je_band[topo][(lo, hi)]), 2)
            if je_band[topo].get((lo, hi)) else None
            for lo, hi in BAENDER
        ]
        aus["je_matchup"][topo] = {
            a: round(statistics.median(v), 2) for a, v in je_matchup[topo].items()
        }
        aus["n_laeufe"][topo] = [
            laeufe_je_band[topo].get((lo, hi), 0) for lo, hi in BAENDER
        ]
    return aus


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    root = sys.argv[1].rstrip("/\\")
    ziel = sys.argv[2] if len(sys.argv) > 2 else os.path.join(root, "deck_extra.json")

    daten = {"evaluation": evaluation(root), "knoten": knotenverlauf(root),
             "verteidiger": verteidiger(root)}
    with open(ziel, "w", encoding="utf-8") as fh:
        json.dump(daten, fh, indent=1, ensure_ascii=False)

    ev = daten["evaluation"]
    if ev:
        print("Evaluation aus %d Datei(en), Seeds: %s"
              % (len(ev["dateien"]), ", ".join(ev["seeds"])))
        print()
        print("  %-17s %8s %10s %10s %11s %11s"
              % ("Topologie", "ohne", "zufaellig", "trainiert", "Rest zuf.", "Rest trai."))
        for t in TOPOS:
            e = ev["je_topologie"][t]
            print("  %-17s %8.0f %10.0f %10.0f %10.1f%% %10.1f%%"
                  % (t, e["keiner"]["reward"], e["zufaellig"]["reward"],
                     e["trainiert"]["reward"], e["zufaellig"]["restanteil"],
                     e["trainiert"]["restanteil"]))
        print()
        print("  Gewinn durch Training gegenueber Zufall (Prozentpunkte):")
        for t in TOPOS:
            e = ev["je_topologie"][t]
            print("    %-17s %+6.1f"
                  % (t, e["zufaellig"]["restanteil"] - e["trainiert"]["restanteil"]))
    else:
        print("Keine evaluation_*.csv gefunden.")

    print()
    print("Gehaltene Knoten im Trainingsverlauf (Median):")
    print("  %-17s %s" % ("", "".join("%9s" % b for b in daten["knoten"]["baender"])))
    for t in TOPOS:
        werte = daten["knoten"]["je_topologie"][t]
        n = daten["knoten"]["n_laeufe"][t]
        print("  %-17s %s" % (t, "".join("%9s" % (w if w is not None else "-") for w in werte)))
        print("  %-17s %s" % ("  davon Laeufe", "".join("%9s" % x for x in n)))
    print()
    print("Geschrieben:", ziel)


if __name__ == "__main__":
    main()
