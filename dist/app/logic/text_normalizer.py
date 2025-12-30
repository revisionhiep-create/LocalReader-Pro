import re
from typing import List, Dict, Any

def fix_broken_words(text: str) -> str:
    """Fixes PDF artifacts like ligatures, ghost spaces, and mid-word hyphens."""
    # 0. Ligatures
    ligatures = {'\ufb00': 'ff', '\ufb01': 'fi', '\ufb02': 'fl', '\ufb03': 'ffi', '\ufb04': 'ffl', '\ufb05': 'ft', '\ufb06': 'st', '\u00a0': ' ', '\u2013': '-', '\u2014': '--'}
    for char, rep in ligatures.items(): text = text.replace(char, rep)

    # 1. De-hyphenation
    text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', text)
    
    # 2. Ghost spaces in common words
    common = [(r'\bo\s+ff\b', 'off'), (r'\bo\s+f\b', 'of'), (r'\ba\s+nd\b', 'and'), (r'\bt\s+he\b', 'the'), (r'\bi\s+n\b', 'in'), (r'\bi\s+t\b', 'it'), (r'\bi\s+s\b', 'is'), (r'\bt\s+o\b', 'to'), (r'\bs\s+t\b', 'st')]
    for pat, rep in common: text = re.sub(pat, rep, text, flags=re.IGNORECASE)

    # 3. Recursive single letter join (e.g. "W o r d" -> "Word")
    old = ""
    while old != text:
        old = text
        text = re.sub(r'(?:^|(?<=\s))([a-zA-Z])\s+([a-zA-Z])(?=\s|$)', r'\1\2', text)
    
    # 4. Cleanup punctuation spaces
    text = re.sub(r'([\"\'\(\[\{\u201c\u2018\u201d\u2019])\s+', r'\1', text)
    text = re.sub(r'\s+([\"\'\)\\\}\]\u201c\u2018\u201d\u2019])', r'\1', text)
    text = re.sub(r'(?<=[\"\'\u201c\u2018\u201d\u2019])\s+', '', text)
    text = re.sub(r'\s+(?=[\"\'\u201c\u2018\u201d\u2019])', '', text)
    
    return re.sub(r'\s+', ' ', text).strip()

def apply_custom_pronunciations(text: str, rules: List[Dict[str, Any]], ignore_list: List[str] = []) -> str:
    # First fix PDF artifacts
    text = fix_broken_words(text)
    
    # Apply ignore list
    for item in ignore_list:
        if item: text = re.sub(re.escape(item), "", text, flags=re.IGNORECASE)

    # Apply pronunciation rules
    for rule in rules:
        orig, rep = rule.get("original", ""), rule.get("replacement", "")
        if not orig: continue
        pat = re.escape(orig)
        if rule.get("word_boundary"): pat = f"\\b{pat}\\b"
        text = re.sub(pat, rep, text, flags=0 if rule.get("match_case") else re.IGNORECASE)
            
    return text

def inject_pauses(text: str, pause_settings: Dict[str, int]) -> str:
    """
    Inject SSML-like pause markers based on punctuation.
    Note: Kokoro TTS doesn't support SSML, so this is a placeholder for future enhancement.
    For now, we simply return the text as-is since Kokoro handles pauses naturally.
    
    Args:
        text: Input text
        pause_settings: Dict with keys 'comma', 'period', 'question', 'newline' (values in ms)
    
    Returns:
        Text with pause markers (currently unchanged for Kokoro compatibility)
    """
    # Kokoro TTS naturally handles pauses based on punctuation
    # This function is a placeholder for future TTS engines that support SSML
    # or custom pause injection
    return text