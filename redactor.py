import re
import spacy
from typing import List, Tuple

class PrivacyRedactor:
    def __init__(self, use_spacy=True):
        """
        Initialize the Privacy Redactor
        :param use_spacy: Whether to use spaCy for entity recognition
        """
        self.use_spacy = use_spacy
        if use_spacy:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                print("spaCy model not found. Please install with: python -m spacy download en_core_web_sm")
                self.use_spacy = False
        
        # Define regex patterns for different entity types
        self.patterns = {
            'EMAIL_ADDRESS': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'PHONE_NUMBER': r'(\+?\d{1,3}[-.\s]?)?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
            'IP_ADDRESS': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            'CREDIT_CARD': r'\b(?:\d{4}[- ]?){3,4}\d{4}\b',
            'URL': r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*\??[/\w\.-=&]*',
            'DATE_TIME': r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{1,2}:\d{2}(?::\d{2})?\b',
        }
        
        # Common names and locations for rule-based detection
        self.common_names = {
            'john', 'jane', 'martin', 'smith', 'doe', 'david', 'mary', 'robert',
            'michael', 'william', 'james', 'patricia', 'linda', 'elizabeth', 'emma',
            'oliver', 'sophia', 'liam', 'ava', 'noah'
        }
        
        self.common_locations = {
            'new york', 'london', 'paris', 'tokyo', 'berlin', 'cardiff', 'coriff',
            'los angeles', 'chicago', 'toronto', 'sydney', 'manchester', 'boston',
            'washington', 'mumbai', 'delhi', 'dublin'
        }

    def detect_with_regex(self, text: str) -> List[Tuple[int, int, str, str]]:
        """
        Detect entities using regex patterns
        Returns: List of (start, end, entity_type, text) tuples
        """
        entities = []
        
        for entity_type, pattern in self.patterns.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Validate specific entities
                if entity_type == 'CREDIT_CARD' and not self._is_valid_credit_card(match.group()):
                    continue
                entities.append((match.start(), match.end(), entity_type, match.group()))
        
        return entities

    def detect_with_spacy(self, text: str) -> List[Tuple[int, int, str, str]]:
        """
        Detect entities using spaCy
        """
        if not self.use_spacy:
            return []
            
        entities = []
        doc = self.nlp(text)
        
        for ent in doc.ents:
            entity_type = self._map_spacy_label(ent.label_)
            if entity_type:
                entities.append((ent.start_char, ent.end_char, entity_type, ent.text))
        
        return entities

    def detect_names_locations_rules(self, text: str) -> List[Tuple[int, int, str, str]]:
        """
        Rule-based detection for names and locations
        """
        entities = []
        
        # Detect names: Title + Capitalized words
        name_patterns = [
            r'\b(Mr|Mrs|Ms|Dr|Prof)\.?\s+([A-Z][a-z]+)(?:\s+([A-Z][a-z]+))?',
            r'\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b'
        ]
        
        for pattern in name_patterns:
            for match in re.finditer(pattern, text):
                potential_name = match.group().lower()
                # Check if it contains common names or follows name patterns
                if any(name in potential_name for name in self.common_names):
                    entities.append((match.start(), match.end(), 'PERSON', match.group()))
        
        # Detect locations: Capitalized words that are in common locations
        words = re.findall(r'\b[A-Z][a-z]+\b', text)
        for word in words:
            if word.lower() in self.common_locations:
                for match in re.finditer(re.escape(word), text):
                    entities.append((match.start(), match.end(), 'LOCATION', match.group()))
        
        return entities

    def redact_text(self, text: str, mode: str = 'redact') -> Tuple[str, List[dict]]:
        """
        Main redaction function
        :param text: Input text to redact
        :param mode: 'redact' (remove) or 'mask' (replace with [ENTITY_TYPE])
        :return: Tuple of (redacted_text, entities_list)
        """
        # Collect all entities
        all_entities = []
        
        # Regex-based detection
        all_entities.extend(self.detect_with_regex(text))
        
        # spaCy-based detection (if enabled)
        if self.use_spacy:
            all_entities.extend(self.detect_with_spacy(text))
        
        # Rule-based name and location detection
        all_entities.extend(self.detect_names_locations_rules(text))
        
        # Remove duplicates and sort by start position (descending for safe replacement)
        unique_entities = self._remove_overlapping_entities(all_entities)
        unique_entities.sort(key=lambda x: x[0], reverse=True)
        
        # Prepare entities for output
        entities_info = []
        for start, end, entity_type, entity_text in unique_entities:
            entities_info.append({
                'entity_type': entity_type,
                'text': entity_text,
                'start': start,
                'end': end
            })
        
        # Apply redaction
        redacted_text = text
        for start, end, entity_type, entity_text in unique_entities:
            if mode == 'redact':
                replacement = ''
            else:  # mask mode
                replacement = f'[{entity_type}]'
            
            redacted_text = redacted_text[:start] + replacement + redacted_text[end:]
        
        return redacted_text, entities_info

    def _map_spacy_label(self, label: str) -> str:
        """Map spaCy entity labels to our entity types"""
        mapping = {
            'PERSON': 'PERSON',
            'GPE': 'LOCATION',  # Countries, cities, states
            'LOC': 'LOCATION',   # Non-GPE locations
            'DATE': 'DATE_TIME',
            'TIME': 'DATE_TIME',
            'EMAIL': 'EMAIL_ADDRESS',
            'PHONE': 'PHONE_NUMBER',
        }
        return mapping.get(label, None)

    def _is_valid_credit_card(self, number: str) -> bool:
        """Basic credit card validation using Luhn algorithm"""
        # Remove non-digits
        digits = ''.join(filter(str.isdigit, number))
        if len(digits) < 13:
            return False
        
        # Luhn algorithm
        total = 0
        for i, digit in enumerate(reversed(digits)):
            n = int(digit)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n -= 9
            total += n
        
        return total % 10 == 0

    def _remove_overlapping_entities(self, entities: List[Tuple]) -> List[Tuple]:
        """Remove overlapping entities, keeping the longest one"""
        if not entities:
            return []
        
        # Sort by start position
        entities.sort(key=lambda x: x[0])
        
        filtered = []
        current_start, current_end, current_type, current_text = entities[0]
        
        for start, end, entity_type, text in entities[1:]:
            if start <= current_end:  # Overlapping
                if (end - start) > (current_end - current_start):  # Keep longer entity
                    current_start, current_end, current_type, current_text = start, end, entity_type, text
            else:
                filtered.append((current_start, current_end, current_type, current_text))
                current_start, current_end, current_type, current_text = start, end, entity_type, text
        
        filtered.append((current_start, current_end, current_type, current_text))
        return filtered

# Utility function for Levenshtein similarity
def levenshtein_similarity(original: str, redacted: str) -> float:
    """
    Calculate similarity between original and redacted text using Levenshtein distance
    """
    if not original:
        return 0.0
    
    # Calculate Levenshtein distance
    m, n = len(original), len(redacted)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    
    for i in range(m + 1):
        for j in range(n + 1):
            if i == 0:
                dp[i][j] = j
            elif j == 0:
                dp[i][j] = i
            elif original[i-1] == redacted[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(dp[i][j-1], dp[i-1][j], dp[i-1][j-1])
    
    distance = dp[m][n]
    max_len = max(len(original), len(redacted))
    
    if max_len == 0:
        return 1.0
    
    return 1 - (distance / max_len)