from typing import List, Dict
from srt_parser import Subtitle, SRTParser
from fuzzy_matcher import FuzzyMatcher
from models import Detection
from config import DEFAULT_THRESHOLD, DEFAULT_MAX_DISTANCE
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SpotDetector:
    """Détecteur segment-à-segment avec calcul de position réelle du spot"""
    
    def __init__(self):
        self.matcher = FuzzyMatcher(
            threshold=DEFAULT_THRESHOLD,
            max_distance=DEFAULT_MAX_DISTANCE
        )
    
    def detect_spot_in_enregistrements(
        self,
        spot_id: int,
        spot_content: str,
        enregistrements: List[tuple]  # [(enreg_id, enreg_content, heure_debut), ...]
    ) -> List[Detection]:
        """Détecter un spot dans plusieurs enregistrements"""
        parser = SRTParser()
        spot_subtitles = parser.parse(spot_content)
        
        if not spot_subtitles:
            logger.warning("Aucun segment trouvé dans le spot")
            return []
        
        spot_duration = spot_subtitles[-1].end_seconds
        spot_start_time = spot_subtitles[0].start_seconds
        
        all_detections = []
        
        for enreg_id, enreg_content, heure_debut in enregistrements:
            recording_subtitles = parser.parse(enreg_content)
            
            if not recording_subtitles:
                logger.warning(f"Aucun segment trouvé dans enreg_id={enreg_id}")
                continue
            
            for spot_segment in spot_subtitles:
                segment_pos_in_spot = spot_segment.start_seconds - spot_start_time
                
                matches = self._find_segment_in_recording(
                    spot_id,
                    enreg_id,
                    spot_segment,
                    recording_subtitles,
                    segment_pos_in_spot,
                    spot_duration,
                    heure_debut
                )
                all_detections.extend(matches)
        
        return self._filter_and_group_matches(all_detections, spot_duration)
    
    def _find_segment_in_recording(
        self,
        spot_id: int,
        enreg_id: int,
        spot_segment: Subtitle,
        recording_subtitles: List[Subtitle],
        segment_pos_in_spot: float,
        spot_duration: float,
        heure_debut: str
    ) -> List[Detection]:
        """Chercher un segment du spot dans l'enregistrement"""
        matches = []
        spot_text = spot_segment.text
        
        # Convertir heure_debut en secondes depuis minuit
        base_seconds = self._time_to_seconds(heure_debut)
        
        for rec_subtitle in recording_subtitles:
            matched_text, confidence = self.matcher.find_in_text(
                spot_text,
                rec_subtitle.text
            )
            
            if matched_text and confidence >= self.matcher.threshold:
                estimated_spot_start = rec_subtitle.start_seconds - segment_pos_in_spot
                estimated_spot_end = estimated_spot_start + spot_duration
                
                # Calculer l'heure réelle dans la journée
                real_start_seconds = base_seconds + estimated_spot_start
                real_end_seconds = base_seconds + estimated_spot_end
                
                match = Detection(
                    id=None,
                    spot_id=spot_id,
                    enregistrement_id=enreg_id,
                    start_time=self._seconds_to_time(real_start_seconds),
                    start_seconds=real_start_seconds,
                    end_time=self._seconds_to_time(real_end_seconds),
                    end_seconds=real_end_seconds,
                    confidence=confidence,
                    match_type="exact" if confidence == 100 else "fuzzy",
                    date_detection=datetime.now()
                )
                matches.append(match)
        
        return matches
    
    def _filter_and_group_matches(self, matches: List[Detection], spot_duration: float) -> List[Detection]:
        """
        Filtrer doublons intelligemment:
        - Si plusieurs détections du même spot avec débuts < durée_spot, garder la plus ancienne
        - Sinon ce sont des spots différents
        """
        if not matches:
            return matches
        
        by_enreg: Dict[int, List[Detection]] = {}
        for match in matches:
            key = match.enregistrement_id
            if key not in by_enreg:
                by_enreg[key] = []
            by_enreg[key].append(match)
        
        filtered = []
        
        for enreg_id, enreg_matches in by_enreg.items():
            enreg_matches_sorted = sorted(enreg_matches, key=lambda m: m.start_seconds)
            
            kept = []
            i = 0
            
            while i < len(enreg_matches_sorted):
                current = enreg_matches_sorted[i]
                same_spot_group = [current]
                j = i + 1
                
                # Regrouper toutes les détections dont le début est < spot_duration du premier
                while j < len(enreg_matches_sorted):
                    next_match = enreg_matches_sorted[j]
                    time_diff = next_match.start_seconds - current.start_seconds
                    
                    # Si l'écart < durée du spot, c'est le même spot mal détecté
                    if time_diff < spot_duration:
                        same_spot_group.append(next_match)
                        j += 1
                    else:
                        break
                
                # Garder celui avec le timestamp le plus ancien (= le vrai début du spot)
                # et la meilleure confiance en cas d'égalité
                best = min(same_spot_group, key=lambda m: (m.start_seconds, -m.confidence))
                kept.append(best)
                
                i = j if j > i + 1 else i + 1
            
            filtered.extend(kept)
        
        filtered.sort(key=lambda m: (m.enregistrement_id, m.start_seconds))
        return filtered
    
    @staticmethod
    def _time_to_seconds(time_str: str) -> float:
        """Convertir HH:MM:SS en secondes depuis minuit"""
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    
    @staticmethod
    def _seconds_to_time(seconds: float) -> str:
        """Convertir secondes depuis minuit en HH:MM:SS,MMM"""
        # Gérer le dépassement de 24h
        seconds = seconds % 86400  # 86400 = 24*3600
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        millis = int((secs % 1) * 1000)
        secs = int(secs)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
