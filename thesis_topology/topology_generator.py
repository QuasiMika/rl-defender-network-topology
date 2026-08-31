"""
Topologie-Generator: Verdrahtet ein festes Knoten-Inventar zu fünf
CBS-Environments mit unterschiedlichem Segmentierungsgrad.

WAS VARIIERT (die unabhängige Variable):
  - VulnerabilityOutcome von ScanLocalCredentials  (welche Credentials wohin)
  - VulnerabilityOutcome von ScanHostDiscovery      (welche Node-IDs sichtbar)
  - FirewallConfiguration  (welche Ports ein-/ausgehen darf)

WAS KONSTANT BLEIBT:
  Node-IDs, Werte, Services, Credential-IDs, Vulnerability-IDs,
  -Typen, -Raten, ENV_IDENTIFIERS.

TOPOLOGIE-SEMANTIK (vier Vergleichsfälle + eine Pretraining-Topologie):

  flat             : Keine interne Netzwerksegmentierung.
                     WebServer hat direkte Credentials für viele interne Services
                     (gemeinsame Service-Accounts, kein Firewall-Zoning).
                     DC als Admin-Gateway zu allen Workstations.
                     Kürzeste Pfade zur DB: 2 Hops (WebServer→AppServer→DB
                     oder WebServer→DC→DB).

  hub_and_spoke    : DC als einziger Knotenpunkt (Hub).
                     WebServer verbindet sich ausschließlich mit DC;
                     DC verteilt den Zugang zu allen anderen Knoten.
                     Einziger Pfad zur DB: WebServer→DC→DB (2 Hops).
                     Risiko: DC-Kompromittierung = vollständiger Netzwerkverlust.

  dmz              : Drei Zonen – Internet-Edge | DMZ | Intranet.
                     WebServer (DMZ) erreicht nur MailServer und AppServer.
                     Zonengrenzen: MailServer→DC, AppServer→{DC,DB}.
                     DC als Admin-Gateway zu allen internen Maschinen.
                     Pfade zur DB: WebServer→AppServer→DB (2 Hops)
                     oder über MailServer/AppServer→DC→DB (3 Hops).

  micro_segmented  : Zero-Trust – nur explizit erforderliche Verbindungen.
                     DC fungiert als Identity-Provider, nicht als Admin-Gateway.
                     WS1–3, MailServer, FileServer, BackupServer sind strukturell
                     von der Angreifer-Route isoliert (90 von 235 Pkt nie erreichbar).
                     Einziger Pfad zur DB: WebServer→AppServer→DB.

  defense_in_depth : Hierarchische Baumstruktur, vier Schichten.
                     Alle 10 Knoten erreichbar – neutrale Pretraining-Topologie
                     für den Attacker (kein Vergleichsfall der Bachelorarbeit).
                     Verworfen als Pretraining-Wahl (Ausreißer-Reward, s. chain).

  chain            : Strikt linearer Pfad über alle 10 Knoten (9 Hops), in
                     fester Inventar-Reihenfolge. Strukturell maximal
                     verschieden von allen vier Vergleichsfällen → kein
                     Overlap-Bias beim Attacker-Pretraining. Kein
                     Vergleichsfall der Bachelorarbeit, nur Pretraining.
"""

from __future__ import annotations

from typing import Dict, List

from cyberbattle.simulation import model as m

from .inventory import (
    NODE_NAMES, NODE_VALUES, CRED_ID, NODE_ACCESS_PORT, NODE_PROPERTIES,
    ENTRY_NODE, TARGET_NODE,
    VULN_SCAN_CREDS, VULN_SCAN_HOSTS, VULN_REMOTE_PROBE,
    ENV_IDENTIFIERS,
)

