#!/usr/bin/env python3
"""
Gemeinsame Logik fuer run_experiment_matrix.py (voller Lauf) und
run_experiment_matrix_test.py (Testlauf mit weniger Steps). Beide Skripte
fuehren exakt denselben Ablauf aus (Phase 1a/1b Attacker-Pretraining, Phase 2
Defender-Matrix) und unterscheiden sich nur in Default-Steps und
Output-Verzeichnis - die Logik liegt deshalb hier zentral, damit sie nicht an
zwei Stellen synchron gehalten werden muss.
"""

import argparse
import csv
import json
import os
import sys
import time
import traceback
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "MARLon"))

from thesis_topology.envs import register_all, ENV_IDS  # noqa: E402
from marlon.simulate import train  # noqa: E402

# ── Konfiguration der Matrix ──────────────────────────────────────────────
SOLO_ATTACKER_TOPOLOGIES = ["chain", "flat", "hub_and_spoke", "dmz", "micro_segmented"]
SUPER_ATTACKER_ORDER = ["chain", "flat", "hub_and_spoke", "dmz", "micro_segmented"]
DEFENDER_TOPOLOGIES = ["flat", "hub_and_spoke", "dmz", "micro_segmented"]
ATTACKER_NAMES = SOLO_ATTACKER_TOPOLOGIES + ["super"]

DEFAULT_EPISODE_STEPS = 2000

MANIFEST_FIELDNAMES = [
    "phase", "topology", "attacker_name", "status",
    "attacker_model", "defender_model", "csv_log",
    "total_timesteps", "duration_sec", "error",
]

COMBINED_FIELDNAMES = [
    "phase", "topology", "attacker_name", "defender_algo", "run_id",
    "episode", "agent", "env_id", "algorithm", "timestep",
    "episode_reward", "episode_length",
    # Action-Tracking (Angreifer- und Defender-spezifisch; je Zeile nur eine Gruppe befüllt)
    "atk_invalid", "atk_valid", "atk_cj_reached", "atk_cj_step", "atk_won", "atk_max_owned",
    "atk_hold_reward", "atk_eviction",
    "def_reimage", "def_block", "def_allow", "def_stop_svc", "def_stop_svc_clean",
    "def_start_svc", "def_invalid", "def_recovered", "def_sla_break_steps",
    "def_abwehr_reward", "def_abgeschirmt",
]


def _done_marker(run_dir):
    return os.path.join(run_dir, "_DONE")


def _resolve_path(p):
    """Biegt absolute Pfade aus _DONE-Markern auf das lokale PROJECT_ROOT um.

    Die Marker speichern absolute Pfade der erzeugenden Maschine. Beim verteilten
    Rechnen (z.B. Attacker auf dem PC trainiert, Defender-Seeds auf dem Laptop)
    liegt das Repo dort ggf. unter einem anderen Pfad - dann existiert der
    gespeicherte Pfad nicht mehr. Ab dem 'experiments/'-Segment neu verankern.
    """
    if not p or os.path.exists(p):
        return p
    marker = os.sep + "experiments"
    idx = p.find(marker)
    if idx != -1:
        candidate = os.path.join(PROJECT_ROOT, p[idx + 1:])
        if os.path.exists(candidate):
            return candidate
    return p


