from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import re


@dataclass
class Spot:
    """Modèle pour un spot publicitaire"""
    id: Optional[int]
    nom_campagne: str
    contenu_srt: str
    date_ajout: datetime
    
    @classmethod
    def from_filename(cls, filename: str, content: str) -> 'Spot':
        """Créer un spot depuis un nom de fichier"""
        nom = filename.replace('.srt', '')
        return cls(
            id=None,
            nom_campagne=nom,
            contenu_srt=content,
            date_ajout=datetime.now()
        )


@dataclass
class Enregistrement:
    """Modèle pour un enregistrement"""
    id: Optional[int]
    nom_fichier: str
    chaine: str
    date_enreg: str  # YYYY-MM-DD
    heure_debut: str  # HH:MM:SS
    heure_fin: str  # HH:MM:SS
    contenu_srt: str
    date_ajout: datetime
    
    @classmethod
    def from_filename(cls, filename: str, content: str) -> Optional['Enregistrement']:
        """Parser le nom: 3_2025-12-29_05-31-25_06-01-26.srt"""
        pattern = r'^(\d+)_(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})\.srt$'
        match = re.match(pattern, filename)
        
        if not match:
            return None
        
        chaine, date, debut, fin = match.groups()
        
        return cls(
            id=None,
            nom_fichier=filename,
            chaine=chaine,
            date_enreg=date,
            heure_debut=debut.replace('-', ':'),
            heure_fin=fin.replace('-', ':'),
            contenu_srt=content,
            date_ajout=datetime.now()
        )


@dataclass
class Detection:
    """Modèle pour une détection"""
    id: Optional[int]
    spot_id: int
    enregistrement_id: int
    start_time: str
    end_time: str
    start_seconds: float
    end_seconds: float
    confidence: float
    match_type: str
    date_detection: datetime
    
    # Données enrichies (jointures)
    spot_nom: Optional[str] = None
    enreg_nom: Optional[str] = None
    enreg_chaine: Optional[str] = None
    enreg_date: Optional[str] = None