# ── Adjacency-Maps für jedes Muster (NUR Netz-Erreichbarkeit) ─────────────────
# adjacency[A] = [B, C, ...]  bedeutet:
#   • A's ScanHostDiscovery    leakt die Node-IDs von B, C, ...
#   • A's Firewall outgoing erlaubt die Ports von B, C, ...
#   • B's, C's Firewall incoming erlaubt ihren eigenen Zugangport
#
# WICHTIG: Credentials sind hiervon ENTKOPPELT -> siehe CREDENTIAL_MAP.
# Kompromittierung braucht Netzpfad (hier) UND Ziel-Credential (CREDENTIAL_MAP).
# Ein Angreifer, der A besitzt, kann B, C, ... zwar erreichen, aber nur
# uebernehmen, wenn er auch deren Credential hat.
#
# DESIGN-PRINZIP (DC als Admin-Gateway):
#   In allen Topologien gilt: DomainController → [WS1, WS2, WS3, FS, Backup, ...]
#   Der DC hat Domain-Admin-Rechte auf alle domain-joined Maschinen – dies ist die
#   CBS-Abstraktion von Pass-the-Hash / Golden-Ticket-Angriffen.
#   Ausnahme: micro_segmented – dort ist DC nur Identity-Provider (keine Lateral
#   Movement-Credentials zu Workstations), was Zero-Trust entspricht.

