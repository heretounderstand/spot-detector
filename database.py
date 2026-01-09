import sqlite3
from typing import List, Optional, Dict
from datetime import datetime
from models import Spot, Enregistrement, Detection
import logging

logger = logging.getLogger(__name__)


class Database:
    """Couche d'accès aux données SQLite"""
    
    def __init__(self, db_path: str = "spots.db"):
        self.db_path = db_path
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS spots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom_campagne TEXT NOT NULL UNIQUE,
                contenu_srt TEXT NOT NULL,
                date_ajout TIMESTAMP NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS enregistrements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom_fichier TEXT NOT NULL UNIQUE,
                chaine TEXT NOT NULL,
                date_enreg TEXT NOT NULL,
                heure_debut TEXT NOT NULL,
                heure_fin TEXT NOT NULL,
                contenu_srt TEXT NOT NULL,
                date_ajout TIMESTAMP NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_enreg_chaine ON enregistrements(chaine)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_enreg_date ON enregistrements(date_enreg)
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                spot_id INTEGER NOT NULL,
                enregistrement_id INTEGER NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                start_seconds REAL NOT NULL,
                end_seconds REAL NOT NULL,
                confidence REAL NOT NULL,
                match_type TEXT NOT NULL,
                date_detection TIMESTAMP NOT NULL,
                FOREIGN KEY (spot_id) REFERENCES spots(id) ON DELETE CASCADE,
                FOREIGN KEY (enregistrement_id) REFERENCES enregistrements(id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_detection_spot ON detections(spot_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_detection_enreg ON detections(enregistrement_id)
        """)
        
        conn.commit()
        conn.close()
    
    # ==================== SPOTS ====================
    
    def add_spot(self, spot: Spot) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO spots (nom_campagne, contenu_srt, date_ajout)
                VALUES (?, ?, ?)
            """, (spot.nom_campagne, spot.contenu_srt, spot.date_ajout))
            spot_id = cursor.lastrowid
            conn.commit()
            return spot_id
        except sqlite3.IntegrityError:
            cursor.execute("SELECT id FROM spots WHERE nom_campagne = ?", (spot.nom_campagne,))
            row = cursor.fetchone()
            return row['id'] if row else None
        finally:
            conn.close()
    
    def get_all_spots(self) -> List[Spot]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM spots ORDER BY date_ajout DESC")
        rows = cursor.fetchall()
        conn.close()
        
        return [
            Spot(
                id=row['id'],
                nom_campagne=row['nom_campagne'],
                contenu_srt=row['contenu_srt'],
                date_ajout=datetime.fromisoformat(row['date_ajout'])
            )
            for row in rows
        ]
    
    def get_spot_by_id(self, spot_id: int) -> Optional[Spot]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM spots WHERE id = ?", (spot_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return Spot(
            id=row['id'],
            nom_campagne=row['nom_campagne'],
            contenu_srt=row['contenu_srt'],
            date_ajout=datetime.fromisoformat(row['date_ajout'])
        )
    
    def delete_spot(self, spot_id: int) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM spots WHERE id = ?", (spot_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
    
    # ==================== ENREGISTREMENTS ====================
    
    def add_enregistrement(self, enreg: Enregistrement) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO enregistrements 
                (nom_fichier, chaine, date_enreg, heure_debut, heure_fin, contenu_srt, date_ajout)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                enreg.nom_fichier, enreg.chaine, enreg.date_enreg,
                enreg.heure_debut, enreg.heure_fin, enreg.contenu_srt, enreg.date_ajout
            ))
            enreg_id = cursor.lastrowid
            conn.commit()
            return enreg_id
        except sqlite3.IntegrityError:
            cursor.execute("SELECT id FROM enregistrements WHERE nom_fichier = ?", (enreg.nom_fichier,))
            row = cursor.fetchone()
            return row['id'] if row else None
        finally:
            conn.close()
    
    def get_all_enregistrements(self) -> List[Enregistrement]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM enregistrements ORDER BY date_enreg DESC, heure_debut DESC")
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_enregistrement(row) for row in rows]
    
    def get_enregistrements_by_filters(
        self, 
        chaines: Optional[List[str]] = None,
        date_debut: Optional[str] = None,
        date_fin: Optional[str] = None
    ) -> List[Enregistrement]:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM enregistrements WHERE 1=1"
        params = []
        
        if chaines:
            placeholders = ','.join('?' * len(chaines))
            query += f" AND chaine IN ({placeholders})"
            params.extend(chaines)
        
        if date_debut:
            query += " AND date_enreg >= ?"
            params.append(date_debut)
        
        if date_fin:
            query += " AND date_enreg <= ?"
            params.append(date_fin)
        
        query += " ORDER BY date_enreg DESC, heure_debut DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_enregistrement(row) for row in rows]
    
    def get_enregistrement_by_id(self, enreg_id: int) -> Optional[Enregistrement]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM enregistrements WHERE id = ?", (enreg_id,))
        row = cursor.fetchone()
        conn.close()
        return self._row_to_enregistrement(row) if row else None
    
    def delete_enregistrement(self, enreg_id: int) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM enregistrements WHERE id = ?", (enreg_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
    
    def get_all_chaines(self) -> List[str]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT chaine FROM enregistrements ORDER BY chaine")
        rows = cursor.fetchall()
        conn.close()
        return [row['chaine'] for row in rows]
    
    @staticmethod
    def _row_to_enregistrement(row) -> Enregistrement:
        return Enregistrement(
            id=row['id'],
            nom_fichier=row['nom_fichier'],
            chaine=row['chaine'],
            date_enreg=row['date_enreg'],
            heure_debut=row['heure_debut'],
            heure_fin=row['heure_fin'],
            contenu_srt=row['contenu_srt'],
            date_ajout=datetime.fromisoformat(row['date_ajout'])
        )
    
    # ==================== DETECTIONS ====================
    
    def add_detection(self, detection: Detection) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO detections 
            (spot_id, enregistrement_id, start_time, end_time, start_seconds, 
             end_seconds, confidence, match_type, date_detection)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            detection.spot_id, detection.enregistrement_id,
            detection.start_time, detection.end_time,
            detection.start_seconds, detection.end_seconds,
            detection.confidence, detection.match_type, detection.date_detection
        ))
        
        detection_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return detection_id
    
    def get_detections_enriched(
        self,
        spot_ids: Optional[List[int]] = None,
        enreg_ids: Optional[List[int]] = None,
        chaines: Optional[List[str]] = None,
        date_debut: Optional[str] = None,
        date_fin: Optional[str] = None
    ) -> List[Detection]:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT 
                d.*,
                s.nom_campagne as spot_nom,
                e.nom_fichier as enreg_nom,
                e.chaine as enreg_chaine,
                e.date_enreg as enreg_date
            FROM detections d
            JOIN spots s ON d.spot_id = s.id
            JOIN enregistrements e ON d.enregistrement_id = e.id
            WHERE 1=1
        """
        params = []
        
        if spot_ids:
            placeholders = ','.join('?' * len(spot_ids))
            query += f" AND d.spot_id IN ({placeholders})"
            params.extend(spot_ids)
        
        if enreg_ids:
            placeholders = ','.join('?' * len(enreg_ids))
            query += f" AND d.enregistrement_id IN ({placeholders})"
            params.extend(enreg_ids)
        
        if chaines:
            placeholders = ','.join('?' * len(chaines))
            query += f" AND e.chaine IN ({placeholders})"
            params.extend(chaines)
        
        if date_debut:
            query += " AND e.date_enreg >= ?"
            params.append(date_debut)
        
        if date_fin:
            query += " AND e.date_enreg <= ?"
            params.append(date_fin)
        
        query += " ORDER BY e.date_enreg DESC, d.start_seconds ASC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [
            Detection(
                id=row['id'],
                spot_id=row['spot_id'],
                enregistrement_id=row['enregistrement_id'],
                start_time=row['start_time'],
                end_time=row['end_time'],
                start_seconds=row['start_seconds'],
                end_seconds=row['end_seconds'],
                confidence=row['confidence'],
                match_type=row['match_type'],
                date_detection=datetime.fromisoformat(row['date_detection']),
                spot_nom=row['spot_nom'],
                enreg_nom=row['enreg_nom'],
                enreg_chaine=row['enreg_chaine'],
                enreg_date=row['enreg_date']
            )
            for row in rows
        ]
    
    def delete_detections_by_spot(self, spot_id: int):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM detections WHERE spot_id = ?", (spot_id,))
        conn.commit()
        conn.close()
    
    def get_stats(self) -> Dict:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM spots")
        nb_spots = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM enregistrements")
        nb_enreg = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM detections")
        nb_detections = cursor.fetchone()['count']
        
        cursor.execute("SELECT AVG(confidence) as avg FROM detections")
        avg_conf = cursor.fetchone()['avg'] or 0
        
        conn.close()
        
        return {
            'nb_spots': nb_spots,
            'nb_enregistrements': nb_enreg,
            'nb_detections': nb_detections,
            'avg_confidence': avg_conf
        }