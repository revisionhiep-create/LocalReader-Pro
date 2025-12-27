import re
from typing import List, Dict, Any

def apply_custom_pronunciations(text: str, rules: List[Dict[str, Any]], ignore_list: List[str] = []) -> str:
    """
    Applies custom pronunciation rules and ignore list to the input text using regex.
    Rules follow the PronunciationRule interface:
    { "original": str, "replacement": str, "match_case": bool, "word_boundary": bool }
    """
    normalized_text = text
    
    # 1. Apply ignore list (exact string removal)
    for item in ignore_list:
        if not item: continue
        try:
            pattern = re.compile(re.escape(item), flags=re.IGNORECASE)
            normalized_text = pattern.sub("", normalized_text)
        except re.error: continue

    # 2. Apply pronunciation rules
    for rule in rules:
        original = rule.get("original", "")
        replacement = rule.get("replacement", "")
        match_case = rule.get("match_case", False)
        word_boundary = rule.get("word_boundary", False)
        
        if not original:
            continue
            
        # Escape the original text for regex safety
        pattern_str = re.escape(original)
        
        # Apply word boundary if requested
        if word_boundary:
            pattern_str = f"\\b{pattern_str}\\b"
            
        # Set regex flags
        flags = 0 if match_case else re.IGNORECASE
        
        # Perform replacement
        try:
            pattern = re.compile(pattern_str, flags=flags)
            normalized_text = pattern.sub(replacement, normalized_text)
        except re.error as e:
            print(f"Regex error for rule {original} -> {replacement}: {e}")
            continue
            
    return normalized_text