ADJACENCY: Dict[str, Dict[str, List[str]]] = {

    # ── 1. FLAT (keine interne Segmentierung) ─────────────────────────────────
    # Keine Firewall-Zonen zwischen WebServer und internen Services.
    # WebServer hat Service-Account-Credentials für mehrere interne Systeme
    # (typische Credential-Sprawl-Situation in nicht-segmentierten Netzen).
    # Workstations besitzen File-Share- und Domain-Credentials (WS→FS, WS→DC),
    # was realistisch für domain-joined PCs ist.
    # Kürzeste Pfade zur DB: 2 Hops (WebServer→AppServer→DB oder WebServer→DC→DB).
    "flat": {
        "WebServer":        ["MailServer", "AppServer", "FileServer", "DomainController"],
        "MailServer":       ["DomainController"],
        "AppServer":        ["DatabaseServer", "DomainController"],
        "FileServer":       ["BackupServer", "DomainController"],
        "BackupServer":     [],
        "DomainController": ["Workstation1", "Workstation2", "Workstation3",
                             "FileServer", "BackupServer", "DatabaseServer"],
        "Workstation1":     ["FileServer", "DomainController"],
        "Workstation2":     ["FileServer", "DomainController"],
        "Workstation3":     ["AppServer",  "DomainController"],
        "DatabaseServer":   [],
    },

    # ── 2. HUB-AND-SPOKE (AppServer als Hub / Chokepoint) ────────────────────
    # WebServer verbindet sich ausschließlich mit dem AppServer (dem Hub).
    # Der AppServer erreicht als einziger Knoten alle übrigen (die Spokes).
    # Kein direkter Spoke-zu-Spoke-Zugang; die Spokes haben keine ausgehenden
    # Firewall-Regeln.
    #
    # WARUM DER APPSERVER UND NICHT DER DC (geaendert 13.08.2026):
    #   Zuvor war der DomainController der Hub. Damit fiel der Engpass mit dem
    #   Knoten zusammen, der ohnehin ALLE Credentials haelt (_dc_holds_all) —
    #   eine Uebernahme des Hubs bedeutete sofort Reichweite UND Zugriff auf
    #   das gesamte Netz. Das ist kein zentrales Zugangskontrollmodell, sondern
    #   ein Single Point of Total Failure, und es widerspricht dem Tiering-
    #   Prinzip, das Domain-Controller bewusst aus dem Verkehrsweg haelt.
    #   Der AppServer ist der fachlich naheliegende Transitknoten: Er liest aus
    #   der Datenbank, authentifiziert am Verzeichnisdienst und greift auf
    #   Ablagen zu. Jetzt gilt: Hub-Uebernahme = Reichweite, aber noch kein
    #   einziger Zugang.
    #
    # Pfad zur DB: WebServer→AppServer→DB (2 Hops, wie flat/dmz).
    # Uebrige Knoten: erst nach Uebernahme des DC (Credentials), erreichbar
    # ausschliesslich ueber den AppServer.
    "hub_and_spoke": {
        "WebServer":        ["AppServer"],
        "AppServer":        ["MailServer", "DomainController", "Workstation1",
                             "Workstation2", "Workstation3", "FileServer",
                             "BackupServer", "DatabaseServer"],
        "MailServer":       [],
        "DomainController": [],
        "Workstation1":     [],
        "Workstation2":     [],
        "Workstation3":     [],
        "FileServer":       [],
        "BackupServer":     [],
        "DatabaseServer":   [],
    },

    # ── 3. DMZ (Zonenmodell / Defense-in-Depth) ───────────────────────────────
    # Drei Sicherheitszonen: Internet-Edge → DMZ → Intranet.
    # WebServer befindet sich in der DMZ und erreicht nur die DMZ-Services.
    # Zonengrenzen:
    #   MailServer → DC   (Mail-Relay authentifiziert sich per LDAP/Kerberos an AD)
    #   AppServer  → DC   (App-Server authentifiziert sich an AD)
    #   AppServer  → DB   (App hat direkte DB-Credentials)
    # DC als Admin-Gateway zu allen internen, domain-joined Maschinen.
    # Pfade zur DB: WebServer→AppServer→DB (2 Hops)
    #   oder WebServer→MailServer→DC→DB (3 Hops)
    #   oder WebServer→AppServer→DC→DB (3 Hops).
    "dmz": {
        "WebServer":        ["MailServer", "AppServer"],
        "MailServer":       ["DomainController"],
        "AppServer":        ["DatabaseServer", "DomainController"],
        "DomainController": ["Workstation1", "Workstation2", "Workstation3",
                             "FileServer", "BackupServer", "DatabaseServer"],
        "Workstation1":     [],
        "Workstation2":     [],
        "Workstation3":     [],
        "FileServer":       ["BackupServer"],
        "BackupServer":     [],
        "DatabaseServer":   [],
    },

    # ── 4. MICRO-SEGMENTED (Zero-Trust, minimale Kommunikationspfade) ─────────
    # Nur explizit erforderliche Verbindungen sind zugelassen (Least-Privilege).
    # WebServer kommuniziert ausschließlich mit AppServer (Web→App-Backend).
    # AppServer kommuniziert mit DB (Applikationsdaten) und DC (Identity).
    # DC ist hier ein reiner Identity-Provider (z. B. LDAP/Kerberos-Dienst),
    # kein Admin-Gateway – entspricht NIST SP 800-207 Zero-Trust-Prinzip.
    # Workstations, MailServer, FileServer und BackupServer sind von der
    # Angreifer-Route strukturell isoliert: sie sind nie erreichbar.
    #   Strukturell geschützte Punkte: WS1+WS2+WS3+Mail+FS+Backup = 90 Pkt
    #   Max. erreichbarer Attacker-Reward: 15+30+100 = 145 von 235 Pkt.
    # Einziger Pfad zur DB: WebServer→AppServer→DB (2 Hops).
    "micro_segmented": {
        "WebServer":        ["AppServer"],
        "AppServer":        ["DatabaseServer", "DomainController"],
        "DomainController": [],
        "MailServer":       [],
        "Workstation1":     [],
        "Workstation2":     [],
        "Workstation3":     [],
        "FileServer":       [],
        "BackupServer":     [],
        "DatabaseServer":   [],
    },

    # ── 5. DEFENSE-IN-DEPTH (hierarchisch, für Attacker-Pretraining) ──────────
    # Vier Schichten mit zwei Ästen, die am DC konvergieren.
    # Alle 10 Knoten erreichbar → geeignet als neutrale Pretraining-Topologie.
    # Kein Vergleichsfall der Bachelorarbeit – dient nur dem Attacker-Training.
    # Schicht 0 (Entry):  WebServer
    # Schicht 1 (DMZ):    WS1, WS2, MailServer
    # Schicht 2 (Intern): WS3, FileServer (aus WS1)
    #                     DomainController (aus WS2 und WS3 – Konvergenz)
    #                     AppServer (aus MailServer)
    # Schicht 3 (Core):   DatabaseServer (aus DC), BackupServer (Sackgasse)
    "defense_in_depth": {
        "WebServer":        ["Workstation1", "Workstation2", "MailServer"],
        "Workstation1":     ["Workstation3", "FileServer"],
        "Workstation2":     ["DomainController"],
        "MailServer":       ["AppServer"],
        "Workstation3":     ["DomainController"],
        "FileServer":       [],
        "AppServer":        ["BackupServer"],
        "BackupServer":     [],
        "DomainController": ["DatabaseServer"],
        "DatabaseServer":   [],
    },

    # ── 6. CHAIN (strikt linear, für Attacker-Pretraining) ────────────────────
    # Jeder Knoten leakt Credential/Node-ID ausschließlich für den nächsten
    # Knoten in der Kette. 9 Hops von WebServer bis DatabaseServer, keine
    # Verzweigungen. Strukturell maximal verschieden von allen vier
    # Vergleichsfällen (die alle Verzweigungen/mehrere Pfade haben) – damit
    # entsteht kein Overlap-Bias zwischen Pretraining- und Testtopologie.
    "chain": {
        "WebServer":        ["Workstation1"],
        "Workstation1":     ["Workstation2"],
        "Workstation2":     ["Workstation3"],
        "Workstation3":     ["MailServer"],
        "MailServer":       ["FileServer"],
        "FileServer":       ["AppServer"],
        "AppServer":        ["BackupServer"],
        "BackupServer":     ["DomainController"],
        "DomainController": ["DatabaseServer"],
        "DatabaseServer":   [],
    },
}

