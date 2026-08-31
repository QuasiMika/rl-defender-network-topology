#!/usr/bin/env python3
"""Baut manifest.csv und combined_episodes.csv eines Experiments komplett neu auf.

Gedacht fuer verteiltes Rechnen: PC und Laptop rechnen unterschiedliche Seeds
(--seed-list) und schreiben in getrennte seed<N>/-Ordner. Nach dem Zusammenfuehren
der Verzeichnisbaeume (git merge/pull) sind die beiden aggregierten CSVs
uneinheitlich - jede Maschine kennt nur ihre eigene Haelfte. Dieses Skript liest
stattdessen ALLE _DONE-Marker und erzeugt beide Dateien aus dem tatsaechlichen
Bestand neu.

Nutzung:
    python aggregate_experiment.py experiments/20260807_004059
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import experiment_matrix_lib as lib  # noqa: E402


def main():
    if len(sys.argv) < 2:
        raise SystemExit(f"Nutzung: python {os.path.basename(__file__)} <experiment-dir>")
    root = sys.argv[1].rstrip("/\\")
    if not os.path.isdir(root):
        raise SystemExit(f"Experiment-Ordner nicht gefunden: {root}")

    attackers_root = os.path.join(root, "attackers")
    defenders_root = os.path.join(root, "defenders")

    manifest_path = os.path.join(root, "manifest.csv")
    combined_path = os.path.join(root, "combined_episodes.csv")
    for p in (manifest_path, combined_path):
        if os.path.exists(p):
            os.remove(p)   # bewusst neu aufbauen statt anhaengen

    manifest = lib.ManifestWriter(manifest_path)
    combined = lib.CombinedCsvWriter(combined_path)
    n_atk = n_def = 0

    # ── Phase 1a: Solo-Attacker ──────────────────────────────────────────────
    for topo in lib.SOLO_ATTACKER_TOPOLOGIES:
        marker = lib._load_marker(os.path.join(attackers_root, topo))
        if not marker:
            continue
        combined.append(marker.get("csv"), "attacker_pretrain", topo, topo, "None",
                        marker.get("run_id"))
        manifest.write(phase="attacker_pretrain", topology=topo, attacker_name=topo,
                       status="success", attacker_model=marker.get("attacker", ""),
                       defender_model="", csv_log=marker.get("csv", ""),
                       total_timesteps=marker.get("total_timesteps", ""),
                       duration_sec="", error="")
        n_atk += 1

    # ── Phase 1b: Super-Attacker-Stufen ──────────────────────────────────────
    for i, topo in enumerate(lib.SUPER_ATTACKER_ORDER, 1):
        stage_dir = os.path.join(attackers_root, "super", f"stage{i}_{topo}")
        marker = lib._load_marker(stage_dir)
        if not marker:
            continue
        name = f"super_stage{i}_{topo}"
        combined.append(marker.get("csv"), "attacker_pretrain_super_stage", topo, name,
                        "None", marker.get("run_id"))
        manifest.write(phase="attacker_pretrain_super_stage", topology=topo,
                       attacker_name=name, status="success",
                       attacker_model=marker.get("attacker", ""), defender_model="",
                       csv_log=marker.get("csv", ""),
                       total_timesteps=marker.get("total_timesteps", ""),
                       duration_sec="", error="")
        n_atk += 1

    # ── Phase 2: Defender-Matrix (alle Seeds, egal von welcher Maschine) ─────
    for topo in lib.DEFENDER_TOPOLOGIES:
        for atk in lib.ATTACKER_NAMES:
            base = os.path.join(defenders_root, topo, f"vs_{atk}")
            if not os.path.isdir(base):
                continue
            # Sowohl seed<N>/-Unterordner als auch der seed-lose Fall (--seeds 1)
            candidates = [os.path.join(base, d) for d in sorted(os.listdir(base))
                          if d.startswith("seed") and os.path.isdir(os.path.join(base, d))]
            if not candidates:
                candidates = [base]
            for run_dir in candidates:
                marker = lib._load_marker(run_dir)
                if not marker:
                    continue
                combined.append(marker.get("csv"), "defender_matrix", topo, atk, "PPO",
                                marker.get("run_id"))
                manifest.write(phase="defender_matrix", topology=topo, attacker_name=atk,
                               status="success", attacker_model="",
                               defender_model=marker.get("defender", "") or "",
                               csv_log=marker.get("csv", ""),
                               total_timesteps=marker.get("total_timesteps", ""),
                               duration_sec="", error="")
                n_def += 1

    manifest.close()
    print(f"Aggregiert: {n_atk} Attacker-Laeufe, {n_def} Defender-Matchups")
    print(f"  {manifest_path}")
    print(f"  {combined_path}")


if __name__ == "__main__":
    main()
