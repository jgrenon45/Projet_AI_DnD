#!/usr/bin/env python3
"""
Le Grimoire du Maitre du Donjon v2
Assistant IA pour D&D 5e

Lancement: python run.py
"""

import sys
from pathlib import Path

# Ajouter le repertoire racine au path
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

# Changer le repertoire de travail
import os
os.chdir(root_dir)


def main():
    print("=" * 50)
    print("  LE GRIMOIRE DU MAITRE DU DONJON v2")
    print("  Assistant IA pour D&D 5e")
    print("=" * 50)
    print()
    print("Demarrage de l'interface...")
    print()
    
    try:
        from tools.UserGUI.GUI_v4 import DnDAssistantGUI
        app = DnDAssistantGUI()
        app.run()
    except ImportError as e:
        print(f"Erreur d'import: {e}")
        print()
        print("Verifiez que les dependances sont installees:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Erreur: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