PATTERNS: list[str] = list(ADJACENCY.keys())

# Feste (x, y)-Positionen pro Topologie für die Plotly-Visualisierung.
# Werden als graph.graph['topology_pos'] gespeichert, damit simulation.py
# sie auslesen kann – ohne CBS-Core-Code zu ändern.
POSITIONS: Dict[str, Dict[str, tuple]] = {

    # ── flat: Spread-Layout, viele sichtbare Querverbindungen ─────────────────
    # WebServer links; Services in der Mitte; DC als Admin-Punkt rechts-mitte;
    # Workstations und Storage-Nodes am rechten Rand.
    "flat": {
        "WebServer":        ( 0.0,  2.5),
        "MailServer":       ( 3.0,  4.5),
        "AppServer":        ( 3.0,  2.5),
        "FileServer":       ( 3.0,  0.5),
        "DomainController": ( 6.0,  2.5),
        "Workstation1":     ( 9.0,  5.0),
        "Workstation2":     ( 9.0,  3.5),
        "Workstation3":     ( 9.0,  2.0),
        "BackupServer":     ( 9.0,  0.5),
        "DatabaseServer":   (11.0,  2.5),
    },

    # ── hub_and_spoke: AppServer als zentraler Stern ──────────────────────────
    # WebServer weit links; AppServer im Zentrum; 8 Spokes gleichmäßig verteilt.
    "hub_and_spoke": {
        "WebServer":        (-4.5,  0.0),
        "AppServer":        ( 0.0,  0.0),
        "Workstation1":     ( 0.0,  3.0),
        "MailServer":       ( 2.1,  2.1),
        "DatabaseServer":   ( 3.0,  0.0),
        "BackupServer":     ( 2.1, -2.1),
        "FileServer":       ( 0.0, -3.0),
        "DomainController": (-2.1, -2.1),
        "Workstation3":     (-3.0,  0.0),
        "Workstation2":     (-2.1,  2.1),
    },

    # ── dmz: Zonenlayout von links (Internet) nach rechts (Core) ──────────────
    # Zone 1 (x=0):   WebServer (Internet-Edge / DMZ-Einstieg)
    # Zone 2 (x=3):   MailServer, AppServer (DMZ-Services)
    # Zone 3 (x=6):   DomainController, DatabaseServer (Intranet Core)
    # Zone 4 (x=9-11):Workstations und Storage (Intranet Endpoints)
    "dmz": {
        "WebServer":        ( 0.0,  2.5),
        "MailServer":       ( 3.5,  4.0),
        "AppServer":        ( 3.5,  1.0),
        "DomainController": ( 7.0,  3.5),
        "DatabaseServer":   ( 7.0,  1.0),
        "Workstation1":     (10.0,  5.5),
        "Workstation2":     (10.0,  4.0),
        "Workstation3":     (10.0,  2.5),
        "FileServer":       (10.0,  1.0),
        "BackupServer":     (12.0,  1.0),
    },

    # ── micro_segmented: Reachable-Path links, isolierte Nodes rechts ─────────
    # Erreichbarer Pfad: WebServer → AppServer → {DC (oben), DB (unten)}
    # Strukturell isolierte Nodes: rechts abgesetzt, klar als inaktiv erkennbar.
    "micro_segmented": {
        "WebServer":        ( 0.0,  2.0),
        "AppServer":        ( 3.5,  2.0),
        "DomainController": ( 7.0,  3.5),
        "DatabaseServer":   ( 7.0,  0.5),
        "MailServer":       (11.0,  5.0),
        "Workstation1":     (11.0,  3.5),
        "Workstation2":     (11.0,  2.5),
        "Workstation3":     (11.0,  1.5),
        "FileServer":       (11.0,  0.5),
        "BackupServer":     (13.0,  1.0),
    },

    # ── defense_in_depth: hierarchischer Baum von oben nach unten ────────────
    # Schicht 0 (y=4): WebServer
    # Schicht 1 (y=3): WS1, WS2, MailServer  (3 DMZ-Segmente)
    # Schicht 2 (y=2): WS3, FileServer (linker Ast), DC (Konvergenz), AppServer
    # Schicht 3 (y=1): DatabaseServer (aus DC), BackupServer (Sackgasse)
    "defense_in_depth": {
        "WebServer":        ( 0.0,  4.0),
        "Workstation1":     (-3.0,  3.0),
        "Workstation2":     ( 0.0,  3.0),
        "MailServer":       ( 3.0,  3.0),
        "Workstation3":     (-3.5,  2.0),
        "FileServer":       (-1.5,  2.0),
        "DomainController": ( 0.0,  2.0),
        "AppServer":        ( 3.0,  2.0),
        "DatabaseServer":   ( 0.0,  1.0),
        "BackupServer":     ( 3.0,  1.0),
    },

    # ── chain: strikte Linie von links (Entry) nach rechts (Crown Jewel) ──────
    "chain": {
        "WebServer":        ( 0.0,  2.5),
        "Workstation1":     ( 1.3,  2.5),
        "Workstation2":     ( 2.6,  2.5),
        "Workstation3":     ( 3.9,  2.5),
        "MailServer":       ( 5.2,  2.5),
        "FileServer":       ( 6.5,  2.5),
        "AppServer":        ( 7.8,  2.5),
        "BackupServer":     ( 9.1,  2.5),
        "DomainController": (10.4,  2.5),
        "DatabaseServer":   (11.7,  2.5),
    },
}


