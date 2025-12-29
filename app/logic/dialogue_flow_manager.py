"""
DialogueFlowManager - TTS Pacing Engine for Web Novel Dialogue
Fixes "rushed" dialogue by inserting industry-standard pauses.
"""

import re
from typing import List, Dict, Literal


class DialogueFlowManager:
    """
    Processes chapter text into structured audio segments with intelligent pause insertion.
    
    Industry Standards:
    - Speaker Change: 0.4s (natural turn-taking)
    - Action Beat: 0.1s (connected flow)
    - Header: 1.0s (chapter transitions)
    """
    
    # Pause durations (seconds)
    PAUSE_SPEAKER_CHANGE = 0.4
    PAUSE_ACTION_BEAT = 0.1
    PAUSE_NARRATION = 0.2
    PAUSE_HEADER = 1.0
    PAUSE_DIALOGUE_DEFAULT = 0.5
    
    def __init__(self, use_ssml: bool = False):
        """
        Args:
            use_ssml: If True, insert SSML break tags. Otherwise, rely on pause_after values.
        """
        self.use_ssml = use_ssml
        
        # Regex patterns
        self.dialogue_standalone_pattern = re.compile(
            r'^["\u201C\u201D\u2018\u2019].*["\u201C\u201D\u2018\u2019][.!?\u2026]*$'
        )
        self.dialogue_attributed_pattern = re.compile(
            r'["\u201C\u201D\u2018\u2019].*["\u201C\u201D\u2018\u2019]'
        )
        self.header_pattern = re.compile(
            r'^(Chapter|CHAPTER|Ch\.|C|Arc|Volume|Vol\.)\s*[\d\w]+', 
            re.IGNORECASE
        )
    
    def classify_paragraph(self, text: str) -> Literal["dialogue_standalone", "dialogue_attributed", "narration", "header"]:
        """
        Classifies a paragraph into one of four types.
        
        Returns:
            - "header": Chapter/Arc titles
            - "dialogue_standalone": Pure dialogue ("Text.")
            - "dialogue_attributed": Dialogue + narration ("Text," he said.)
            - "narration": No dialogue
        """
        text = text.strip()
        
        if not text:
            return "narration"
        
        # Check for header first
        if self.header_pattern.match(text):
            return "header"
        
        # Check for dialogue (standalone)
        if self.dialogue_standalone_pattern.match(text):
            return "dialogue_standalone"
        
        # Check for dialogue (attributed)
        if self.dialogue_attributed_pattern.search(text):
            return "dialogue_attributed"
        
        return "narration"
    
    def _add_break_token(self, text: str, duration_ms: int) -> str:
        """
        Adds a break token to text (SSML or ellipsis).
        
        Args:
            text: Original text
            duration_ms: Break duration in milliseconds
            
        Returns:
            Modified text with break token
        """
        if self.use_ssml:
            return f'{text} <break time="{duration_ms}ms"/>'
        else:
            # Fallback: Add ellipsis for natural pause
            if not text.endswith(("...", "…")):
                return f"{text}..."
            return text
    
    def _calculate_pause(
        self, 
        current_type: str, 
        next_type: str | None
    ) -> float:
        """
        Calculates pause duration based on segment types.
        
        Args:
            current_type: Type of current segment
            next_type: Type of next segment (None if last)
            
        Returns:
            Pause duration in seconds
        """
        if current_type == "header":
            return self.PAUSE_HEADER
        
        if next_type is None:
            return 0.0
        
        # Rule A: Speaker Change (Dialogue -> Dialogue)
        if current_type.startswith("dialogue") and next_type.startswith("dialogue"):
            return self.PAUSE_SPEAKER_CHANGE
        
        # Rule B: Action Beat (Dialogue -> Narration)
        if current_type.startswith("dialogue") and next_type == "narration":
            return self.PAUSE_ACTION_BEAT
        
        # Default narration pause
        if current_type == "narration":
            return self.PAUSE_NARRATION
        
        return self.PAUSE_DIALOGUE_DEFAULT
    
    def process_chapter(self, text: str) -> List[Dict[str, any]]:
        """
        Processes raw chapter text into structured audio segments.
        
        Args:
            text: Raw chapter text (multi-paragraph string)
            
        Returns:
            List of audio segments:
            [
                {
                    "text": "processed text",
                    "type": "dialogue|narration|header",
                    "pause_after": 0.4  # seconds
                },
                ...
            ]
        """
        # Split into paragraphs (preserve empty lines as separators)
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        
        if not paragraphs:
            return []
        
        segments = []
        
        for i, para in enumerate(paragraphs):
            # Classify paragraph
            para_type = self.classify_paragraph(para)
            
            # Determine next paragraph type (for pause calculation)
            next_type = None
            if i + 1 < len(paragraphs):
                next_type = self.classify_paragraph(paragraphs[i + 1])
            
            # Calculate pause
            pause = self._calculate_pause(para_type, next_type)
            
            # Apply punctuation hacking (Rule C) for standalone dialogue
            processed_text = para
            if para_type == "dialogue_standalone":
                processed_text = self._add_break_token(para, 300)
            
            # Simplify type for output
            output_type = "dialogue" if "dialogue" in para_type else para_type
            
            segments.append({
                "text": processed_text,
                "type": output_type,
                "pause_after": pause
            })
        
        return segments
    
    def process_chapter_with_metadata(self, text: str) -> Dict[str, any]:
        """
        Enhanced version that returns segments + metadata.
        
        Returns:
            {
                "segments": [...],
                "stats": {
                    "total_paragraphs": 50,
                    "dialogue_count": 30,
                    "narration_count": 19,
                    "header_count": 1
                }
            }
        """
        segments = self.process_chapter(text)
        
        stats = {
            "total_paragraphs": len(segments),
            "dialogue_count": sum(1 for s in segments if s["type"] == "dialogue"),
            "narration_count": sum(1 for s in segments if s["type"] == "narration"),
            "header_count": sum(1 for s in segments if s["type"] == "header")
        }
        
        return {
            "segments": segments,
            "stats": stats
        }


# Example Usage
if __name__ == "__main__":
    manager = DialogueFlowManager(use_ssml=False)
    
    sample_text = """
Chapter 1: The Beginning

Lin Fan looked up at the sky.

"Who are you?"

"I am your nightmare."

He stepped back, heart racing.

"Don't do that."

"Why not?" she asked with a smirk.
"""
    
    result = manager.process_chapter(sample_text)
    
    print("=== Processed Audio Segments ===\n")
    for i, segment in enumerate(result, 1):
        print(f"{i}. [{segment['type'].upper()}] {segment['text']}")
        print(f"   Pause: {segment['pause_after']}s\n")

