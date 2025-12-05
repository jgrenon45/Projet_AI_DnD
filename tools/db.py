"""
Database management for D&D Assistant
Handles monster data from CSV and vector storage for RAG
"""

import pandas as pd
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
import json


class MonsterDatabase:
    """Manages monster data from a CSV file for the D&D assistant"""
    
    def __init__(self, csv_path: str = "data/monsters/monsters.csv"):
        """
        Initialize the MonsterDatabase.
        
        Args:
            csv_path (str): Path to the CSV file containing monster data.
        """
        # Store the path as a Path object for easier path operations
        self.csv_path = Path(csv_path)
        
        # This will hold the monster data as a pandas DataFrame
        self.df = None
        
        # Load monsters immediately when creating the object
        self.load_monsters()
    
    def load_monsters(self):
        """
        Load monsters from CSV file into a pandas DataFrame.
        Handles errors and missing files gracefully.
        """
        if self.csv_path.exists():
            try:
                # Read CSV into a DataFrame
                self.df = pd.read_csv(self.csv_path)
                
                # Print the number of monsters loaded
                print(f"Loaded {len(self.df)} monsters from database")
            except Exception as e:
                # If reading CSV fails, print the error and use empty DataFrame
                print(f"Error loading monsters: {e}")
                self.df = pd.DataFrame()
        else:
            # File does not exist, initialize empty DataFrame
            print(f"Monster file not found: {self.csv_path}")
            self.df = pd.DataFrame()
    
    def search_monster(self, name: str) -> Optional[Dict]:
        """
        Search for a monster by name.
        
        Args:
            name (str): Name of the monster to search for.
        
        Returns:
            Optional[Dict]: Returns monster data as a dictionary if found, else None.
        """
        if self.df is None or self.df.empty:
            # No data available
            return None
        
        # Exact match (case-insensitive)
        result = self.df[self.df['name'].str.lower() == name.lower()]
        if not result.empty:
            # Return the first matching monster as a dict
            return result.iloc[0].to_dict()
        
        # Partial match if exact not found
        result = self.df[self.df['name'].str.contains(name, case=False, na=False)]
        if not result.empty:
            return result.iloc[0].to_dict()
        
        # No match found
        return None
    
    def get_monsters_by_cr(self, cr_min: float = 0, cr_max: float = 30) -> List[Dict]:
        """
        Get monsters within a specified Challenge Rating (CR) range.
        
        Args:
            cr_min (float): Minimum CR (inclusive)
            cr_max (float): Maximum CR (inclusive)
        
        Returns:
            List[Dict]: List of monsters that fall within the CR range
        """
        if self.df is None or self.df.empty:
            # No data available
            return []
        
        # Make a copy of DataFrame to avoid modifying the original
        df_filtered = self.df.copy()
        
        if 'cr' in df_filtered.columns:
            # Convert the 'cr' column to numeric, non-convertible values become NaN
            df_filtered['cr_numeric'] = pd.to_numeric(df_filtered['cr'], errors='coerce')
            
            # Filter monsters by CR range
            result = df_filtered[
                (df_filtered['cr_numeric'] >= cr_min) & 
                (df_filtered['cr_numeric'] <= cr_max)
            ]
            
            # Convert filtered DataFrame to a list of dictionaries
            return result.to_dict('records')
        
        # If 'cr' column doesn't exist, return empty list
        return []
    
    def get_all_monsters(self) -> List[Dict]:
        """Return all monsters as a list of dictionaries."""
        if self.df is None or self.df.empty:
            return []
        return self.df.to_dict('records')
    
    def get_monster_types(self) -> List[str]:
        """
        Return a sorted list of unique monster types.
        Useful for filtering by type in the UI or logic.
        """
        if self.df is None or self.df.empty:
            return []
        if 'type' in self.df.columns:
            # Drop any missing types and return sorted unique values
            return sorted(self.df['type'].dropna().unique().tolist())
        return []
    
    def search_by_type(self, monster_type: str) -> List[Dict]:
        """
        Search monsters by type (case-insensitive, partial match).
        
        Args:
            monster_type (str): Type of monsters to search for
        
        Returns:
            List[Dict]: List of monsters matching the type
        """
        if self.df is None or self.df.empty:
            return []
        
        if 'type' in self.df.columns:
            # Filter rows where 'type' contains the search string
            result = self.df[self.df['type'].str.contains(monster_type, case=False, na=False)]
            return result.to_dict('records')
        return []


class CampaignDatabase:
    """Manages campaign data and session history using SQLite"""
    
    def __init__(self, db_path: str = "data/campaign.db"):
        """
        Initialize the CampaignDatabase.
        
        Args:
            db_path (str): Path to the SQLite database file
        """
        # Convert path to Path object for convenience
        self.db_path = Path(db_path)
        
        # Ensure that the parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database tables if they do not exist
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database tables for sessions, NPCs, locations, and encounters."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                title TEXT,
                notes TEXT,
                summary TEXT
            )
        ''')
        
        # Create NPCs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS npcs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                race TEXT,
                class TEXT,
                description TEXT,
                location TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create locations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create encounters table (links monsters to sessions)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS encounters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                monsters TEXT,  -- JSON string of monsters
                difficulty TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        ''')
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        print("Campaign database initialized")
    
    def add_session(self, title: str, notes: str = "", summary: str = "") -> int:
        """
        Add a new session to the database.
        
        Args:
            title (str): Session title
            notes (str): Optional notes
            summary (str): Optional summary
        
        Returns:
            int: ID of the inserted session
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (title, notes, summary) VALUES (?, ?, ?)",
            (title, notes, summary)
        )
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return session_id
    
    def add_npc(self, name: str, race: str = "", 
                class_name: str = "", description: str = "", location: str = "") -> int:
        """
        Add a new NPC to the database.
        
        Args:
            name (str): NPC name
            race (str): NPC race
            class_name (str): NPC class
            description (str): NPC description
            location (str): NPC location
        
        Returns:
            int: ID of the inserted NPC
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO npcs (name, race, class, description, location) VALUES (?, ?, ?, ?, ?)",
            (name, race, class_name, description, location)
        )
        npc_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return npc_id
    
    def get_all_npcs(self) -> List[Dict]:
        """
        Retrieve all NPCs from the database.
        
        Returns:
            List[Dict]: List of NPC dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        # Make rows accessible as dictionaries
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM npcs ORDER BY name")
        npcs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return npcs
    
    def get_recent_sessions(self, limit: int = 10) -> List[Dict]:
        """
        Retrieve recent sessions, ordered by most recent first.
        
        Args:
            limit (int): Maximum number of sessions to return
        
        Returns:
            List[Dict]: List of recent session dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions ORDER BY session_date DESC LIMIT ?", (limit,))
        sessions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return sessions
