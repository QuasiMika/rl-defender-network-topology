"""
pytest-Konfiguration: stellt sicher, dass das Repo-Wurzelverzeichnis im
Python-Pfad liegt, damit "thesis_topology" und "cyberbattle" importierbar sind.
"""
import sys
import os

# Wurzelverzeichnis des Repositorys (eine Ebene ueber thesis_topology/)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
