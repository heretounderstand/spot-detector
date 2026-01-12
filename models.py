from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import re


@dataclass
class Chaine:
    """Modèle pour une chaîne TV"""
    id: Optional[int]
    chaine_id: str  # Identifiant dans nom fichier (ex: "CRTV", "3")
    chaine_nom: str  # Nom affiché (ex: "CRTV", "Canal 3")
    date_ajout: datetime


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
    chaine_id: str
    chaine_nom: str
    date_enreg: str  # YYYY-MM-DD
    heure_debut: str  # HH:MM:SS
    heure_fin: str  # HH:MM:SS
    contenu_srt: str
    date_ajout: datetime
    
    @classmethod
    def from_filename(cls, filename: str, content: str, chaine_nom: str = None) -> Optional['Enregistrement']:
        """Parser le nom: CHAINE_YYYY-MM-DD_HH-MM-SS_HH-MM-SS.srt (CHAINE peut être texte ou nombre)"""
        pattern = r'^([^_]+)_(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})\.srt$'
        match = re.match(pattern, filename)
        
        if not match:
            return None
        
        chaine_id, date, debut, fin = match.groups()
        
        return cls(
            id=None,
            nom_fichier=filename,
            chaine_id=chaine_id,
            chaine_nom=chaine_nom or chaine_id,
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
    enreg_chaine_id: Optional[str] = None
    enreg_chaine_nom: Optional[str] = None
    enreg_date: Optional[str] = None