def _load_marker(run_dir, require_model=False):
    """Liest den _DONE-Marker eines Laufs, oder None wenn der Lauf unvollstaendig ist.

    Robust gegen abgebrochene Laeufe: Stirbt die WSL-VM oder der Rechner mitten im
    Schreiben, bleiben Marker und Artefakte als 0-Byte-Dateien zurueck (die Daten
    hingen noch im Schreibcache). Ein solcher Torso darf NICHT als "fertig" gelten -
    sonst bricht die Wiederaufnahme mit JSONDecodeError ab oder ueberspringt einen
    Lauf, dessen Ergebnisse gar nicht existieren.

    Immer geprueft wird die Ergebnis-CSV, denn sie ist das eigentliche Resultat.

    `require_model` nur dort setzen, wo die Modelldatei anschliessend wirklich
    geladen wird - also fuer die Angreifer aus Phase 1, die Phase 2 braucht.
    Beim verteilten Rechnen werden Defender-Modelle bewusst nicht zwischen den
    Maschinen synchronisiert (~360 MB); ihre Laeufe sind trotzdem vollstaendig
    und duerfen weder wiederholt noch aus der Auswertung geworfen werden.
    """
    marker = _done_marker(run_dir)
    if not os.path.isfile(marker) or os.path.getsize(marker) == 0:
        return None
    try:
        with open(marker, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError):
        print(f"  [WARN] beschaedigter _DONE-Marker, Lauf wird wiederholt: {run_dir}")
        return None

    # Pfade zentral normalisieren, damit alle Aufrufer davon profitieren.
    for key in ("attacker", "defender", "csv"):
        if data.get(key):
            data[key] = _resolve_path(data[key])

    csv_path = data.get("csv")
    if csv_path and (not os.path.isfile(csv_path) or os.path.getsize(csv_path) == 0):
        print(f"  [WARN] Ergebnis-CSV fehlt oder ist leer, Lauf wird wiederholt: {csv_path}")
        return None

    if require_model:
        for key in ("attacker", "defender"):
            p = data.get(key)
            if p and (not os.path.isfile(p) or os.path.getsize(p) == 0):
                print(f"  [WARN] benoetigtes Modell fehlt oder ist leer, Lauf wird wiederholt: {p}")
                return None
    return data


def _mark_done(run_dir, result):
    with open(_done_marker(run_dir), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)


class ManifestWriter:
    """Schreibt nach jedem Lauf sofort eine Zeile in manifest.csv, damit bei
    einem Abbruch (z.B. mehrtaegiger Lauf) der Fortschritt nicht verloren geht."""

    def __init__(self, path):
        is_new = not os.path.exists(path)
        self._f = open(path, "a", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._f, fieldnames=MANIFEST_FIELDNAMES)
        if is_new:
            self._writer.writeheader()
            self._f.flush()

    def write(self, **row):
        self._writer.writerow({k: row.get(k, "") for k in MANIFEST_FIELDNAMES})
        self._f.flush()

    def close(self):
        self._f.close()


class CombinedCsvWriter:
    """Haengt die Episode-Zeilen jedes Laufs an eine einzige
    combined_episodes.csv im Experiment-Ordner an, damit sich Reward-Kurven
    ueber die gesamte Matrix (alle Topologien/Attacker/Phasen) direkt aus
    einer Datei plotten lassen, statt sie aus vielen Einzel-CSVs pro Lauf
    zusammensuchen zu muessen. Idempotent ueber run_id, damit ein
    fortgesetztes Experiment keine Zeilen doppelt anhaengt."""

    def __init__(self, path):
        self._path = path
        self._existing_run_ids = set()
        if os.path.exists(path):
            with open(path, newline="", encoding="utf-8") as f:
                self._existing_run_ids = {row["run_id"] for row in csv.DictReader(f)}

    def append(self, csv_log_path, phase, topology, attacker_name, defender_algo, run_id):
        if not csv_log_path or not run_id or run_id in self._existing_run_ids:
            return
        if not os.path.exists(csv_log_path):
            return
        write_header = not os.path.exists(self._path)
        with open(self._path, "a", newline="", encoding="utf-8") as out_f, \
                open(csv_log_path, newline="", encoding="utf-8") as in_f:
            # extrasaction='ignore': ältere Trainings-Logs ohne Action-Spalten
            # (und evtl. zukünftige Zusatzspalten) brechen den Writer nicht.
            writer = csv.DictWriter(out_f, fieldnames=COMBINED_FIELDNAMES,
                                    restval="", extrasaction="ignore")
            if write_header:
                writer.writeheader()
            for row in csv.DictReader(in_f):
                writer.writerow({
                    "phase": phase, "topology": topology,
                    "attacker_name": attacker_name, "defender_algo": defender_algo,
                    "run_id": run_id, **row,
                })
        self._existing_run_ids.add(run_id)


