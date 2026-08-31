# thesis_topology

Topologie-Generator für CyberBattleSim – Bachelorarbeit:
**"Einfluss der Netzwerktopologie auf die Lerneffizienz eines RL-basierten Blue Agents in CyberBattleSim"**

---

## Design-Begründung (Methodik-Kapitel)

### Wissenschaftliche Kernanforderung: Festes Inventar

Damit **Topologie die einzige unabhängige Variable** ist, teilen alle vier
Topologien exakt dasselbe Knoten-Inventar:

| Was konstant bleibt              | Was variiert                                   |
|----------------------------------|------------------------------------------------|
| Node-IDs, Anzahl, Werte          | `LeakedCredentials`-Outcomes (wer kann wohin)  |
| Vulnerability-IDs & -Typen       | `LeakedNodesId`-Outcomes (wer sieht wen)       |
| Credential-IDs & Dienste         | `FirewallConfiguration` (welche Ports erlaubt) |
| `ENV_IDENTIFIERS` (Obs.-Space)   |                                                |
| Gesamt-Reward (= 180)            |                                                |

Konsequenz: Reward-Kapazität, Observation-Space-Dimensionen und
Vulnerability-Menge sind identisch. Unterschiede in Konvergenzzeit und
final erreichtem Reward lassen sich kausal auf die Topologie zurückführen.

### Erreichbarkeitsmodell in CBS

CBS modelliert **keine physischen Netzwerkkanten**. `create_network()`
erzeugt einen kantenlosen DiGraph. Erreichbarkeit entsteht aus:

1. **`LeakedCredentials`** (LOCAL-Vulnerability): Angreifer, der Knoten A
   besitzt, kann `ScanLocalCredentials` ausführen → erhält
   `CachedCredential(node=B, port=P, credential=C)` → kann danach per
   `connect`-Aktion zu B wechseln, **wenn** Firewall beidseitig erlaubt.

2. **`LeakedNodesId`** (LOCAL-Vulnerability): Offenbart nur die Existenz von
   B (Discovery), kein automatischer Zugang.

3. **`FirewallConfiguration`**: Port-basiert (kein Source-IP-Filter).
   Erste passende Regel gewinnt; nicht gelistet = BLOCKED.

### Abbildung Segmentierungsgrad → Topologie

| Muster | Segmentierung | Chokepoints | Pfade zu DB | CBS-Implementierung |
|--------|--------------|-------------|-------------|---------------------|
| chain  | maximal      | 5           | 1           | Jeder Knoten leakt Credential nur für nächsten |
| star   | hoch         | 1 (DC)      | 1           | WebServer→DC, DC→alle anderen |
| tree   | mittel       | 1 (DC)      | 2           | 2 Äste konvergieren am DC |
| mesh   | minimal      | 0           | 9           | Viele Direktpfade, max. parallele Credentials |

---

## Knoten-Inventar

```
WebServer        (Einstiegspunkt, value=0,   HTTP/HTTPS)
Workstation1     (value=10,  SSH,  cred_ws1_ssh)
Workstation2     (value=10,  SSH,  cred_ws2_ssh)
Workstation3     (value=10,  SSH,  cred_ws3_ssh)
FileServer       (value=20,  SMB,  cred_fs_smb)
DomainController (value=30,  RDP,  cred_dc_rdp)
DatabaseServer   (value=100, SQL,  cred_db_sql)   ← Crown Jewel
                                    ───────────
                         Gesamt-Reward: 180
```

**Vulnerabilities** (identisch auf jedem Knoten, nur Outcomes variieren):
- `ScanLocalCredentials` (LOCAL): leakt Credentials für direkte Nachbarn
- `ScanHostDiscovery` (LOCAL): leakt Node-IDs der direkten Nachbarn
- `RemoteProbe` (REMOTE): liefert Node-Properties (Recon)

---

## Dateistruktur

```
thesis_topology/
├── inventory.py           # Festes Inventar + ENV_IDENTIFIERS (Aufgabe 1)
├── topology_generator.py  # Adjacency-Maps + NodeInfo-Erzeugung (Aufgabe 2)
├── validator.py           # Angriffsgraph-Aufbau + BFS-Check (Aufgabe 3)
├── metrics.py             # Struktur-Metriken + Tabellen-Ausgabe (Aufgabe 4)
├── envs.py                # CyberBattleEnv-Subklassen + gym.register (Aufgabe 5)
├── cli.py                 # CLI: erzeugen, validieren, Metriken (Aufgabe 5)
├── test_smoke.py          # Pytest Smoke-Tests (Aufgabe 5)
└── conftest.py            # pytest sys.path-Setup
```

---

## Schnellstart

```bash
# Aus dem Wurzelverzeichnis des Repositorys
export PYTHONPATH=$(pwd)

# Alle Topologien erzeugen, validieren, Metriken ausgeben:
python -m thesis_topology.cli

# Einzelne Topologie:
python -m thesis_topology.cli --pattern chain mesh

# Smoke-Tests:
python -m pytest thesis_topology/test_smoke.py -v

# In eigenem Code:
from thesis_topology.envs import make_env
from marlon.baseline_models.env_wrappers.attack_wrapper import AttackerEnvWrapper

cyber_env = make_env("chain")
wrapper = AttackerEnvWrapper(cyber_env=cyber_env, max_timesteps=2000)
obs, _ = wrapper.reset()
```

---

## Metriken-Referenz

| Metrik | Bedeutung für Lerneffizienz |
|--------|-----------------------------|
| `Pfade→Ziel` | Mehr Pfade = mehr Lernmöglichkeiten, ggf. schnellere Konvergenz |
| `Chokepoints` | Engstellen, die der Agent zuverlässig finden muss |
| `Ø-KP-Länge` | Längere Pfade = mehr Schritte bis Reward → langsamere Konvergenz erwartet |
| `KP→Ziel` | Minimale Angriffspfadlänge |
| `Durchmesser` | Maximale Netzausdehnung aus Angreifer-Sicht |

---

## Bekannte Bugs (gefixt)

`MARLon/marlon/baseline_models/env_wrappers/attack_wrapper.py:298`
verwendete `local_attacks_count` statt `remote_attacks_count` beim
Flatten des `remote_vulnerability`-Arrays → IndexError wenn
`local_attacks_count ≠ remote_attacks_count`. Wurde in diesem Repo gefixt.
