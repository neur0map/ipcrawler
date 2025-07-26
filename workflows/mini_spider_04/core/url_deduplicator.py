"""Advanced URL deduplication utilities"""
import hashlib
import re
from typing import List, Set, Dict, Any, Optional, Tuple
from urllib.parse import urlparse, parse_qs, urlunparse, unquote
from collections import defaultdict

from ..models import CrawledURL
from ..utils import URLNormalizer


class AdvancedURLDeduplicator:
    """Advanced URL deduplication with similarity detection and clustering"""
    
    def __init__(self, similarity_threshold: float = 0.8, enable_clustering: bool = True):
        self.similarity_threshold = similarity_threshold
        self.enable_clustering = enable_clustering
        self.seen_signatures: Set[str] = set()
        self.url_clusters: Dict[str, List[str]] = defaultdict(list)
        self.parameter_patterns: Dict[str, Set[str]] = defaultdict(set)
        
    def deduplicate_advanced(self, urls: List[CrawledURL]) -> Tuple[List[CrawledURL], Dict[str, Any]]:
        """
        Advanced deduplication with detailed statistics
        Returns (deduplicated_urls, stats)
        """
        if not urls:
            return [], {'total_input': 0, 'total_output': 0, 'duplicates_removed': 0}
        
        original_count = len(urls)
        unique_urls = []
        duplicate_count = 0
        
        # Phase 1: Basic signature deduplication
        for url in urls:
            signature = self._get_enhanced_signature(url.url)
            
            if signature not in self.seen_signatures:
                self.seen_signatures.add(signature)
                unique_urls.append(url)
            else:
                duplicate_count += 1
        
        # Phase 2: Similarity-based deduplication
        if self.enable_clustering and len(unique_urls) > 1:
            clustered_urls, cluster_stats = self._cluster_similar_urls(unique_urls)
            unique_urls = clustered_urls
            duplicate_count += cluster_stats['removed_count']
        
        # Phase 3: Parameter pattern analysis
        final_urls = self._deduplicate_by_parameter_patterns(unique_urls)
        duplicate_count += len(unique_urls) - len(final_urls)
        
        stats = {
            'total_input': original_count,
            'total_output': len(final_urls),
            'duplicates_removed': duplicate_count,
            'deduplication_rate': duplicate_count / original_count if original_count > 0 else 0,
            'unique_clusters': len(self.url_clusters),
            'parameter_patterns_found': len(self.parameter_patterns)
        }
        
        return final_urls, stats
    
    def _get_enhanced_signature(self, url: str) -> str:
        """Generate enhanced signature for URL deduplication"""
        try:
            parsed = urlparse(url)
            
            # Normalize components
            scheme = parsed.scheme.lower()
            netloc = parsed.netloc.lower()
            
            # Remove default ports
            if netloc.endswith(':80') and scheme == 'http':
                netloc = netloc[:-3]
            elif netloc.endswith(':443') and scheme == 'https':
                netloc = netloc[:-4]
            
            # Normalize path
            path = unquote(parsed.path) if parsed.path else '/'
            if path != '/' and path.endswith('/'):
                path = path.rstrip('/')
            
            # Normalize and sort query parameters
            query_signature = self._normalize_query_parameters(parsed.query)
            
            # Create signature
            signature_components = [scheme, netloc, path, query_signature]
            signature_string = '|'.join(signature_components)
            
            return hashlib.md5(signature_string.encode()).hexdigest()
            
        except Exception:
            # Fallback to simple hash
            return hashlib.md5(url.encode()).hexdigest()
    
    def _normalize_query_parameters(self, query: str) -> str:
        """Normalize query parameters for consistent signatures"""
        if not query:
            return ''
        
        try:
            params = parse_qs(query, keep_blank_values=True)
            
            # Sort parameters and values
            normalized_params = []
            for key in sorted(params.keys()):
                values = sorted(params[key])
                for value in values:
                    normalized_params.append(f"{key}={value}")
            
            return '&'.join(normalized_params)
            
        except Exception:
            return query
    
    def _cluster_similar_urls(self, urls: List[CrawledURL]) -> Tuple[List[CrawledURL], Dict[str, Any]]:
        """Cluster similar URLs and keep representative from each cluster"""
        clusters = []
        clustered_urls = []
        removed_count = 0
        
        for url in urls:
            # Find if this URL belongs to an existing cluster
            cluster_found = False
            
            for cluster in clusters:
                representative = cluster[0]
                if self._are_urls_similar(url.url, representative.url):
                    cluster.append(url)
                    cluster_found = True
                    removed_count += 1
                    break
            
            if not cluster_found:
                # Start new cluster
                clusters.append([url])
                clustered_urls.append(url)
        
        # Store cluster information
        for i, cluster in enumerate(clusters):
            cluster_key = f"cluster_{i}"
            self.url_clusters[cluster_key] = [u.url for u in cluster]
        
        stats = {
            'clusters_created': len(clusters),
            'removed_count': removed_count
        }
        
        return clustered_urls, stats
    
    def _are_urls_similar(self, url1: str, url2: str) -> bool:
        """Check if two URLs are similar enough to be considered duplicates"""
        try:
            parsed1 = urlparse(url1)
            parsed2 = urlparse(url2)
            
            # Must have same scheme, host, and base path
            if (parsed1.scheme != parsed2.scheme or 
                parsed1.netloc.lower() != parsed2.netloc.lower()):
                return False
            
            # Path similarity check
            path_similarity = self._calculate_path_similarity(parsed1.path, parsed2.path)
            if path_similarity < 0.7:
                return False
            
            # Parameter similarity check
            param_similarity = self._calculate_parameter_similarity(parsed1.query, parsed2.query)
            
            # Overall similarity score
            overall_similarity = (path_similarity + param_similarity) / 2
            
            return overall_similarity >= self.similarity_threshold
            
        except Exception:
            return False
    
    def _calculate_path_similarity(self, path1: str, path2: str) -> float:
        """Calculate similarity between two URL paths"""
        if path1 == path2:
            return 1.0
        
        # Tokenize paths
        tokens1 = set([t for t in path1.split('/') if t])
        tokens2 = set([t for t in path2.split('/') if t])
        
        if not tokens1 and not tokens2:
            return 1.0
        
        if not tokens1 or not tokens2:
            return 0.0
        
        # Jaccard similarity
        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_parameter_similarity(self, query1: str, query2: str) -> float:
        """Calculate similarity between query parameters"""
        if query1 == query2:
            return 1.0
        
        try:
            params1 = set(parse_qs(query1 or '').keys())
            params2 = set(parse_qs(query2 or '').keys())
            
            if not params1 and not params2:
                return 1.0
            
            if not params1 or not params2:
                return 0.5  # Different but not completely dissimilar
            
            # Jaccard similarity for parameter names
            intersection = len(params1.intersection(params2))
            union = len(params1.union(params2))
            
            return intersection / union if union > 0 else 0.0
            
        except Exception:
            return 0.5
    
    def _deduplicate_by_parameter_patterns(self, urls: List[CrawledURL]) -> List[CrawledURL]:
        """Remove URLs that follow similar parameter patterns"""
        if len(urls) <= 1:
            return urls
        
        # Group URLs by base URL (without query parameters)
        base_url_groups = defaultdict(list)
        
        for url in urls:
            try:
                parsed = urlparse(url.url)
                base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                base_url_groups[base_url].append(url)
            except:
                # Keep URLs we can't parse
                continue
        
        deduplicated_urls = []
        
        for base_url, url_group in base_url_groups.items():
            if len(url_group) == 1:
                # Single URL for this base, keep it
                deduplicated_urls.extend(url_group)
            else:
                # Multiple URLs for same base, analyze parameter patterns
                representative_urls = self._select_representative_urls(url_group)
                deduplicated_urls.extend(representative_urls)
        
        return deduplicated_urls
    
    def _select_representative_urls(self, url_group: List[CrawledURL]) -> List[CrawledURL]:
        """Select representative URLs from a group with same base URL"""
        if len(url_group) <= 3:
            # Keep all if small group
            return url_group
        
        # Analyze parameter patterns
        param_patterns = self._analyze_parameter_patterns([u.url for u in url_group])
        
        # Group by parameter pattern
        pattern_groups = defaultdict(list)
        for url in url_group:
            pattern = self._get_parameter_pattern(url.url)
            pattern_groups[pattern].append(url)
        
        # Select representative from each pattern group
        representatives = []
        for pattern, pattern_urls in pattern_groups.items():
            # Prefer URLs with successful status codes
            sorted_urls = sorted(
                pattern_urls,
                key=lambda u: (
                    -(u.status_code or 0) if u.status_code and 200 <= u.status_code < 300 else 0,
                    -(len(u.url)),  # Prefer shorter URLs
                    u.url  # Alphabetical as tiebreaker
                )
            )
            representatives.append(sorted_urls[0])
        
        # Limit to reasonable number of representatives
        return representatives[:5]
    
    def _analyze_parameter_patterns(self, urls: List[str]) -> Dict[str, int]:
        """Analyze parameter patterns in URL group"""
        patterns = defaultdict(int)
        
        for url in urls:
            pattern = self._get_parameter_pattern(url)
            patterns[pattern] += 1
        
        return dict(patterns)
    
    def _get_parameter_pattern(self, url: str) -> str:
        """Get parameter pattern signature for URL"""
        try:
            parsed = urlparse(url)
            if not parsed.query:
                return 'no_params'
            
            params = parse_qs(parsed.query)
            param_names = sorted(params.keys())
            
            # Create pattern based on parameter names and value types
            pattern_parts = []
            for param in param_names:
                values = params[param]
                if values:
                    value = values[0]
                    if value.isdigit():
                        pattern_parts.append(f"{param}:int")
                    elif re.match(r'^[a-f0-9-]{32,}$', value, re.IGNORECASE):
                        pattern_parts.append(f"{param}:uuid")
                    elif len(value) > 50:
                        pattern_parts.append(f"{param}:long")
                    else:
                        pattern_parts.append(f"{param}:str")
                else:
                    pattern_parts.append(f"{param}:empty")
            
            return '&'.join(pattern_parts)
            
        except Exception:
            return 'unknown'
    
    def get_deduplication_report(self) -> Dict[str, Any]:
        """Generate detailed deduplication report"""
        return {
            'total_signatures': len(self.seen_signatures),
            'clusters_created': len(self.url_clusters),
            'cluster_details': {
                cluster_id: {
                    'urls': urls,
                    'count': len(urls)
                }
                for cluster_id, urls in self.url_clusters.items()
            },
            'parameter_patterns': {
                pattern: list(params)
                for pattern, params in self.parameter_patterns.items()
            }
        }
    
    def reset(self):
        """Reset deduplicator state"""
        self.seen_signatures.clear()
        self.url_clusters.clear()
        self.parameter_patterns.clear()


def deduplicate_urls_advanced(urls: List[CrawledURL], 
                             similarity_threshold: float = 0.8,
                             enable_clustering: bool = True) -> Tuple[List[CrawledURL], Dict[str, Any]]:
    """
    Convenience function for advanced URL deduplication
    Returns (deduplicated_urls, stats)
    """
    deduplicator = AdvancedURLDeduplicator(similarity_threshold, enable_clustering)
    return deduplicator.deduplicate_advanced(urls)