def run_one(manifest, combined, phase, topology, attacker_name, save_dir,
            total_timesteps, episode_steps, dry_run,
            defender_algo="None", attacker_file=None, attacker_frozen=False,
            attacker_masking=False, auto_stop=False, seed=None):
    """Fuehrt einen einzelnen train()-Lauf aus. Ueberspringt ihn, falls die
    _DONE-Markerdatei im Zielordner schon existiert (Wiederaufnahme)."""

    existing = _load_marker(save_dir)
    if existing:
        print(f"  [SKIP] bereits abgeschlossen: {save_dir}")
        if not dry_run:
            combined.append(existing.get("csv"), phase, topology, attacker_name,
                             defender_algo, existing.get("run_id"))
        return existing

    if dry_run:
        print(f"  [DRY-RUN] {phase} | topology={topology} | attacker={attacker_name} "
              f"| defender_algo={defender_algo} | steps={total_timesteps} "
              f"| attacker_file={attacker_file} -> {save_dir}")
        return None

    os.makedirs(save_dir, exist_ok=True)
    env_id = ENV_IDS[topology]

    print(f"  [START] {phase} | topology={topology} | attacker={attacker_name} "
          f"| defender_algo={defender_algo} | steps={total_timesteps}")
    start = time.time()
    try:
        result = train(
            env_id=env_id,
            attacker_algo="PPO",
            defender_algo=defender_algo,
            total_timesteps=total_timesteps,
            episode_steps=episode_steps,
            save_dir=save_dir,
            attacker_file=attacker_file,
            defender_file=None,
            attacker_frozen=attacker_frozen,
            defender_frozen=False,
            attacker_masking=attacker_masking,
            auto_stop=auto_stop,
            seed=seed,
        )
        duration = time.time() - start
        _mark_done(save_dir, result)
        manifest.write(
            phase=phase, topology=topology, attacker_name=attacker_name,
            status="success",
            attacker_model=result.get("attacker", ""),
            defender_model=result.get("defender", "") or "",
            csv_log=result.get("csv", ""),
            total_timesteps=total_timesteps,
            duration_sec=round(duration, 1),
            error="",
        )
        combined.append(result.get("csv"), phase, topology, attacker_name,
                         defender_algo, result.get("run_id"))
        print(f"  [OK] {duration:.0f}s -> {save_dir}")
        return result
    except Exception as exc:
        duration = time.time() - start
        traceback.print_exc()
        manifest.write(
            phase=phase, topology=topology, attacker_name=attacker_name,
            status="failed",
            attacker_model="", defender_model="", csv_log="",
            total_timesteps=total_timesteps,
            duration_sec=round(duration, 1),
            error=str(exc),
        )
        print(f"  [FAIL] {exc}")
        return None


def _pretrain_worker(job):
    """Trainiert EINEN Solo-Angreifer isoliert (fuer ProcessPoolExecutor).
    Schreibt nur ins eigene save_dir + _DONE-Marker; Aggregation danach zentral."""
    try:
        import torch
        torch.set_num_threads(job.get("torch_threads", 2))
    except Exception:
        pass
    register_all()
    save_dir = job["save_dir"]
    if _load_marker(save_dir):
        return dict(job, status="skip")
    os.makedirs(save_dir, exist_ok=True)
    start = time.time()
    try:
        result = train(
            env_id=ENV_IDS[job["topology"]], attacker_algo="PPO", defender_algo="None",
            total_timesteps=job["total_timesteps"], episode_steps=job["episode_steps"],
            save_dir=save_dir, attacker_masking=job["masking"], consolidate=False,
        )
        _mark_done(save_dir, result)
        return dict(job, status="success", duration=round(time.time() - start, 1))
    except Exception as exc:
        traceback.print_exc()
        return dict(job, status="failed", error=str(exc))


