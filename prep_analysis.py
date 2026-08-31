#!/usr/bin/env python3
"""Vollstaendige Auswertung eines Matrix-Experiments in EINE analysis.json.

Loest die frueheren Einzelskripte (prep_partial_matrix / prep_attacker_matrix /
prep_boxplot_matrix / prep_mean_curves / prep_timeline*) ab, die alle dieselbe
CSV neu eingelesen und den Experiment-Ordner hartkodiert hatten.

Nutzung:
    python prep_analysis.py experiments/20260807_004059 [out.json]

Erzeugt je Matchup (Topologie x Angreifer):
  * defender/attacker : Median der letzten 20 Episoden je Seed, dann ueber Seeds
                        aggregiert (Median + Mittelwert + Standardabweichung)
  * box               : Verteilung ueber ALLE Episoden aller Seeds (min/Q1/Median/Q3/max)
  * curves            : Mittelwert-Lernkurve je Episode ueber alle Seeds (geglaettet),
                        fuer Defender und Attacker, plus Trend-Label
  * atkstats          : Crown-Jewel-Quote, Siegquote, Anteil ungueltiger Aktionen
  * convergence       : Anzahl Auto-Stops und mittlere Konvergenz-Episode
"""
import csv
import json
import os
import statistics
import sys
from collections import defaultdict

TOPOS = ["flat", "hub_and_spoke", "dmz", "micro_segmented"]
ATTACKERS = ["chain", "flat", "hub_and_spoke", "dmz", "micro_segmented", "super"]
TAIL = 20        # Episoden am Ende, die die "Endleistung" definieren
SMOOTH = 5       # Fenster fuer die geglaettete Lernkurve


def quantile(sorted_vals, q):
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0]
    idx = q * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (idx - lo)


def rolling(vals, w=SMOOTH):
    return [sum(vals[max(0, i - w + 1): i + 1]) / len(vals[max(0, i - w + 1): i + 1])
            for i in range(len(vals))]


def mean_over_seeds(seed_series):
    """Mittelwert je Episoden-Index, GEKUERZT auf die kuerzeste Seed-Laenge.

    Ohne Kuerzung wuerde das Kurvenende von immer weniger Seeds getragen und
    koennte einen Trend vortaeuschen, der nur von einem langlaufenden Seed stammt.
    """
    if not seed_series:
        return []
    n = min(len(s) for s in seed_series)
    return rolling([sum(s[i] for s in seed_series) / len(seed_series) for i in range(n)])


