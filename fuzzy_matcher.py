from difflib import SequenceMatcher
from typing import List, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """RÃ©sultat de correspondance"""
    spot_name: str
    recording_name: str
    start_time: str
    start_seconds: float
    confidence: float
    matched_text: str
    match_type: str
    end_time: str = ""
    end_seconds: float = 0.0


class FuzzyMatcher:
    """DÃ©tection de correspondance avec tolÃ©rance aux erreurs"""
    
    def __init__(self, threshold: int = 85, max_distance: int = 2):
        self.threshold = threshold
        self.max_distance = max_distance
    
    @staticmethod
    def similarity_ratio(s1: str, s2: str) -> float:
        """Ratio de similaritÃ© (0-100)"""
        matcher = SequenceMatcher(None, s1.lower(), s2.lower())
        return matcher.ratio() * 100
    
    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """Distance de Levenshtein"""
        if len(s1) < len(s2):
            return FuzzyMatcher.levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def find_in_text(
        self,
        needle: str,
        haystack: str
    ) -> Tuple[Optional[str], float]:
        """
        Chercher needle dans haystack avec tolÃ©rance
        
        Returns:
            (texte_trouvÃ©, confiance)
        """
        needle_lower = needle.lower().strip()
        haystack_lower = haystack.lower().strip()
        
        # Recherche exacte
        if needle_lower in haystack_lower:
            return (needle, 100.0)
        
        # Recherche floue par fenÃªtre glissante
        needle_len = len(needle_lower)
        best_match = None
        best_confidence = 0
        
        for i in range(len(haystack_lower) - needle_len + 1):
            window = haystack_lower[i:i + needle_len]
            similarity = self.similarity_ratio(needle_lower, window)
            
            if similarity > best_confidence:
                best_confidence = similarity
                best_match = window
        
        if best_confidence >= self.threshold:
            return (best_match, best_confidence)
        
        return (None, 0.0)