def _matrix_worker(job):
    """Fuehrt EIN Defender-Matchup isoliert aus (fuer ProcessPoolExecutor).
    Schreibt nicht in geteilte Dateien (manifest/combined/all_training_runs) -
    nur ins eigene save_dir + _DONE-Marker. Die Aggregation erfolgt danach
    zentral im Hauptprozess (single-threaded, dadurch konfliktfrei)."""
    try:
        import torch
        torch.set_num_threads(job.get("torch_threads", 2))
    except Exception:
        pass
    register_all()
    save_dir = job["save_dir"]
    if _load_marker(save_dir):
        return dict(job, status="skip")
    os.makedirs(save_dir, exist_ok=True)
    start = time.time()
    try:
        result = train(
            env_id=ENV_IDS[job["topology"]], attacker_algo="PPO", defender_algo="PPO",
            total_timesteps=job["total_timesteps"], episode_steps=job["episode_steps"],
            save_dir=save_dir, attacker_file=job["attacker_file"], attacker_frozen=True,
            attacker_masking=job["masking"], auto_stop=job["auto_stop"], seed=job["seed"],
            consolidate=False,
        )
        _mark_done(save_dir, result)
        return dict(job, status="success", duration=round(time.time() - start, 1))
    except Exception as exc:
        traceback.print_exc()
        return dict(job, status="failed", error=str(exc))


def build_arg_parser(doc, default_attacker_steps, default_defender_steps):
    parser = argparse.ArgumentParser(
        description=doc, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--attacker-steps", type=int, default=default_attacker_steps,
                         help=f"Total-Timesteps je Solo-/Super-Attacker-Stufe (default: {default_attacker_steps})")
    parser.add_argument("--defender-steps", type=int, default=default_defender_steps,
                         help=f"Total-Timesteps je Defender-Matrix-Lauf (default: {default_defender_steps})")
    parser.add_argument("--episode-steps", type=int, default=DEFAULT_EPISODE_STEPS,
                         help=f"Episodenlaenge / max_timesteps pro Episode (default: {DEFAULT_EPISODE_STEPS})")
    parser.add_argument("--experiment-dir", type=str, default=None,
                         help="Bestehenden Experiment-Ordner fortsetzen statt einen neuen anzulegen "
                              "(z.B. experiments/20260710_140000) - ueberspringt bereits fertige Laeufe.")
    parser.add_argument("--dry-run", action="store_true",
                         help="Nur den Ablaufplan anzeigen, nichts trainieren.")
    parser.add_argument("--masking", action="store_true",
                         help="Angreifer mit Invalid-Action-Masking (MaskablePPO) trainieren/einfrieren.")
    parser.add_argument("--auto-stop", action="store_true",
                         help="Defender-Matrix-Laeufe bei Konvergenz vorzeitig stoppen (spart Rechenzeit).")
    parser.add_argument("--seeds", type=int, default=1,
                         help="Anzahl Seeds pro Defender-Matchup (Wiederholungen fuer Statistik, default: 1).")
    parser.add_argument("--attackers-only", action="store_true",
                         help="Nur Phase 1 (Attacker-Pretraining) rechnen und vor der "
                              "Defender-Matrix stoppen. Nuetzlich, wenn die Angreifer zentral "
                              "auf einer Maschine trainiert und die Defender-Seeds danach auf "
                              "mehrere Rechner verteilt werden.")
    parser.add_argument("--seed-list", type=str, default=None,
                         help="Nur diese Seeds rechnen, kommagetrennt (z.B. '0,1,2'). Ueberschreibt "
                              "--seeds bei der Auswahl. Fuer verteiltes Rechnen auf mehreren Maschinen: "
                              "PC '--seed-list 0,1,2', Laptop '--seed-list 3,4'. Die Ordnernamen bleiben "
                              "seed<N>, sodass sich beide Haelften spaeter konfliktfrei zusammenfuehren "
                              "lassen (danach aggregate_experiment.py laufen lassen).")
    parser.add_argument("--workers", type=int, default=1,
                         help="Anzahl paralleler Prozesse fuer die Defender-Matrix (default: 1 = sequenziell).")
    return parser


