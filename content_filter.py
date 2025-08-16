import re
import logging
from typing import List, Dict, Tuple
from config import Config

logger = logging.getLogger(__name__)

class ContentFilter:
    def __init__(self):
        self.vulgar_patterns = self._compile_patterns(Config.VULGAR_WORDS)
        self.competitor_patterns = self._compile_patterns(Config.COMPETITOR_KEYWORDS)
        self.screenshot_patterns = self._compile_patterns(Config.SCREENSHOT_INDICATORS)
        
    def _compile_patterns(self, words: List[str]) -> List[re.Pattern]:
        patterns = []
        for word in words:
            pattern = re.compile(rf'\b{re.escape(word)}\b', re.IGNORECASE)
            patterns.append(pattern)
        return patterns
    
    def check_vulgar_content(self, text: str) -> Tuple[bool, List[str]]:
        found_words = []
        for pattern in self.vulgar_patterns:
            matches = pattern.findall(text)
            found_words.extend(matches)
        
        return len(found_words) > 0, found_words
    
    def check_competitor_content(self, text: str) -> Tuple[bool, List[str]]:
        found_words = []
        for pattern in self.competitor_patterns:
            matches = pattern.findall(text)
            found_words.extend(matches)
        
        return len(found_words) > 0, found_words
    
    def check_screenshot_threat(self, text: str) -> Tuple[bool, List[str]]:
        # Only flag as threat if text contains malicious screenshot indicators
        # Don't flag educational screenshots with NEET-related content
        if not text:
            return False, []
            
        # Check for educational indicators (allow these)
        educational_keywords = [
            "neet", "question", "doubt", "solve", "answer", "physics", "chemistry", 
            "biology", "math", "solution", "help", "explain", "concept", "formula"
        ]
        
        text_lower = text.lower()
        has_educational_content = any(keyword in text_lower for keyword in educational_keywords)
        
        # If has educational content, don't flag as screenshot threat
        if has_educational_content:
            return False, []
        
        # Only flag if contains threat indicators without educational context
        found_words = []
        for pattern in self.screenshot_patterns:
            matches = pattern.findall(text)
            found_words.extend(matches)
        
        return len(found_words) > 0, found_words
    
    def check_spam_patterns(self, text: str) -> bool:
        if not text:
            return False
            
        text_lower = text.lower()
        
        # Check for URLs but allow NEET-related ones
        url_pattern = r'(?:https?://|www\.)\S+'
        urls = re.findall(url_pattern, text, re.IGNORECASE)
        for url in urls:
            # Allow NEET preparation related URLs
            allowed_domains = ['neetprep', 'neet', 'ncert', 'cbse', 'nta.ac.in']
            if not any(domain in url.lower() for domain in allowed_domains):
                return True
        
        # Don't flag @mentions (students interact with each other)
        # Removed: r'@\w+' pattern
        
        # Keep other spam patterns
        spam_indicators = [
            r'\b(?:call|contact|whatsapp)\s*:?\s*\+?\d+',
            r'(?:dm|message)\s+me',
            r'click\s+(?:here|link)',
            r'join\s+(?:my|our)\s+(?:channel|group)',
            r'free\s+(?:download|pdf|course)',
            r'limited\s+time\s+offer',
            r'buy\s+now',
            r'discount\s+code'
        ]
        
        for pattern in spam_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def check_commercial_spam(self, text: str) -> bool:
        """Check for obvious commercial spam even in educational context"""
        commercial_patterns = [
            r'buy\s+(?:now|course|pdf)',
            r'₹\s*\d+',  # Price mentions
            r'discount\s+(?:code|offer)',
            r'limited\s+time\s+offer',
            r'call\s+now',
            r'whatsapp\s+\+?\d+',
            r'dm\s+for\s+(?:course|pdf|notes)'
        ]
        
        for pattern in commercial_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def analyze_message(self, text: str) -> Dict[str, any]:
        if not text:
            return {"is_safe": True, "violations": []}
        
        # Check if message has educational context
        educational_keywords = [
            "neet", "question", "doubt", "solve", "answer", "physics", "chemistry", 
            "biology", "math", "mathematics", "solution", "help", "explain", "concept", 
            "formula", "ncert", "jee", "study", "exam", "preparation", "syllabus",
            "chapter", "topic", "theory", "practice", "test", "mock", "sample"
        ]
        
        text_lower = text.lower()
        has_educational_content = any(keyword in text_lower for keyword in educational_keywords)
        
        # If educational content, be very lenient - only block obvious spam
        if has_educational_content:
            # Only check for blatant commercial spam
            if self.check_commercial_spam(text):
                return {
                    "is_safe": False,
                    "violations": [{"type": "commercial_spam", "severity": "high"}],
                    "text": text
                }
            return {"is_safe": True, "violations": [], "text": text}
        
        # For non-educational content, apply normal filters
        violations = []
        
        # Only check enabled filters (most are commented out in config)
        is_vulgar, vulgar_words = self.check_vulgar_content(text)
        if is_vulgar and vulgar_words:  # Only if words are actually defined
            violations.append({
                "type": "vulgar_content",
                "words": vulgar_words,
                "severity": "high"
            })
        
        is_competitor, competitor_words = self.check_competitor_content(text)
        if is_competitor and competitor_words:  # Only if words are actually defined
            violations.append({
                "type": "competitor_content", 
                "words": competitor_words,
                "severity": "medium"
            })
        
        is_threat, threat_words = self.check_screenshot_threat(text)
        if is_threat and threat_words:  # Only if words are actually defined
            violations.append({
                "type": "screenshot_threat",
                "words": threat_words,
                "severity": "high"
            })
        
        if self.check_spam_patterns(text):
            violations.append({
                "type": "spam_pattern",
                "severity": "medium"
            })
        
        return {
            "is_safe": len(violations) == 0,
            "violations": violations,
            "text": text
        }
    
    def analyze_message_trusted(self, text: str) -> Dict[str, any]:
        """Very lenient filtering for trusted users"""
        if not text:
            return {"is_safe": True, "violations": []}
        
        # Only block obvious commercial spam for trusted users
        if self.check_commercial_spam(text):
            return {
                "is_safe": False,
                "violations": [{"type": "commercial_spam", "severity": "high"}],
                "text": text
            }
        
        return {"is_safe": True, "violations": [], "text": text}
    
    def analyze_message_strict(self, text: str) -> Dict[str, any]:
        """Stricter filtering for new/monitored users"""
        if not text:
            return {"is_safe": True, "violations": []}
        
        violations = []
        
        # Check all patterns more strictly for new users
        is_vulgar, vulgar_words = self.check_vulgar_content(text)
        if is_vulgar and vulgar_words:
            violations.append({
                "type": "vulgar_content",
                "words": vulgar_words,
                "severity": "high"
            })
        
        is_competitor, competitor_words = self.check_competitor_content(text)
        if is_competitor and competitor_words:
            violations.append({
                "type": "competitor_content", 
                "words": competitor_words,
                "severity": "medium"
            })
        
        is_threat, threat_words = self.check_screenshot_threat(text)
        if is_threat and threat_words:
            violations.append({
                "type": "screenshot_threat",
                "words": threat_words,
                "severity": "high"
            })
        
        # More aggressive spam detection for new users
        if self.check_spam_patterns(text) or self.check_commercial_spam(text):
            violations.append({
                "type": "spam_pattern",
                "severity": "medium"
            })
        
        # Additional checks for new users
        text_lower = text.lower()
        
        # Check for suspicious behavior patterns
        if any(pattern in text_lower for pattern in [
            'join my', 'follow me', 'check my', 'visit my',
            'subscribe to', 'like and share', 'comment below'
        ]):
            violations.append({
                "type": "promotional_pattern",
                "severity": "medium"
            })
        
        return {
            "is_safe": len(violations) == 0,
            "violations": violations,
            "text": text
        }