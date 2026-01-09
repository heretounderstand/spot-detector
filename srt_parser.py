import re
from dataclasses import dataclass
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class Subtitle:
    """ReprÃ©sente un segment SRT"""
    index: int
    start_time: str
    end_time: str
    text: str
    start_seconds: float = 0.0
    end_seconds: float = 0.0
    
    def __post_init__(self):
        self.start_seconds = self._time_to_seconds(self.start_time)
        self.end_seconds = self._time_to_seconds(self.end_time)
    
    @staticmethod
    def _time_to_seconds(time_str: str) -> float:
        """Convertir HH:MM:SS,MMM en secondes"""
        try:
            parts = time_str.replace(',', '.').split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        except (ValueError, IndexError):
            logger.error(f"Format de temps invalide: {time_str}")
            return 0.0


class SRTParser:
    """Parseur SRT minimaliste"""
    
    def parse(self, srt_content: str) -> List[Subtitle]:
        """Parser contenu SRT en liste de Subtitle"""
        subtitles = []
        blocks = srt_content.strip().split('\n\n')
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) < 3:
                continue
            
            try:
                index = int(lines[0])
                time_line = lines[1]
                text = '\n'.join(lines[2:]).strip()
                
                time_match = re.match(
                    r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})',
                    time_line
                )
                
                if time_match:
                    subtitle = Subtitle(
                        index=index,
                        start_time=time_match.group(1),
                        end_time=time_match.group(2),
                        text=text
                    )
                    subtitles.append(subtitle)
            except (ValueError, IndexError):
                continue
        
        return subtitles