# ── Hilfsfunktionen ────────────────────────────────────────────────────────────

def _cached_cred_for(neighbor: str) -> m.CachedCredential:
    """Erzeugt ein CachedCredential-Objekt für einen Nachbar-Knoten."""
    return m.CachedCredential(
        node=neighbor,
        port=NODE_ACCESS_PORT[neighbor],
        credential=CRED_ID[neighbor],
    )


def _make_firewall(node: str, adjacency: Dict[str, List[str]]) -> m.FirewallConfiguration:
    """
    Leitet Firewall-Regeln aus der Adjacency ab:
      OUTGOING: erlaubt die Zugangports aller ausgehenden Nachbarn
      INCOMING: erlaubt den eigenen Zugangport (wenn kein Einstiegsknoten)

    Alle nicht aufgelisteten Ports sind implizit BLOCKED (CBS-Default).
    So erzwingt die Firewall auf Netzwerkebene dieselbe Struktur,
    die die Credential-Leaks auf Anwendungsebene definieren.
    """
    neighbors = adjacency.get(node, [])

    outgoing_ports = sorted({
        NODE_ACCESS_PORT[nb]
        for nb in neighbors
        if nb in NODE_ACCESS_PORT
    })

    # Einstiegsknoten hat keine eigene Credential → kein incoming-Port nötig
    incoming_ports = []
    if node != ENTRY_NODE and node in NODE_ACCESS_PORT:
        incoming_ports = [NODE_ACCESS_PORT[node]]

    return m.FirewallConfiguration(
        outgoing=[m.FirewallRule(p, m.RulePermission.ALLOW) for p in outgoing_ports],
        incoming=[m.FirewallRule(p, m.RulePermission.ALLOW) for p in incoming_ports],
    )


