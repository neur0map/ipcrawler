"""
Pydantic models for technology detection database
"""

from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field
from enum import Enum
from pathlib import Path
import json
import re

try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False


class TechnologyCategory(str, Enum):
    """Categories of technologies"""
    WEB_FRAMEWORK = "web_framework"
    CMS = "cms"
    DATABASE = "database" 
    MONITORING = "monitoring"
    ANALYTICS = "analytics"
    CI_CD = "ci_cd"
    ADMIN_PANEL = "admin_panel"
    SECURITY = "security"
    CONTAINER = "container"
    CLOUD = "cloud"


class TechnologyIndicators(BaseModel):
    """Indicators for detecting a technology"""
    response_patterns: List[str] = Field(default_factory=list, description="Regex patterns to match in response body")
    header_patterns: List[str] = Field(default_factory=list, description="Patterns to match in HTTP headers")
    path_patterns: List[str] = Field(default_factory=list, description="URL path patterns")
    file_extensions: List[str] = Field(default_factory=list, description="Common file extensions")
    fuzzy_keywords: List[str] = Field(default_factory=list, description="Keywords for fuzzy matching")


class TechnologyEntry(BaseModel):
    """Individual technology entry"""
    name: str = Field(..., description="Display name of the technology")
    category: TechnologyCategory = Field(..., description="Technology category")
    description: Optional[str] = Field(None, description="Description of the technology")
    indicators: TechnologyIndicators = Field(..., description="Detection indicators")
    discovery_paths: List[str] = Field(default_factory=list, description="Paths to test for this technology")
    confidence_weights: Optional[Dict[str, float]] = Field(None, description="Confidence weights for different indicator types")
    
    def get_confidence_weight(self, indicator_type: str) -> float:
        """Get confidence weight for an indicator type"""
        if self.confidence_weights and indicator_type in self.confidence_weights:
            return self.confidence_weights[indicator_type]
        # Default weights
        defaults = {
            'response_patterns': 0.8,
            'header_patterns': 0.9,
            'path_patterns': 0.7,
            'fuzzy_keywords': 0.6
        }
        return defaults.get(indicator_type, 0.5)


class TechnologyDatabase(BaseModel):
    """Complete technology detection database"""
    web_frameworks: Dict[str, TechnologyEntry] = Field(default_factory=dict)
    databases: Dict[str, TechnologyEntry] = Field(default_factory=dict)
    admin_panels: Dict[str, TechnologyEntry] = Field(default_factory=dict)
    monitoring_tools: Dict[str, TechnologyEntry] = Field(default_factory=dict)
    
    def get_all_technologies(self) -> Dict[str, TechnologyEntry]:
        """Get all technologies as a flat dictionary"""
        all_tech = {}
        all_tech.update(self.web_frameworks)
        all_tech.update(self.databases)
        all_tech.update(self.admin_panels)
        all_tech.update(self.monitoring_tools)
        return all_tech
    
    def get_by_category(self, category: TechnologyCategory) -> Dict[str, TechnologyEntry]:
        """Get technologies by category"""
        all_tech = self.get_all_technologies()
        return {k: v for k, v in all_tech.items() if v.category == category}


class DetectionResult(BaseModel):
    """Result of technology detection"""
    technology: str
    name: str
    category: TechnologyCategory
    confidence: float = Field(..., ge=0.0, le=1.0)
    matched_indicators: List[str] = Field(default_factory=list)
    discovery_paths: List[str] = Field(default_factory=list)


