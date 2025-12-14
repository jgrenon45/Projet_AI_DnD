"""
Base de donnees etendue pour D&D 5e
Gestion des monstres, sorts et items magiques
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional


class MonsterDatabase:
    """Base de donnees des monstres"""
    
    def __init__(self, csv_path: str = "data/fichier_csv/Monsters.csv"):
        self.csv_path = Path(csv_path)
        self.extra_path = Path("data/fichier_csv/Monsters_extra.csv")
        self.df = None
        self.load_data()
    
    def load_data(self):
        dfs = []
        
        # Charger le fichier principal
        if self.csv_path.exists():
            try:
                df_main = pd.read_csv(self.csv_path)
                dfs.append(df_main)
                print(f"[DB] {len(df_main)} monstres charges (principal)")
            except Exception as e:
                print(f"[DB] Erreur chargement monstres principal: {e}")
        
        # Charger le fichier supplementaire
        if self.extra_path.exists():
            try:
                df_extra = pd.read_csv(self.extra_path)
                dfs.append(df_extra)
                print(f"[DB] {len(df_extra)} monstres charges (supplementaire)")
            except Exception as e:
                print(f"[DB] Erreur chargement monstres extra: {e}")
        
        # Fusionner
        if dfs:
            self.df = pd.concat(dfs, ignore_index=True)
            # Supprimer les doublons par nom
            self.df = self.df.drop_duplicates(subset=['name'], keep='last')
            print(f"[DB] Total: {len(self.df)} monstres uniques")
        else:
            print(f"[DB] Aucun fichier monstre trouve")
            self.df = pd.DataFrame()
    
    def search(self, name: str) -> Optional[Dict]:
        if self.df is None or self.df.empty:
            return None
        
        # Recherche exacte
        result = self.df[self.df['name'].str.lower() == name.lower()]
        if not result.empty:
            return result.iloc[0].to_dict()
        
        # Recherche partielle
        result = self.df[self.df['name'].str.contains(name, case=False, na=False)]
        if not result.empty:
            return result.iloc[0].to_dict()
        
        return None
    
    def search_multiple(self, name: str, limit: int = 10) -> List[Dict]:
        if self.df is None or self.df.empty:
            return []
        
        result = self.df[self.df['name'].str.contains(name, case=False, na=False)]
        return result.head(limit).to_dict('records')
    
    def get_by_cr(self, cr_min: float = 0, cr_max: float = 30) -> List[Dict]:
        if self.df is None or self.df.empty:
            return []
        
        df = self.df.copy()
        if 'cr' in df.columns:
            df['cr_num'] = pd.to_numeric(df['cr'], errors='coerce')
            result = df[(df['cr_num'] >= cr_min) & (df['cr_num'] <= cr_max)]
            return result.to_dict('records')
        return []
    
    def get_types(self) -> List[str]:
        if self.df is None or self.df.empty or 'type' not in self.df.columns:
            return []
        return sorted(self.df['type'].dropna().unique().tolist())


class SpellDatabase:
    """Base de donnees des sorts"""
    
    def __init__(self, csv_path: str = "data/fichier_csv/Spells.csv"):
        self.csv_path = Path(csv_path)
        self.df = None
        self.load_data()
    
    def load_data(self):
        if self.csv_path.exists():
            try:
                self.df = pd.read_csv(self.csv_path)
                print(f"[DB] {len(self.df)} sorts charges")
            except Exception as e:
                print(f"[DB] Erreur chargement sorts: {e}")
                self.df = pd.DataFrame()
        else:
            print(f"[DB] Fichier sorts non trouve: {self.csv_path}")
            self.df = pd.DataFrame()
    
    def search(self, name: str) -> Optional[Dict]:
        if self.df is None or self.df.empty:
            return None
        
        result = self.df[self.df['name'].str.lower() == name.lower()]
        if not result.empty:
            return result.iloc[0].to_dict()
        
        result = self.df[self.df['name'].str.contains(name, case=False, na=False)]
        if not result.empty:
            return result.iloc[0].to_dict()
        
        return None
    
    def search_multiple(self, name: str, limit: int = 10) -> List[Dict]:
        if self.df is None or self.df.empty:
            return []
        
        result = self.df[self.df['name'].str.contains(name, case=False, na=False)]
        return result.head(limit).to_dict('records')
    
    def get_by_level(self, level: str) -> List[Dict]:
        if self.df is None or self.df.empty:
            return []
        
        result = self.df[self.df['level'].str.lower() == level.lower()]
        return result.to_dict('records')
    
    def get_by_class(self, class_name: str) -> List[Dict]:
        if self.df is None or self.df.empty:
            return []
        
        result = self.df[self.df['classes'].str.contains(class_name, case=False, na=False)]
        return result.to_dict('records')
    
    def get_schools(self) -> List[str]:
        if self.df is None or self.df.empty or 'school' not in self.df.columns:
            return []
        return sorted(self.df['school'].dropna().unique().tolist())
    
    def get_levels(self) -> List[str]:
        if self.df is None or self.df.empty or 'level' not in self.df.columns:
            return []
        levels = self.df['level'].dropna().unique().tolist()
        # Trier: cantrip en premier, puis 1-9
        order = ['cantrip', '1', '2', '3', '4', '5', '6', '7', '8', '9']
        return [l for l in order if l in levels]


class ItemDatabase:
    """Base de donnees des items"""
    
    def __init__(self, csv_path: str = "data/fichier_csv/Items.csv"):
        self.csv_path = Path(csv_path)
        self.magic_path = Path("data/fichier_csv/Items_magic.csv")
        self.df = None
        self.load_data()
    
    def load_data(self):
        dfs = []
        
        # Charger le fichier principal
        if self.csv_path.exists():
            try:
                df_main = pd.read_csv(self.csv_path)
                dfs.append(df_main)
                print(f"[DB] {len(df_main)} items charges (principal)")
            except Exception as e:
                print(f"[DB] Erreur chargement items principal: {e}")
        
        # Charger les items magiques
        if self.magic_path.exists():
            try:
                df_magic = pd.read_csv(self.magic_path)
                dfs.append(df_magic)
                print(f"[DB] {len(df_magic)} items magiques charges")
            except Exception as e:
                print(f"[DB] Erreur chargement items magiques: {e}")
        
        # Fusionner
        if dfs:
            self.df = pd.concat(dfs, ignore_index=True)
            self.df = self.df.drop_duplicates(subset=['name'], keep='last')
            print(f"[DB] Total: {len(self.df)} items uniques")
        else:
            print(f"[DB] Aucun fichier item trouve")
            self.df = pd.DataFrame()
    
    def search(self, name: str) -> Optional[Dict]:
        if self.df is None or self.df.empty:
            return None
        
        result = self.df[self.df['name'].str.lower() == name.lower()]
        if not result.empty:
            return result.iloc[0].to_dict()
        
        result = self.df[self.df['name'].str.contains(name, case=False, na=False)]
        if not result.empty:
            return result.iloc[0].to_dict()
        
        return None
    
    def search_multiple(self, name: str, limit: int = 10) -> List[Dict]:
        if self.df is None or self.df.empty:
            return []
        
        result = self.df[self.df['name'].str.contains(name, case=False, na=False)]
        return result.head(limit).to_dict('records')
    
    def get_by_rarity(self, rarity: str) -> List[Dict]:
        if self.df is None or self.df.empty:
            return []
        
        result = self.df[self.df['rarity'].str.lower() == rarity.lower()]
        return result.to_dict('records')
    
    def get_by_category(self, category: str) -> List[Dict]:
        if self.df is None or self.df.empty:
            return []
        
        result = self.df[self.df['category'].str.contains(category, case=False, na=False)]
        return result.to_dict('records')
    
    def get_magic_items(self) -> List[Dict]:
        """Retourne les items magiques (rarete > COMMON)"""
        if self.df is None or self.df.empty:
            return []
        
        magic_rarities = ['UNCOMMON', 'RARE', 'VERY RARE', 'LEGENDARY', 'ARTIFACT']
        result = self.df[self.df['rarity'].str.upper().isin(magic_rarities)]
        return result.to_dict('records')
    
    def get_rarities(self) -> List[str]:
        if self.df is None or self.df.empty or 'rarity' not in self.df.columns:
            return []
        return sorted(self.df['rarity'].dropna().unique().tolist())
    
    def get_categories(self) -> List[str]:
        if self.df is None or self.df.empty or 'category' not in self.df.columns:
            return []
        return sorted(self.df['category'].dropna().unique().tolist())
