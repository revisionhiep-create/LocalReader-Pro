"""
Smart Content Detection Module for LocalReader Pro v1.5
Handles Smart Start (intro skip) and Header/Footer filtering.
"""

import re
from typing import List, Tuple, Dict
from difflib import SequenceMatcher

def find_content_start_page(pages: List[str], max_scan: int = 10) -> int:
    """
    Scans the first N pages and finds the first page with substantial content.
    
    Args:
        pages: List of page texts
        max_scan: Maximum number of pages to scan (default: 10)
    
    Returns:
        Index of the first content page (0 if no empty pages found)
    """
    scan_limit = min(max_scan, len(pages))
    
    for i in range(scan_limit):
        page_text = pages[i].strip()
        
        # Count alphanumeric characters (ignore whitespace and punctuation)
        char_count = len(re.findall(r'[a-zA-Z0-9]', page_text))
        
        # Count words
        words = re.findall(r'\b\w+\b', page_text)
        word_count = len(words)
        
        # Heuristic: Substantial content = >500 chars OR >100 words
        if char_count > 500 or word_count > 100:
            return i
    
    # If no substantial content found, start at page 0
    return 0


def split_into_lines(text: str) -> List[str]:
    """Split text into lines and clean up."""
    return [line.strip() for line in text.split('\n') if line.strip()]


def similarity(a: str, b: str) -> float:
    """Calculate similarity between two strings (0.0 to 1.0)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def is_page_number(line: str) -> bool:
    """Detect if a line is likely a page number."""
    # Remove whitespace and common page number patterns
    cleaned = line.strip().replace('Page', '').replace('page', '').strip()
    
    # Check if it's just a number (or Roman numeral)
    if re.match(r'^[0-9]+$', cleaned):
        return True
    if re.match(r'^[ivxlcdm]+$', cleaned, re.IGNORECASE):
        return True
    if re.match(r'^\d+\s*of\s*\d+$', cleaned, re.IGNORECASE):
        return True
    
    return False


def detect_headers_footers(pages: List[str], page_index: int) -> Dict[str, List[str]]:
    """
    Detects repeated header/footer lines by comparing with adjacent pages.
    
    Args:
        pages: All pages in the document
        page_index: Current page index
    
    Returns:
        Dictionary with 'headers' and 'footers' lists containing detected noise lines
    """
    if not pages or page_index >= len(pages):
        return {'headers': [], 'footers': []}
    
    current_page = pages[page_index]
    current_lines = split_into_lines(current_page)
    
    if len(current_lines) < 3:
        return {'headers': [], 'footers': []}
    
    headers = []
    footers = []
    
    # Get adjacent pages for comparison
    prev_page = pages[page_index - 1] if page_index > 0 else None
    next_page = pages[page_index + 1] if page_index < len(pages) - 1 else None
    
    prev_lines = split_into_lines(prev_page) if prev_page else []
    next_lines = split_into_lines(next_page) if next_page else []
    
    # Calculate safe scan depth (max 20% of page or 3 lines, whichever is smaller, but at least 1 if lines exist)
    limit = max(1, min(3, int(len(current_lines) * 0.2)))
    
    # Check top lines (potential headers)
    for i in range(limit):
        current_line = current_lines[i]
        matches = 0
        
        # Compare with previous page
        if prev_lines and i < len(prev_lines):
            if similarity(current_line, prev_lines[i]) > 0.9:
                matches += 1
        
        # Compare with next page
        if next_lines and i < len(next_lines):
            if similarity(current_line, next_lines[i]) > 0.9:
                matches += 1
        
        # If line matches in at least 1 adjacent page
        if matches >= 1:
            headers.append(current_line)
    
    # Check bottom lines (potential footers)
    # Ensure footer scan doesn't overlap with header scan
    start_footer_scan = max(limit, len(current_lines) - limit)
    
    for i in range(start_footer_scan, len(current_lines)):
        current_line = current_lines[i]
        matches = 0
        offset_from_end = len(current_lines) - i - 1
        
        # Compare with previous page (same position from end)
        if prev_lines:
            prev_index = len(prev_lines) - offset_from_end - 1
            if 0 <= prev_index < len(prev_lines):
                if similarity(current_line, prev_lines[prev_index]) > 0.9:
                    matches += 1
        
        # Compare with next page
        if next_lines:
            next_index = len(next_lines) - offset_from_end - 1
            if 0 <= next_index < len(next_lines):
                if similarity(current_line, next_lines[next_index]) > 0.9:
                    matches += 1
        
        # Also check if it's a page number
        if is_page_number(current_line):
            matches += 2
        
        if matches >= 1:
            footers.append(current_line)
    
    return {'headers': headers, 'footers': footers}


def apply_header_footer_filter(text: str, headers: List[str], footers: List[str], mode: str = 'clean') -> str:
    """
    Applies header/footer filtering to text.
    
    Args:
        text: The page text
        headers: List of header lines to filter
        footers: List of footer lines to filter
        mode: 'clean' (remove) or 'dim' (mark for styling)
    
    Returns:
        Filtered text (with markers if mode='dim')
    """
    lines = split_into_lines(text)
    
    if mode == 'clean':
        # Remove all matching lines
        filtered_lines = []
        for line in lines:
            is_noise = False
            
            # Check if line matches any header/footer
            for header in headers:
                if similarity(line, header) > 0.9:
                    is_noise = True
                    break
            
            if not is_noise:
                for footer in footers:
                    if similarity(line, footer) > 0.9:
                        is_noise = True
                        break
            
            # Also check page numbers
            if is_page_number(line):
                is_noise = True
            
            if not is_noise:
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    elif mode == 'dim':
        # Mark lines with a special marker for frontend styling
        marked_lines = []
        for line in lines:
            is_noise = False
            
            for header in headers:
                if similarity(line, header) > 0.9:
                    is_noise = True
                    break
            
            if not is_noise:
                for footer in footers:
                    if similarity(line, footer) > 0.9:
                        is_noise = True
                        break
            
            if is_page_number(line):
                is_noise = True
            
            if is_noise:
                marked_lines.append(f'[DIM]{line}[/DIM]')
            else:
                marked_lines.append(line)
        
        return '\n'.join(marked_lines)
    
    else:
        return text


def filter_text_for_tts(text: str) -> str:
    """
    Removes [DIM]...[/DIM] markers for TTS playback.
    
    Args:
        text: Text with potential dim markers
    
    Returns:
        Clean text without dimmed sections
    """
    # Remove dimmed sections
    return re.sub(r'\[DIM\].*?\[/DIM\]', '', text, flags=re.DOTALL).strip()