def main(doc, default_attacker_steps, default_defender_steps,
         experiments_dirname, new_experiment_label):
    args = build_arg_parser(doc, default_attacker_steps, default_defender_steps).parse_args()

    register_all()

    if args.experiment_dir:
        root = args.experiment_dir
        if not os.path.isdir(root):
            raise SystemExit(f"Experiment-Ordner nicht gefunden: {root}")
        print(f"Setze bestehendes Experiment fort: {root}")
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        root = os.path.join(PROJECT_ROOT, experiments_dirname, timestamp)
        os.makedirs(root, exist_ok=True)
        print(f"{new_experiment_label}: {root}")

    attackers_root = os.path.join(root, "attackers")
    defenders_root = os.path.join(root, "defenders")
    manifest = ManifestWriter(os.path.join(root, "manifest.csv"))
    combined = CombinedCsvWriter(os.path.join(root, "combined_episodes.csv"))

    config_path = os.path.join(root, "config.json")
    if not os.path.exists(config_path):
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({
                "attacker_steps": args.attacker_steps,
                "defender_steps": args.defender_steps,
                "episode_steps": args.episode_steps,
                "solo_attacker_topologies": SOLO_ATTACKER_TOPOLOGIES,
                "super_attacker_order": SUPER_ATTACKER_ORDER,
                "defender_topologies": DEFENDER_TOPOLOGIES,
                "started_at": datetime.now().isoformat(),
            }, f, indent=2)

    total_runs = len(SOLO_ATTACKER_TOPOLOGIES) + len(SUPER_ATTACKER_ORDER) + \
        len(DEFENDER_TOPOLOGIES) * len(ATTACKER_NAMES)
    print(f"Geplante Laeufe: {len(SOLO_ATTACKER_TOPOLOGIES)} Solo-Attacker + "
          f"{len(SUPER_ATTACKER_ORDER)} Super-Attacker-Stufen + "
          f"{len(DEFENDER_TOPOLOGIES)}x{len(ATTACKER_NAMES)} Defender-Matrix "
          f"= {total_runs} Laeufe insgesamt\n")

    try:
        # ── Phase 1a: 5 Solo-Attacker (unabhaengig -> parallelisierbar) ───
        print("=== Phase 1a: Solo-Attacker-Pretraining ===")
        attacker_paths = {}
        if args.workers > 1 and not args.dry_run:
            from concurrent.futures import ProcessPoolExecutor, as_completed
            import multiprocessing as mp
            solo_jobs = [dict(topology=t, save_dir=os.path.join(attackers_root, t),
                              total_timesteps=args.attacker_steps, episode_steps=args.episode_steps,
                              masking=args.masking) for t in SOLO_ATTACKER_TOPOLOGIES]
            print(f"Parallel mit {args.workers} Workern (spawn) ...")
            with ProcessPoolExecutor(max_workers=args.workers,
                                     mp_context=mp.get_context('spawn')) as ex:
                futs = [ex.submit(_pretrain_worker, j) for j in solo_jobs]
                for fut in as_completed(futs):
                    r = fut.result()
                    print(f"  {r['status']:7s} attacker/{r['topology']}")
            for j in solo_jobs:  # zentrale Aggregation + attacker_paths
                marker = _load_marker(j["save_dir"], require_model=True)
                if not marker:
                    print(f"  [WARN] kein Attacker-Modell fuer '{j['topology']}' - Phase 2 ueberspringt es.")
                    continue
                combined.append(marker.get("csv"), "attacker_pretrain", j["topology"],
                                j["topology"], "None", marker.get("run_id"))
                manifest.write(phase="attacker_pretrain", topology=j["topology"],
                               attacker_name=j["topology"], status="success",
                               attacker_model=marker.get("attacker", ""), defender_model="",
                               csv_log=marker.get("csv", ""), total_timesteps=j["total_timesteps"],
                               duration_sec="", error="")
                attacker_paths[j["topology"]] = marker["attacker"]
        else:
            for topology in SOLO_ATTACKER_TOPOLOGIES:
                save_dir = os.path.join(attackers_root, topology)
                run_one(
                    manifest, combined, phase="attacker_pretrain", topology=topology,
                    attacker_name=topology, save_dir=save_dir,
                    total_timesteps=args.attacker_steps, episode_steps=args.episode_steps,
                    dry_run=args.dry_run, defender_algo="None",
                    attacker_masking=args.masking,
                )
                marker = _load_marker(save_dir, require_model=True)
                if marker:
                    attacker_paths[topology] = marker["attacker"]
                elif not args.dry_run:
                    print(f"  [WARN] kein Attacker-Modell fuer '{topology}' verfuegbar "
                          f"(Lauf fehlgeschlagen) - wird in Phase 2 uebersprungen.")

        # ── Phase 1b: Super-Attacker (sequenziell ueber alle 5 Topologien) ─
        print("\n=== Phase 1b: Super-Attacker (sequenziell) ===")
        super_dir = os.path.join(attackers_root, "super")
        os.makedirs(super_dir, exist_ok=True)

        super_marker = _load_marker(super_dir, require_model=True)
        if super_marker:
            print(f"  [SKIP] Super-Attacker bereits fertig: {super_dir}")
            attacker_paths["super"] = super_marker["attacker"]
        elif args.dry_run:
            for i, topology in enumerate(SUPER_ATTACKER_ORDER, 1):
                stage_dir = os.path.join(super_dir, f"stage{i}_{topology}")
                run_one(
                    manifest, combined, phase="attacker_pretrain_super_stage",
                    topology=topology, attacker_name=f"super_stage{i}_{topology}",
                    save_dir=stage_dir,
                    total_timesteps=args.attacker_steps, episode_steps=args.episode_steps,
                    dry_run=True, defender_algo="None",
                )
        else:
            prev_model_file = None
            broke = False
            for i, topology in enumerate(SUPER_ATTACKER_ORDER, 1):
                stage_dir = os.path.join(super_dir, f"stage{i}_{topology}")
                run_one(
                    manifest, combined, phase="attacker_pretrain_super_stage",
                    topology=topology, attacker_name=f"super_stage{i}_{topology}",
                    save_dir=stage_dir,
                    total_timesteps=args.attacker_steps, episode_steps=args.episode_steps,
                    dry_run=False, defender_algo="None",
                    attacker_file=prev_model_file, attacker_frozen=False,
                    attacker_masking=args.masking,
                )
                stage_marker = _load_marker(stage_dir, require_model=True)
                if not stage_marker:
                    print(f"  [ABBRUCH] Super-Attacker Stufe {i} ({topology}) fehlgeschlagen "
                          f"- weitere Stufen werden uebersprungen.")
                    broke = True
                    break
                prev_model_file = stage_marker["attacker"]

            if not broke:
                _mark_done(super_dir, {"attacker": prev_model_file})
                attacker_paths["super"] = prev_model_file

        # ── Phase 2: Defender-Matrix (4 Topologien x 6 Attacker x Seeds) ──
        print("\n=== Phase 2: Defender-Matrix ===")
        # Welche Seeds rechnet DIESE Maschine? --seed-list erlaubt es, die Arbeit
        # auf mehrere Rechner aufzuteilen (PC: 0,1,2 / Laptop: 3,4).
        if args.attackers_only:
            # Leere Jobliste -> alle nachfolgenden Zweige laufen ins Leere.
            seed_ids, use_seed_dirs = [], True
            print("  [SKIP] --attackers-only gesetzt: Defender-Matrix wird uebersprungen.")
        elif args.seed_list:
            seed_ids = [int(x) for x in args.seed_list.split(",") if x.strip()]
            use_seed_dirs = True
        else:
            seed_ids = list(range(args.seeds))
            use_seed_dirs = args.seeds > 1

        # Jobliste aufbauen (jedes Matchup ggf. mehrfach mit verschiedenen Seeds)
        jobs = []
        for topology in DEFENDER_TOPOLOGIES:
            for attacker_name in ATTACKER_NAMES:
                attacker_file = attacker_paths.get(attacker_name)
                if not attacker_file:
                    print(f"  [SKIP] kein Attacker-Modell fuer '{attacker_name}' verfuegbar")
                    continue
                for s in seed_ids:
                    sub = os.path.join(f"vs_{attacker_name}", f"seed{s}") if use_seed_dirs \
                        else f"vs_{attacker_name}"
                    jobs.append(dict(
                        topology=topology, attacker_name=attacker_name, attacker_file=attacker_file,
                        save_dir=os.path.join(defenders_root, topology, sub),
                        seed=(s if use_seed_dirs else None),
                        total_timesteps=args.defender_steps, episode_steps=args.episode_steps,
                        masking=args.masking, auto_stop=args.auto_stop,
                    ))
        matrix_total = len(jobs)
        print(f"Defender-Matrix: {matrix_total} Laeufe  "
              f"(masking={args.masking}, auto_stop={args.auto_stop}, "
              f"seeds={seed_ids}, workers={args.workers})")

        def _tag(j):
            return f"{j['topology']}/vs_{j['attacker_name']}" + \
                   ("" if j["seed"] is None else f"/seed{j['seed']}")

        if args.dry_run:
            for j in jobs:
                print(f"  [DRY-RUN] {_tag(j)} -> {j['save_dir']}")
        elif args.workers > 1:
            # Parallel: isolierte Worker, danach zentrale Aggregation.
            # WICHTIG: 'spawn' statt des Linux-Defaults 'fork' - torch/OpenMP
            # verklemmt sich sonst in geforkten Kindprozessen (Deadlock).
            from concurrent.futures import ProcessPoolExecutor, as_completed
            import multiprocessing as mp
            print(f"Parallel mit {args.workers} Workern (spawn, Aggregation danach zentral) ...")
            done = 0
            with ProcessPoolExecutor(max_workers=args.workers,
                                     mp_context=mp.get_context('spawn')) as ex:
                futs = [ex.submit(_matrix_worker, j) for j in jobs]
                for fut in as_completed(futs):
                    r = fut.result(); done += 1
                    extra = f"  ({r['error']})" if r.get("status") == "failed" else ""
                    print(f"  [{done}/{matrix_total}] {r['status']:7s} {_tag(r)}{extra}")
            # zentrale, konfliktfreie Aggregation aus den _DONE-Markern
            for j in jobs:
                marker = _load_marker(j["save_dir"])
                if not marker:
                    continue
                combined.append(marker.get("csv"), "defender_matrix", j["topology"],
                                j["attacker_name"], "PPO", marker.get("run_id"))
                manifest.write(
                    phase="defender_matrix", topology=j["topology"], attacker_name=j["attacker_name"],
                    status="success", attacker_model=j["attacker_file"],
                    defender_model=marker.get("defender", "") or "", csv_log=marker.get("csv", ""),
                    total_timesteps=j["total_timesteps"], duration_sec="", error="",
                )
        else:
            # Sequenziell (nutzt manifest/combined direkt in run_one)
            for i, j in enumerate(jobs, 1):
                print(f"[{i}/{matrix_total}]", end=" ")
                run_one(
                    manifest, combined, phase="defender_matrix", topology=j["topology"],
                    attacker_name=j["attacker_name"], save_dir=j["save_dir"],
                    total_timesteps=j["total_timesteps"], episode_steps=j["episode_steps"],
                    dry_run=False, defender_algo="PPO", attacker_file=j["attacker_file"],
                    attacker_frozen=True, attacker_masking=j["masking"],
                    auto_stop=j["auto_stop"], seed=j["seed"],
                )
    finally:
        manifest.close()

    print(f"\nFertig. Alle Ergebnisse unter: {root}")
    print(f"Uebersicht: {os.path.join(root, 'manifest.csv')}")
    print(f"Kombinierte Episoden-Daten (fuer Plots): {os.path.join(root, 'combined_episodes.csv')}")