class TechnologyMatcher:
    """Advanced technology matcher with fuzzy matching"""
    
    def __init__(self, database: TechnologyDatabase):
        self.database = database
        self.technologies = database.get_all_technologies()
        
    def detect_technologies(self, 
                          response_body: str = "", 
                          headers: Dict[str, str] = None, 
                          url_path: str = "",
                          fuzzy_threshold: int = 80) -> List[DetectionResult]:
        """
        Detect technologies using multiple methods including fuzzy matching
        
        Args:
            response_body: HTML/text response content
            headers: HTTP response headers
            url_path: URL path being analyzed
            fuzzy_threshold: Minimum score for fuzzy matching (0-100)
            
        Returns:
            List of detected technologies with confidence scores
        """
        if headers is None:
            headers = {}
            
        results = []
        
        for tech_key, tech_entry in self.technologies.items():
            confidence_scores = []
            matched_indicators = []
            
            # 1. Response pattern matching
            response_confidence = self._match_response_patterns(
                response_body, tech_entry.indicators.response_patterns
            )
            if response_confidence > 0:
                confidence_scores.append(response_confidence * tech_entry.get_confidence_weight('response_patterns'))
                matched_indicators.extend([p for p in tech_entry.indicators.response_patterns 
                                         if re.search(p, response_body, re.IGNORECASE)])
            
            # 2. Header pattern matching
            header_confidence = self._match_header_patterns(
                headers, tech_entry.indicators.header_patterns
            )
            if header_confidence > 0:
                confidence_scores.append(header_confidence * tech_entry.get_confidence_weight('header_patterns'))
                matched_indicators.extend([p for p in tech_entry.indicators.header_patterns
                                         if self._match_headers_against_pattern(headers, p)])
            
            # 3. Path pattern matching
            path_confidence = self._match_path_patterns(
                url_path, tech_entry.indicators.path_patterns
            )
            if path_confidence > 0:
                confidence_scores.append(path_confidence * tech_entry.get_confidence_weight('path_patterns'))
                matched_indicators.extend([p for p in tech_entry.indicators.path_patterns
                                         if re.search(p, url_path, re.IGNORECASE)])
            
            # 4. Fuzzy keyword matching
            if RAPIDFUZZ_AVAILABLE and tech_entry.indicators.fuzzy_keywords:
                fuzzy_confidence = self._fuzzy_match_content(
                    response_body + " " + " ".join(headers.values()), 
                    tech_entry.indicators.fuzzy_keywords,
                    fuzzy_threshold
                )
                if fuzzy_confidence > 0:
                    confidence_scores.append(fuzzy_confidence * tech_entry.get_confidence_weight('fuzzy_keywords'))
                    matched_indicators.append(f"fuzzy_match")
            
            # Calculate overall confidence
            if confidence_scores:
                # Use weighted average with boost for multiple indicator types
                overall_confidence = sum(confidence_scores) / len(confidence_scores)
                
                # Boost confidence if multiple types of indicators match
                if len(confidence_scores) > 1:
                    overall_confidence = min(1.0, overall_confidence * 1.2)
                
                if overall_confidence > 0.1:  # Minimum threshold
                    results.append(DetectionResult(
                        technology=tech_key,
                        name=tech_entry.name,
                        category=tech_entry.category,
                        confidence=overall_confidence,
                        matched_indicators=matched_indicators,
                        discovery_paths=tech_entry.discovery_paths
                    ))
        
        # Sort by confidence
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results
    
    def _match_response_patterns(self, content: str, patterns: List[str]) -> float:
        """Match response patterns with confidence scoring"""
        if not patterns or not content:
            return 0.0
        
        matches = 0
        for pattern in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                matches += 1
        
        return matches / len(patterns)
    
    def _match_header_patterns(self, headers: Dict[str, str], patterns: List[str]) -> float:
        """Match header patterns"""
        if not patterns or not headers:
            return 0.0
        
        matches = 0
        for pattern in patterns:
            if self._match_headers_against_pattern(headers, pattern):
                matches += 1
                
        return matches / len(patterns)
    
    def _match_headers_against_pattern(self, headers: Dict[str, str], pattern: str) -> bool:
        """Check if any header matches the pattern"""
        for header_name, header_value in headers.items():
            combined = f"{header_name.lower()}: {header_value.lower()}"
            if re.search(pattern, combined, re.IGNORECASE):
                return True
        return False
    
    def _match_path_patterns(self, path: str, patterns: List[str]) -> float:
        """Match URL path patterns"""
        if not patterns or not path:
            return 0.0
        
        matches = 0
        for pattern in patterns:
            if re.search(pattern, path, re.IGNORECASE):
                matches += 1
                
        return matches / len(patterns)
    
    def _fuzzy_match_content(self, content: str, keywords: List[str], threshold: int) -> float:
        """Fuzzy match keywords in content"""
        if not RAPIDFUZZ_AVAILABLE or not keywords or not content:
            return 0.0
        
        # Extract words from content
        words = re.findall(r'\w+', content.lower())
        if not words:
            return 0.0
        
        total_score = 0
        matched_keywords = 0
        
        for keyword in keywords:
            # Find best matching word for this keyword
            if words:
                best_match = process.extractOne(keyword.lower(), words, scorer=fuzz.ratio)
                if best_match and best_match[1] >= threshold:
                    total_score += best_match[1] / 100.0  # Convert to 0-1 scale
                    matched_keywords += 1
        
        if matched_keywords == 0:
            return 0.0
            
        return total_score / len(keywords)  # Average score


def load_technology_database(json_data: Dict[str, Any]) -> TechnologyDatabase:
    """Load technology database from JSON data"""
    
    # Transform the JSON structure to match our model
    db_data = {}
    
    for category_name, technologies in json_data.items():
        category_entries = {}
        
        for tech_key, tech_data in technologies.items():
            # Create TechnologyIndicators
            indicators_data = tech_data.get('indicators', {})
            indicators = TechnologyIndicators(
                response_patterns=indicators_data.get('response_patterns', []),
                header_patterns=indicators_data.get('header_patterns', []),
                path_patterns=indicators_data.get('path_patterns', []),
                file_extensions=indicators_data.get('file_extensions', []),
                fuzzy_keywords=indicators_data.get('fuzzy_keywords', [])
            )
            
            # Map category name to enum
            category_map = {
                'web_frameworks': TechnologyCategory.WEB_FRAMEWORK,
                'databases': TechnologyCategory.DATABASE,
                'admin_panels': TechnologyCategory.ADMIN_PANEL,
                'monitoring_tools': TechnologyCategory.MONITORING
            }
            
            category = category_map.get(category_name, TechnologyCategory.WEB_FRAMEWORK)
            
            # Create TechnologyEntry
            entry = TechnologyEntry(
                name=tech_data.get('name', tech_key.title()),
                category=category,
                description=tech_data.get('description'),
                indicators=indicators,
                discovery_paths=tech_data.get('discovery_paths', []),
                confidence_weights=tech_data.get('confidence_weights')
            )
            
            category_entries[tech_key] = entry
        
        db_data[category_name] = category_entries
    
    return TechnologyDatabase(**db_data)


def load_technology_database_from_file(file_path: Path) -> TechnologyDatabase:
    """Load technology database from JSON file"""
    with open(file_path, 'r') as f:
        json_data = json.load(f)
    return load_technology_database(json_data)