# ── Credential-Map: welche Node-Credentials auf welchem Knoten gecacht sind ────
# GETRENNT von ADJACENCY (Netz-Erreichbarkeit). Kompromittierung von X braucht
# einen Netzpfad zu X (Firewall/Adjacency) UND X's Credential (aus dieser Map).
#   (1) Der DomainController haelt in JEDER Topologie ALLE Credentials (NTDS.dit).
#   (2) Die Credential-Lage folgt der Applikations-/Trust-Nutzung, nicht der
#       Netz-Verkabelung (Web->App->DB-Tiers).
#   (3) Zero-Trust (micro_segmented): der AppServer cacht die DB-Cred NICHT ->
#       das DB-Credential liegt nur beim DC -> Web->App->DC->DB (3 Hops).
def _dc_holds_all(base: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Erweitert eine Credential-Map: der DomainController haelt alle Node-Creds."""
    out = {k: list(v) for k, v in base.items()}
    out["DomainController"] = [n for n in NODE_NAMES
                               if n not in ("DomainController", ENTRY_NODE)]
    return out


CREDENTIAL_MAP: Dict[str, Dict[str, List[str]]] = {
    # Flat: getierte Applikations-Nutzung (NICHT das vollvermaschte Netz!) ->
    # DB-Credential liegt auf dem AppServer -> Web->App->DB bleibt 2 Hops.
    "flat": _dc_holds_all({
        "WebServer":        ["AppServer"],
        "AppServer":        ["DatabaseServer", "DomainController"],
        "MailServer":       ["DomainController"],
        "FileServer":       ["BackupServer", "DomainController"],
        # Alle drei Arbeitsplaetze binden dieselbe Dateiablage ein — genau
        # dafuer existiert ein Dateiserver. Sonst nichts.
        #
        # GEAENDERT 13.08.2026, zwei Punkte:
        #  (1) Frueher hielt Workstation3 stattdessen die AppServer-Cred
        #      (Begruendung war das Betriebssystem: Linux-WS, Linux-AppServer).
        #      Architektonisch schief: In einer Drei-Schichten-Architektur
        #      greifen Benutzer auf die Web-, nicht auf die Anwendungsschicht zu.
        #  (2) Die DC-Cred ist von ALLEN Arbeitsplaetzen entfernt. Sie setzte
        #      voraus, dass sich auf jedem Endgeraet ein privilegiertes Konto
        #      angemeldet und Anmeldedaten hinterlassen hat. Modellannahme:
        #      Administration erfolgt von einem getrennten Geraet, das nicht
        #      Teil des Inventars ist. Der Weg zum DC fuehrt jetzt ueber die
        #      Dienstkonten von Mail- und AppServer.
        "Workstation1":     ["FileServer"],
        "Workstation2":     ["FileServer"],
        "Workstation3":     ["FileServer"],
        "DomainController": [],
        "BackupServer":     [],
        "DatabaseServer":   [],
    }),
    # Hub-and-Spoke: Entry hat nur die AppServer-Cred. Der AppServer cacht wie
    # in flat/dmz die DB-Cred (fest konfigurierte Datenbankverbindung) und die
    # DC-Cred (Authentifizierung am Verzeichnisdienst). Fuer alle uebrigen
    # Knoten liegen die Credentials ausschliesslich beim DC — der Hub allein
    # verschafft also Reichweite, aber keinen Zugang.
    "hub_and_spoke": _dc_holds_all({
        "WebServer":        ["AppServer"],
        "AppServer":        ["DatabaseServer", "DomainController"],
        "DomainController": [],
        "MailServer":       [],
        "Workstation1":     [],
        "Workstation2":     [],
        "Workstation3":     [],
        "FileServer":       [],
        "BackupServer":     [],
        "DatabaseServer":   [],
    }),
    # DMZ: App cacht die DB-Cred direkt (Perimeter, "soft interior") -> DB ohne DC.
    #
    # ZWISCHENZEITLICH GEAENDERT UND WIEDER ZURUECKGENOMMEN (13.08.2026):
    # Kurzzeitig lag die DB-Cred auch hier nur beim DC. Das war falsch, denn
    # damit unterschied sich die DMZ auf der Credential-Ebene nicht mehr von
    # micro_segmented — und "keine dauerhaft gueltigen Zugaenge" ist gerade das
    # Zero-Trust-Merkmal, das micro_segmented ausmacht. Die DMZ haertet den
    # Perimeter, nicht die Credential-Hygiene; das Innere bleibt konventionell.
    "dmz": _dc_holds_all({
        "WebServer":        ["MailServer", "AppServer"],
        "MailServer":       ["DomainController"],
        "AppServer":        ["DatabaseServer", "DomainController"],
        "FileServer":       ["BackupServer"],
        "DomainController": [],
        "Workstation1":     [],
        "Workstation2":     [],
        "Workstation3":     [],
        "BackupServer":     [],
        "DatabaseServer":   [],
    }),
    # Micro-Segmented (Zero-Trust): AppServer OHNE DB-Cred -> DB-Cred nur ueber DC.
    "micro_segmented": _dc_holds_all({
        "WebServer":        ["AppServer"],
        "AppServer":        ["DomainController"],
        "DomainController": [],
        "MailServer":       [],
        "Workstation1":     [],
        "Workstation2":     [],
        "Workstation3":     [],
        "FileServer":       [],
        "BackupServer":     [],
        "DatabaseServer":   [],
    }),
}

# Flat = KEINE Segmentierung -> volle Netz-Erreichbarkeit (jeder erreicht jeden).
# Begruendung: unsegmentiertes Netz als Security-Konzept (nicht "Mesh-Verkabelung").
# Die Credential-Kette bleibt getiert (CREDENTIAL_MAP['flat']) -> DB weiter 2 Hops.
ADJACENCY["flat"] = {n: [x for x in NODE_NAMES if x != n] for n in NODE_NAMES}


def _make_node(node: str, adjacency: Dict[str, List[str]],
               cred_targets: List[str]) -> m.NodeInfo:
    """
    Erzeugt NodeInfo für *node*. cred_targets = Knoten, deren Credentials hier
    gecacht sind (CREDENTIAL_MAP) – getrennt von der Adjacency (Erreichbarkeit).

    Feste Teile  : services, value, properties, reimagable, agent_installed
    Variable Teile: vulnerability outcomes, firewall
    """
    neighbors: List[str] = adjacency.get(node, [])

    # ── Services (fest, topology-unabhängig) ──────────────────────────────────
    if node == ENTRY_NODE:
        # WebServer: von außen erreichbar, keine Credential erforderlich
        services = [m.ListeningService("HTTP"), m.ListeningService("HTTPS")]
    else:
        port = NODE_ACCESS_PORT[node]
        cred = CRED_ID[node]
        services = [m.ListeningService(port, allowedCredentials=[cred])]

    # ── Vulnerability-Outcomes (topology-abhängig) ────────────────────────────
    # Nur Knoten mit CRED_ID können als Ziel einer Credential dienen
    leaked_creds = [
        _cached_cred_for(nb)
        for nb in cred_targets
        if nb in CRED_ID
    ]
    leaked_node_ids = list(neighbors)  # Host-Discovery folgt der Netz-Adjacency

    scan_creds_outcome: m.VulnerabilityOutcome = (
        m.LeakedCredentials(credentials=leaked_creds) if leaked_creds
        else m.ExploitFailed()
    )
    scan_hosts_outcome: m.VulnerabilityOutcome = (
        m.LeakedNodesId(nodes=leaked_node_ids) if leaked_node_ids
        else m.ExploitFailed()
    )

    vulnerabilities = {
        VULN_SCAN_CREDS: m.VulnerabilityInfo(
            description="Durchsuche Credential-Manager / Bash-History nach Zugangsdaten",
            type=m.VulnerabilityType.LOCAL,
            outcome=scan_creds_outcome,
            rates=m.Rates(probingDetectionRate=0.1, exploitDetectionRate=0.2,
                          successRate=1.0),
            cost=1.0,
            reward_string=(
                f"{node}: Credentials für {neighbors} gefunden"
                if neighbors else f"{node}: Keine Credentials gefunden"
            ),
        ),
        VULN_SCAN_HOSTS: m.VulnerabilityInfo(
            description="ARP-Scan / DNS-Lookup – entdecke benachbarte Hosts",
            type=m.VulnerabilityType.LOCAL,
            outcome=scan_hosts_outcome,
            rates=m.Rates(probingDetectionRate=0.05, successRate=1.0),
            cost=1.0,
            reward_string=(
                f"{node}: Hosts entdeckt: {neighbors}"
                if neighbors else f"{node}: Keine benachbarten Hosts"
            ),
        ),
        VULN_REMOTE_PROBE: m.VulnerabilityInfo(
            description="Port-Scan / Banner-Grabbing – Eigenschaften des Ziels ermitteln",
            type=m.VulnerabilityType.REMOTE,
            outcome=m.ProbeSucceeded(discovered_properties=NODE_PROPERTIES[node]),
            rates=m.Rates(probingDetectionRate=0.1, successRate=1.0),
            cost=1.0,
            reward_string=f"Remote-Probe von {node} erfolgreich",
        ),
    }

    return m.NodeInfo(
        services=services,
        value=NODE_VALUES[node],
        properties=NODE_PROPERTIES[node],
        firewall=_make_firewall(node, adjacency),
        agent_installed=(node == ENTRY_NODE),
        reimagable=(node != ENTRY_NODE),
        vulnerabilities=vulnerabilities,
        owned_string=(
            f"[CROWN JEWEL] {node} kompromittiert!"
            if node == TARGET_NODE
            else f"{node} kompromittiert"
        ),
    )


def make_environment(pattern: str) -> m.Environment:
    """
    Erzeugt ein CBS-Environment für das angegebene Topologie-Muster.

    Parameters
    ----------
    pattern : str
        Eines von "flat", "hub_and_spoke", "dmz", "micro_segmented",
        "defense_in_depth", "chain".

    Returns
    -------
    m.Environment – direkt an CyberBattleEnv übergebbar.
    """
    if pattern not in ADJACENCY:
        raise ValueError(
            f"Unbekanntes Muster '{pattern}'. Verfügbar: {PATTERNS}"
        )

    adjacency = ADJACENCY[pattern]
    # Credential-Lage getrennt von der Netz-Adjacency (s. CREDENTIAL_MAP).
    # Fallback fuer nicht-Vergleichstopologien (chain, defense_in_depth):
    # Credentials = Nachbarn (bisheriges Verhalten, unveraendert).
    cred_map = CREDENTIAL_MAP.get(pattern, adjacency)
    nodes = {name: _make_node(name, adjacency, cred_map.get(name, []))
             for name in NODE_NAMES}
    network = m.create_network(nodes)

    # Feste Positionen als Graph-Attribut speichern.
    # simulation.py liest 'topology_pos' aus, falls vorhanden,
    # und ersetzt damit nx.shell_layout – kein CBS-Core-Code nötig.
    network.graph['topology_pos'] = POSITIONS[pattern]

    # Adjacency ebenfalls am Graphen hinterlegen. Der Verteidiger-Wrapper
    # braucht die echten Vorgaengerknoten, um den Abwehrbonus als Kantenbilanz
    # zu rechnen. Aus der Firewall allein ist das nicht ableitbar: Der Netzgraph
    # hat zur Laufzeit keine Kanten, und Ports sind mehrdeutig (SSH bedienen
    # Workstation 1 bis 3, SMB bedienen File- und BackupServer).
    network.graph['thesis_adjacency'] = {k: list(v) for k, v in adjacency.items()}

    return m.Environment(
        network=network,
        vulnerability_library={},   # alle Vulns sind node-lokal definiert
        identifiers=ENV_IDENTIFIERS,
    )