def trend_label(series):
    if len(series) < 10:
        return "?"
    k = max(1, len(series) // 5)
    delta = (sum(series[-k:]) / k) - (sum(series[:k]) / k)
    spread = (max(series) - min(series)) or 1
    if abs(delta) < 0.05 * spread:
        return "oszillierend"
    return "steigend" if delta > 0 else "fallend"


def main():
    if len(sys.argv) < 2:
        raise SystemExit(f"Nutzung: python {os.path.basename(__file__)} <experiment-dir> [out.json]")
    root = sys.argv[1].rstrip("/\\")
    out_path = sys.argv[2] if len(sys.argv) > 2 else "analysis.json"

    csv_path = os.path.join(root, "combined_episodes.csv")
    if not os.path.isfile(csv_path):
        raise SystemExit(f"Nicht gefunden: {csv_path}  (vorher aggregate_experiment.py laufen lassen)")

    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    dm = [r for r in rows if r["phase"] == "defender_matrix" and r["episode_reward"] not in ("", None)]

    # run_id -> Episodenliste, getrennt nach Agent
    runs = defaultdict(lambda: {"attacker": [], "defender": []})
    meta = {}
    for r in dm:
        runs[r["run_id"]][r["agent"]].append(r)
        meta[r["run_id"]] = (r["topology"], r["attacker_name"])
    for rid in runs:
        for ag in ("attacker", "defender"):
            runs[rid][ag].sort(key=lambda r: int(r["episode"]))

    # Matchup -> Liste von run_ids
    matchup_runs = defaultdict(list)
    for rid, (t, a) in meta.items():
        matchup_runs[(t, a)].append(rid)

    defender = {t: {} for t in TOPOS}
    attacker = {t: {} for t in TOPOS}
    box = {t: {} for t in TOPOS}
    curves = {}
    atkstats = {t: {} for t in TOPOS}
    convergence = {t: {} for t in TOPOS}

    autostop_total = 0
    for t in TOPOS:
        for a in ATTACKERS:
            rids = sorted(matchup_runs.get((t, a), []))
            if not rids:
                for d in (defender, attacker, box, atkstats, convergence):
                    d[t][a] = None
                continue

            def agg(agent):
                per_seed = []
                for rid in rids:
                    rew = [float(r["episode_reward"]) for r in runs[rid][agent]]
                    if rew:
                        per_seed.append(statistics.median(rew[-TAIL:] if len(rew) >= TAIL else rew))
                return per_seed

            for agent, target in (("defender", defender), ("attacker", attacker)):
                vals = agg(agent)
                target[t][a] = dict(
                    median=round(statistics.median(vals), 1),
                    mean=round(statistics.mean(vals), 1),
                    std=round(statistics.pstdev(vals), 1) if len(vals) > 1 else 0.0,
                    seeds=[round(v, 1) for v in vals],
                    n_seeds=len(vals),
                )

            # Verteilung ueber ALLE Episoden aller Seeds (Defender)
            allv = sorted(float(r["episode_reward"]) for rid in rids for r in runs[rid]["defender"])
            box[t][a] = dict(n=len(allv), min=allv[0], max=allv[-1],
                             q1=round(quantile(allv, 0.25), 1),
                             median=round(statistics.median(allv), 1),
                             q3=round(quantile(allv, 0.75), 1))

            # Mittelwert-Lernkurven
            dser = [[float(r["episode_reward"]) for r in runs[rid]["defender"]] for rid in rids]
            aser = [[float(r["episode_reward"]) for r in runs[rid]["attacker"]] for rid in rids]
            dmean = mean_over_seeds(dser)
            curves[f"{t}|{a}"] = dict(
                defender=[round(v, 1) for v in dmean],
                attacker=[round(v, 1) for v in mean_over_seeds(aser)],
                n_seeds=len(rids), trend=trend_label(dmean),
            )

            # Angreifer-Kennzahlen (nur Zeilen mit gefuellten Stats)
            arows = [r for rid in rids for r in runs[rid]["attacker"] if r.get("atk_valid") not in ("", None)]
            if arows:
                tv = sum(int(r["atk_valid"]) for r in arows)
                ti = sum(int(r["atk_invalid"]) for r in arows)
                atkstats[t][a] = dict(
                    n_ep=len(arows),
                    cj_pct=round(100 * sum(1 for r in arows if r["atk_cj_reached"] == "1") / len(arows), 1),
                    won_pct=round(100 * sum(1 for r in arows if r["atk_won"] == "1") / len(arows), 1),
                    invalid_pct=round(100 * ti / (tv + ti), 3) if (tv + ti) else 0.0,
                    max_owned=round(statistics.mean(int(r["atk_max_owned"]) for r in arows), 1),
                )
            else:
                atkstats[t][a] = None

            # Konvergenz: Auto-Stop = Lauf endete vor dem Step-Budget
            ep_counts, stops = [], 0
            for rid in rids:
                dfr = runs[rid]["defender"]
                ts = max(int(r["timestep"]) for r in dfr)
                if ts < 480_000:
                    stops += 1
                    ep_counts.append(len(dfr))
            autostop_total += stops
            convergence[t][a] = dict(
                autostop=stops, n_seeds=len(rids),
                mean_episodes=round(statistics.mean(ep_counts), 1) if ep_counts else None,
            )

    out = dict(
        meta=dict(experiment=os.path.basename(root), n_runs=len(runs),
                  n_matchups=sum(1 for t in TOPOS for a in ATTACKERS if defender[t][a]),
                  autostop=autostop_total,
                  autostop_pct=round(100 * autostop_total / len(runs), 1) if runs else 0,
                  tail=TAIL, smooth=SMOOTH),
        defender=defender, attacker=attacker, box=box, curves=curves,
        atkstats=atkstats, convergence=convergence,
    )
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f)

    print(f"{out['meta']['n_runs']} Laeufe, {out['meta']['n_matchups']}/24 Matchups, "
          f"Auto-Stop {autostop_total} ({out['meta']['autostop_pct']}%)  ->  {out_path}\n")
    print("Defender (Median letzte 20 Ep., ueber Seeds) / Attacker in Klammern:")
    for t in TOPOS:
        cells = []
        for a in ATTACKERS:
            d, atk = defender[t][a], attacker[t][a]
            cells.append(f"{a[:6]}:{d['median']:>8.0f}({atk['median']:>7.0f})" if d else f"{a[:6]}: --")
        print(f"  {t:16s} " + "  ".join(cells))


if __name__ == "__main__":
    main()
