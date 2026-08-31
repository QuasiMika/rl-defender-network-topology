"""
Fixed node inventory for topology comparison experiments.

DESIGN RATIONALE (Methodik-Kapitel):
  Alle vier Topologien (chain/star/tree/mesh) teilen dieses Inventar.
  Identisch über alle Topologien: Knoten-IDs, Knotenwerte, Dienste,
  Credential-IDs, Vulnerability-IDs/-Typen/-Raten, ENV_IDENTIFIERS.
  NUR die Vulnerability-Outcomes (welche Credentials/Node-IDs geleakt
  werden) und die Firewall-Konfiguration variieren.
  => Topologie ist die einzige unabhängige Variable.
"""

from cyberbattle.simulation import model as m

# ── Zentrale Konfigurationskonstante ──────────────────────────────────────────
NODE_COUNT = 10         # Einzige Stelle zum Skalieren des Netzes
ENTRY_NODE  = "WebServer"       # Einstiegspunkt des Angreifers
TARGET_NODE = "DatabaseServer"  # Crown Jewel / kritischer Zielknoten

NODE_NAMES = [
    "WebServer",        # von außen erreichbar, Wert 0
    "Workstation1",     # Mitarbeiter-PC
    "Workstation2",     # Mitarbeiter-PC
    "Workstation3",     # Mitarbeiter-PC
    "MailServer",       # E-Mail-Server (intern/webmail)
    "FileServer",       # Dateiserver
    "AppServer",        # Interner Applikationsserver
    "BackupServer",     # Backup-Server (höchste Datendichte)
    "DomainController", # Active-Directory-Server
    "DatabaseServer",   # Produktionsdatenbank, Crown Jewel
]
assert len(NODE_NAMES) == NODE_COUNT

# ── Knotenwerte (topology-unabhängig) ─────────────────────────────────────────
NODE_VALUES: dict[str, int] = {
    "WebServer":         0,    # Einstiegspunkt, bereits owned → kein Reward
    "Workstation1":     10,
    "Workstation2":     10,
    "Workstation3":     10,
    "MailServer":       15,    # Enthält Credentials und sensible Kommunikation
    "FileServer":       20,
    "AppServer":        15,    # Geschäftskritische Applikationsdaten
    "BackupServer":     25,    # Enthält Backups aller Systeme – hoher Wert
    "DomainController": 30,
    "DatabaseServer":  100,    # Crown Jewel
}
assert set(NODE_NAMES) == set(NODE_VALUES)

# Gesamt-Reward ist über alle Topologien identisch (Kontrolle der UV)
TOTAL_REWARD: int = sum(NODE_VALUES.values())  # = 235

# ── Credential-IDs (topology-unabhängig) ──────────────────────────────────────
# Jeder Nicht-Eingangsknoten hat genau eine Credential für seinen Dienst.
# WELCHE Vulnerability auf WELCHEM Knoten diese leakt, variiert per Topologie.
CRED_ID: dict[str, str] = {
    "Workstation1":     "cred_ws1_ssh",
    "Workstation2":     "cred_ws2_ssh",
    "Workstation3":     "cred_ws3_ssh",
    "MailServer":       "cred_mail_https",
    "FileServer":       "cred_fs_smb",
    "AppServer":        "cred_app_http",
    "BackupServer":     "cred_backup_smb",
    "DomainController": "cred_dc_rdp",
    "DatabaseServer":   "cred_db_sql",
}

# ── Port pro Knoten (der Port, über den der Knoten erreichbar ist) ─────────────
NODE_ACCESS_PORT: dict[str, str] = {
    "Workstation1":     "SSH",
    "Workstation2":     "SSH",
    "Workstation3":     "SSH",
    "MailServer":       "HTTPS",   # Webmail-Interface
    "FileServer":       "SMB",
    "AppServer":        "HTTP",    # Internes App-Portal (kein TLS intern)
    "BackupServer":     "SMB",     # Backup über Netzwerkfreigabe
    "DomainController": "RDP",
    "DatabaseServer":   "SQL",
}

# Alle Ports, die in irgendeiner Topologie vorkommen (für ENV_IDENTIFIERS)
ALL_PORTS = ["HTTP", "HTTPS", "RDP", "SMB", "SQL", "SSH"]

# ── Vulnerability-IDs (topology-unabhängig; Outcomes variieren) ───────────────
VULN_SCAN_CREDS   = "ScanLocalCredentials"  # LOCAL: leakt Credentials für Nachbarn
VULN_SCAN_HOSTS   = "ScanHostDiscovery"     # LOCAL: leakt Node-IDs der Nachbarn
VULN_REMOTE_PROBE = "RemoteProbe"           # REMOTE: Probe → ProbeSucceeded(properties)

LOCAL_VULN_IDS  = [VULN_SCAN_CREDS, VULN_SCAN_HOSTS]
REMOTE_VULN_IDS = [VULN_REMOTE_PROBE]

# ── Node-Properties (topology-unabhängig) ─────────────────────────────────────
NODE_PROPERTIES: dict[str, list[str]] = {
    "WebServer":        ["Linux",   "WebServer"],
    "Workstation1":     ["Windows", "Workstation"],
    "Workstation2":     ["Windows", "Workstation"],
    "Workstation3":     ["Linux",   "Workstation"],
    "MailServer":       ["Windows", "MailServer"],
    "FileServer":       ["Windows", "FileServer"],
    "AppServer":        ["Linux",   "AppServer"],
    "BackupServer":     ["Linux",   "BackupServer"],
    "DomainController": ["Windows", "DomainController"],
    "DatabaseServer":   ["Linux",   "DatabaseServer"],
}

# ── Gemeinsame ENV_IDENTIFIERS (MÜSSEN für alle Topologien identisch sein) ────
# Nur so ist der Observation-Space für alle Envs gleich → vergleichbares Training.
ENV_IDENTIFIERS = m.Identifiers(
    properties=sorted({p for props in NODE_PROPERTIES.values() for p in props}),
    ports=ALL_PORTS,
    local_vulnerabilities=sorted(LOCAL_VULN_IDS),
    remote_vulnerabilities=sorted(REMOTE_VULN_IDS),
)

# ── Env-Bounds (identisch für alle Topologien) ────────────────────────────────
MAX_NODE_COUNT    = NODE_COUNT         # 10
MAX_TOTAL_CREDS   = len(CRED_ID)       # 9
# STAR: DomainController leakt bis zu 8 Credentials auf einmal → Bound = 9
MAX_CREDS_PER_ACT = MAX_TOTAL_CREDS    # 9 (sicherer oberer Bound)
