"""
Fuzzy menu-item matching service.
Uses text normalization, keyword extraction, and token-based similarity
to intelligently match menu items across restaurants and platforms.
"""

import re
from config import Config

try:
    from rapidfuzz import fuzz, process
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False

try:
    from unidecode import unidecode
    HAS_UNIDECODE = True
except ImportError:
    HAS_UNIDECODE = False


# Common suffixes/decorators to strip during normalization
_STRIP_PATTERNS = [
    r'\(\d+\s*pc\)', r'\(\d+\s*pcs\)', r'\(\d+\s*pieces?\)',
    r'\(half\)', r'\(full\)', r'\(small\)', r'\(medium\)', r'\(large\)',
    r'\(reg(ular)?\)', r'\(lg\)', r'\(sm\)', r'\(xl\)',
    r'\bsm\b', r'\blg\b', r'\bxl\b',
    r'\bw/\b', r'\bw\b',
]

# Food keyword synonyms for intelligent matching
_SYNONYMS = {
    'biryani': ['biriyani', 'briyani', 'biriani', 'biryaani'],
    'chicken': ['chkn', 'chiken'],
    'mutton': ['goat', 'lamb'],
    'paneer': ['cottage cheese'],
    'naan': ['nan', 'naaan'],
    'tandoori': ['tandori', 'thandoori'],
    'hyderabadi': ['hyderabad', 'hyd'],
    'dum': ['dum pukht', 'dumpukht'],
    'masala': ['massala'],
    'tikka': ['tikha', 'tika'],
    'curry': ['currie', 'kari'],
    'samosa': ['samossa'],
    'gulab': ['gulaab'],
    'jamun': ['jamoon', 'jaamun'],
    'lassi': ['lasi', 'lasee'],
    'mango': ['aam'],
    'dal': ['daal', 'dhal', 'lentil'],
    'rice': ['chawal', 'chaval'],
    'butter': ['makhani', 'makhan'],
    'combo': ['combination', 'platter', 'thali'],
}

# Build reverse synonym map
_REVERSE_SYNONYMS = {}
for canonical, alts in _SYNONYMS.items():
    for alt in alts:
        _REVERSE_SYNONYMS[alt] = canonical


class MatchingService:
    """Intelligent menu item matching using fuzzy string comparison."""

    def __init__(self):
        self.threshold = Config.FUZZY_MATCH_THRESHOLD

    def normalize_name(self, name):
        """Normalize a menu item name for comparison."""
        if not name:
            return ''
        text = name.lower().strip()
        if HAS_UNIDECODE:
            text = unidecode(text)
        # Remove common suffixes
        for pattern in _STRIP_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        # Remove special characters except spaces
        text = re.sub(r'[^a-z0-9\s]', '', text)
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Apply synonym normalization
        tokens = text.split()
        normalized_tokens = []
        for token in tokens:
            canonical = _REVERSE_SYNONYMS.get(token, token)
            normalized_tokens.append(canonical)
        return ' '.join(normalized_tokens)

    def similarity_score(self, name1, name2):
        """Calculate similarity between two menu item names (0.0 to 1.0)."""
        n1 = self.normalize_name(name1)
        n2 = self.normalize_name(name2)
        if not n1 or not n2:
            return 0.0
        # Exact match after normalization
        if n1 == n2:
            return 1.0
        if HAS_RAPIDFUZZ:
            # Weighted combination of different fuzzy metrics
            ratio = fuzz.ratio(n1, n2) / 100.0
            partial = fuzz.partial_ratio(n1, n2) / 100.0
            token_sort = fuzz.token_sort_ratio(n1, n2) / 100.0
            token_set = fuzz.token_set_ratio(n1, n2) / 100.0
            return 0.2 * ratio + 0.2 * partial + 0.3 * token_sort + 0.3 * token_set
        else:
            return self._basic_similarity(n1, n2)

    def find_best_match(self, item_name, candidates, category_hint=None):
        """
        Find the best matching item from a list of candidates.
        Returns (matched_name, score) or (None, 0.0) if no match above threshold.
        """
        if not item_name or not candidates:
            return None, 0.0

        best_match = None
        best_score = 0.0

        for candidate in candidates:
            cand_name = candidate if isinstance(candidate, str) else candidate.get('item_name', '')
            score = self.similarity_score(item_name, cand_name)

            # Boost score if categories match
            if category_hint and isinstance(candidate, dict):
                cand_cat = (candidate.get('category') or '').lower()
                if category_hint.lower() == cand_cat:
                    score = min(score * 1.15, 1.0)

            if score > best_score:
                best_score = score
                best_match = candidate

        if best_score >= self.threshold:
            return best_match, best_score
        return None, 0.0

    def match_menus(self, menu_a, menu_b, category_filter=None):
        """
        Match items between two menus. Returns list of matched pairs:
        [{ 'item_a': {...}, 'item_b': {...}|None, 'score': float }]
        Unmatched items from menu_b are included with item_a=None.
        """
        if category_filter:
            menu_a = [i for i in menu_a if (i.get('category') or '').lower() == category_filter.lower()]
            menu_b = [i for i in menu_b if (i.get('category') or '').lower() == category_filter.lower()]

        matched = []
        used_b_indices = set()

        for item_a in menu_a:
            best_idx = None
            best_score = 0.0
            for idx, item_b in enumerate(menu_b):
                if idx in used_b_indices:
                    continue
                score = self.similarity_score(
                    item_a.get('item_name', ''),
                    item_b.get('item_name', '')
                )
                # Category boost
                cat_a = (item_a.get('category') or '').lower()
                cat_b = (item_b.get('category') or '').lower()
                if cat_a and cat_b and cat_a == cat_b:
                    score = min(score * 1.1, 1.0)
                if score > best_score:
                    best_score = score
                    best_idx = idx

            if best_idx is not None and best_score >= self.threshold:
                matched.append({
                    'item_a': item_a,
                    'item_b': menu_b[best_idx],
                    'score': round(best_score, 3),
                })
                used_b_indices.add(best_idx)
            else:
                matched.append({
                    'item_a': item_a,
                    'item_b': None,
                    'score': 0.0,
                })

        # Add unmatched items from menu_b
        for idx, item_b in enumerate(menu_b):
            if idx not in used_b_indices:
                matched.append({
                    'item_a': None,
                    'item_b': item_b,
                    'score': 0.0,
                })

        return matched

    def _basic_similarity(self, s1, s2):
        """Basic token overlap similarity when rapidfuzz is unavailable."""
        tokens1 = set(s1.split())
        tokens2 = set(s2.split())
        if not tokens1 or not tokens2:
            return 0.0
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        return len(intersection) / len(union)


# Singleton
matching_service = MatchingService()
