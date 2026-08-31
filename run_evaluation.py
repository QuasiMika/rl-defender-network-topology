#!/usr/bin/env python3
"""
Wirksamkeits-Evaluation der trainierten Verteidiger.

ABGRENZUNG ZUM TRAINING
Das Training beantwortet, wie SCHNELL ein Verteidiger stabil wird
(Konvergenz). Hier wird beantwortet, ob die gelernte Policy ueberhaupt etwas
NUETZT. Dafuer werden beide Agenten eingefroren und nur noch gespielt; es wird
nichts gelernt.

STUFEN
  keiner     kein Verteidiger        -> Obergrenze: wie weit kommt der
                                        Angreifer ungehindert?
  zufaellig  RandomMarlonAgent       -> reicht schon irgendein Handeln?
  trainiert  das PPO-Modell des Laufs

Die Angreifermodelle stammen in ALLEN Stufen aus demselben Lauf-Ordner wie das
Verteidigermodell. Damit ist sichergestellt, dass jede Stufe gegen exakt
denselben eingefrorenen Angreifer antritt.

AUSGABE
Eine CSV im GLEICHEN Schema wie combined_episodes.csv, zusaetzlich mit der
Spalte 'stufe'. Dadurch laufen prep_analysis.py und prep_curves.py ohne
Aenderung darueber.

Aufruf:
    python run_evaluation.py experiments/<lauf> [--episodes 25] [--workers 7]
    python run_evaluation.py experiments/<lauf> --dry-run
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
import sys
import traceback
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "MARLon"))
# CyberBattleSim liegt als Unterordner im Repo (siehe experiment_matrix_lib.py).
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "CyberBattleSim"))

STUFEN = ["keiner", "zufaellig", "trainiert"]

BASE_FIELDS = ["phase", "stufe", "topology", "attacker_name", "defender_algo",
               "run_id", "episode", "agent", "env_id", "algorithm",
               "timestep", "episode_reward", "episode_length"]
ATK_FIELDS = ["atk_invalid", "atk_valid", "atk_cj_reached", "atk_cj_step",
              "atk_won", "atk_max_owned", "atk_hold_reward", "atk_eviction"]
DEF_FIELDS = ["def_reimage", "def_block", "def_allow", "def_stop_svc",
              "def_stop_svc_clean", "def_start_svc", "def_invalid",
              "def_recovered", "def_sla_break_steps"]
FIELDNAMES = BASE_FIELDS + ATK_FIELDS + DEF_FIELDS


def finde_laeufe(root):
    """Alle Verteidiger-Laeufe: (topologie, angreifer, seed, atk_zip, def_zip)."""
    treffer = []
    muster = os.path.join(root, "defenders", "*", "vs_*", "seed*")
    for ordner in sorted(glob.glob(muster)):
        if not os.path.exists(os.path.join(ordner, "_DONE")):
            continue
        atk = glob.glob(os.path.join(ordner, "ppo_attacker_*.zip"))
        dfd = glob.glob(os.path.join(ordner, "ppo_defender_*.zip"))
        if not atk or not dfd:
            continue
        teile = ordner.replace("\\", "/").split("/")
        treffer.append({
            "topology": teile[-3],
            "attacker_name": teile[-2][len("vs_"):],
            "seed": teile[-1],
            "attacker_zip": atk[0],
            "defender_zip": dfd[0],
        })
    return treffer


def eine_zelle(auftrag):
    """Evaluiert eine Kombination aus Stufe und Lauf. Gibt CSV-Zeilen zurueck."""
    # WICHTIG bei --workers > 1: Torch startet je Prozess standardmaessig so
    # viele Threads, wie Kerne da sind (hier 8). Sieben Worker ergaeben 56
    # Threads auf 8 physischen Kernen -- die Prozesse blockieren sich
    # gegenseitig. Gemessen: 15,5 s je Episode statt 5 s. Ein Thread je Worker
    # ist bei dieser Last die richtige Einstellung.
    import torch
    torch.set_num_threads(1)

    from thesis_topology.envs import register_all, ENV_IDS
    register_all()

    from stable_baselines3 import PPO
    from stable_baselines3.common.utils import set_random_seed
    from marlon.baseline_models.multiagent import marl_algorithm
    from marlon.baseline_models.multiagent.multiagent_universe import MultiAgentUniverse
    from marlon.baseline_models.multiagent.baseline_marlon_agent import (
        FrozenAgentBuilder, MaskableFrozenAgentBuilder,
    )
    from marlon.baseline_models.multiagent.random_marlon_agent import RandomAgentBuilder

    lauf = auftrag["lauf"]
    stufe = auftrag["stufe"]
    episoden = auftrag["episodes"]
    episode_steps = auftrag["episode_steps"]

    seed_nr = int("".join(c for c in lauf["seed"] if c.isdigit()) or 0)
    # Stufen-Offset, damit die drei Stufen nicht dieselbe Zufallsfolge ziehen.
    set_random_seed(seed_nr + 1000 * STUFEN.index(stufe))

    env_id = ENV_IDS[lauf["topology"]]

    if stufe == "keiner":
        defender_builder = None
    elif stufe == "zufaellig":
        defender_builder = RandomAgentBuilder()
    else:
        defender_builder = FrozenAgentBuilder(alg_type=PPO,
                                              file_path=lauf["defender_zip"])

    universe = MultiAgentUniverse.build(
        attacker_builder=MaskableFrozenAgentBuilder(file_path=lauf["attacker_zip"]),
        defender_builder=defender_builder,
        attacker_invalid_action_reward_modifier=0,
        defender_invalid_action_reward_modifier=0,
        env_id=env_id,
        max_timesteps=episode_steps,
        defender_reset_on_constraint_broken=False,
        attacker_use_masking=True,
    )

    run_id = "eval_%s_%s_%s_%s" % (stufe, lauf["topology"],
                                   lauf["attacker_name"], lauf["seed"])
    atk_wrapper = universe.attacker_agent.wrapper
    def_wrapper = universe.defender_agent.wrapper if universe.defender_agent else None

    def stats_der_episode(wrapper, vorher):
        """
        Aktionsstatistik der gerade beendeten Episode.

        Der Wrapper haengt seinen Snapshot nur an episode_stats_log an, wenn er
        selbst done meldet. run_episode bricht aber schon bei max_steps ab, also
        eine Runde FRUEHER -- bei Episoden, die ins Schrittlimit laufen, waere
        das Log sonst leer. In dem Fall wird der laufende Zaehler _ep_stats
        gelesen, der bis zum naechsten reset() erhalten bleibt.
        """
        log = getattr(wrapper, "episode_stats_log", [])
        if len(log) > vorher:
            return dict(log[-1])
        return dict(getattr(wrapper, "_ep_stats", {}) or {})

    zeilen = []
    schritte_gesamt = 0
    for i in range(episoden):
        atk_log_vorher = len(getattr(atk_wrapper, "episode_stats_log", []))
        def_log_vorher = (len(getattr(def_wrapper, "episode_stats_log", []))
                          if def_wrapper is not None else 0)
        # run_episode liefert (atk_rewards, def_rewards, simulation,
        # attacker_log, defender_log) -- der Docstring nennt nur vier Werte.
        ergebnis = marl_algorithm.run_episode(
            attacker_agent=universe.attacker_agent,
            defender_agent=universe.defender_agent,
            max_steps=episode_steps,
        )
        atk_rew, def_rew = ergebnis[0], ergebnis[1]
        schritte_gesamt += len(atk_rew)

        gemeinsam = {
            "phase": "evaluation",
            "stufe": stufe,
            "topology": lauf["topology"],
            "attacker_name": lauf["attacker_name"],
            "defender_algo": {"keiner": "None", "zufaellig": "Random",
                              "trainiert": "PPO"}[stufe],
            "run_id": run_id,
            "episode": i + 1,
            "env_id": env_id,
            "timestep": schritte_gesamt,
        }

        zeilen.append({**gemeinsam, "agent": "attacker", "algorithm": "MaskablePPO",
                       "episode_reward": round(sum(atk_rew), 4),
                       "episode_length": len(atk_rew),
                       **stats_der_episode(atk_wrapper, atk_log_vorher)})

        if def_wrapper is not None:
            zeilen.append({**gemeinsam, "agent": "defender",
                           "algorithm": gemeinsam["defender_algo"],
                           "episode_reward": round(sum(def_rew), 4),
                           "episode_length": len(def_rew),
                           **stats_der_episode(def_wrapper, def_log_vorher)})

    return zeilen


def arbeite(auftrag):
    """Wrapper fuer den Prozesspool: faengt Fehler ab, damit einer nicht alles kippt."""
    try:
        return auftrag, eine_zelle(auftrag), None
    except Exception:
        return auftrag, [], traceback.format_exc()


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("experiment_dir")
    p.add_argument("--episodes", type=int, default=25,
                   help="Auswertungsepisoden je Zelle (default: 25)")
    p.add_argument("--episode-steps", type=int, default=2000)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--stufen", type=str, default=",".join(STUFEN),
                   help="Kommagetrennte Teilmenge von: " + ", ".join(STUFEN))
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--resume", action="store_true",
                   help="Bereits in der Ziel-CSV vorhandene Zellen ueberspringen "
                        "und die Datei fortschreiben statt sie zu ueberschreiben.")
    p.add_argument("--out", type=str, default=None,
                   help="Ziel-CSV (default: <experiment-dir>/evaluation_episodes.csv)")
    args = p.parse_args()

    root = args.experiment_dir.rstrip("/\\")
    if not os.path.isdir(root):
        raise SystemExit("Experiment-Ordner nicht gefunden: " + root)

    stufen = [s.strip() for s in args.stufen.split(",") if s.strip()]
    unbekannt = [s for s in stufen if s not in STUFEN]
    if unbekannt:
        raise SystemExit("Unbekannte Stufe(n): %s. Erlaubt: %s"
                         % (", ".join(unbekannt), ", ".join(STUFEN)))

    laeufe = finde_laeufe(root)
    if not laeufe:
        raise SystemExit("Keine fertigen Verteidiger-Laeufe in " + root)

    out_path = args.out or os.path.join(root, "evaluation_episodes.csv")

    # Bei --resume die schon fertigen Zellen anhand ihrer run_id ueberspringen.
    erledigt = set()
    if args.resume and os.path.exists(out_path):
        with open(out_path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("run_id"):
                    erledigt.add(r["run_id"])
        print("Fortsetzen: %d Zellen bereits in %s" % (len(erledigt), out_path))

    auftraege = []
    for s in stufen:
        for l in laeufe:
            rid = "eval_%s_%s_%s_%s" % (s, l["topology"], l["attacker_name"], l["seed"])
            if rid in erledigt:
                continue
            auftraege.append({"lauf": l, "stufe": s, "episodes": args.episodes,
                              "episode_steps": args.episode_steps})

    if not auftraege:
        print("Nichts zu tun -- alle Zellen sind bereits vorhanden.")
        return

    zellen = len(auftraege)
    episoden = zellen * args.episodes
    print("Laeufe gefunden:        %d" % len(laeufe))
    print("Stufen:                 %s" % ", ".join(stufen))
    print("Zellen (Stufe x Lauf):  %d" % zellen)
    print("Episoden gesamt:        %d  (%d je Zelle)" % (episoden, args.episodes))
    print("Grobe Schaetzung:       %.1f Mio. Schritte" % (episoden * args.episode_steps / 1e6))

    if args.dry_run:
        for a in auftraege[:8]:
            print("  [DRY] %-10s %-16s vs %-16s %s"
                  % (a["stufe"], a["lauf"]["topology"],
                     a["lauf"]["attacker_name"], a["lauf"]["seed"]))
        if len(auftraege) > 8:
            print("  ... und %d weitere" % (len(auftraege) - 8))
        return

    fertig = 0
    fehler = 0
    anhaengen = args.resume and os.path.exists(out_path)
    with open(out_path, "a" if anhaengen else "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, restval="",
                                extrasaction="ignore")
        if not anhaengen:
            writer.writeheader()

        if args.workers > 1:
            from concurrent.futures import ProcessPoolExecutor, as_completed
            import multiprocessing as mp
            ctx = mp.get_context("spawn")
            with ProcessPoolExecutor(max_workers=args.workers, mp_context=ctx) as ex:
                futures = [ex.submit(arbeite, a) for a in auftraege]
                for fut in as_completed(futures):
                    auftrag, zeilen, fehltext = fut.result()
                    fertig += 1
                    if fehltext:
                        fehler += 1
                        print("[FEHLER] %s %s vs %s %s\n%s"
                              % (auftrag["stufe"], auftrag["lauf"]["topology"],
                                 auftrag["lauf"]["attacker_name"],
                                 auftrag["lauf"]["seed"], fehltext))
                        continue
                    for z in zeilen:
                        writer.writerow(z)
                    f.flush()
                    print("[%3d/%3d] %-10s %-16s vs %-16s %s"
                          % (fertig, zellen, auftrag["stufe"],
                             auftrag["lauf"]["topology"],
                             auftrag["lauf"]["attacker_name"],
                             auftrag["lauf"]["seed"]))
        else:
            for auftrag in auftraege:
                auftrag, zeilen, fehltext = arbeite(auftrag)
                fertig += 1
                if fehltext:
                    fehler += 1
                    print("[FEHLER]\n" + fehltext)
                    continue
                for z in zeilen:
                    writer.writerow(z)
                f.flush()
                print("[%3d/%3d] %-10s %-16s vs %-16s %s"
                      % (fertig, zellen, auftrag["stufe"],
                         auftrag["lauf"]["topology"],
                         auftrag["lauf"]["attacker_name"], auftrag["lauf"]["seed"]))

    print()
    print("Geschrieben: %s" % out_path)
    if fehler:
        print("ACHTUNG: %d von %d Zellen fehlgeschlagen." % (fehler, zellen))


if __name__ == "__main__":
    main()
