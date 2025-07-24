"""Pydantic models for Mini Spider workflow"""
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel, Field, validator, HttpUrl
from urllib.parse import urlparse


class DiscoverySource(Enum):
    """Source of URL discovery"""
    SEED = "seed"
    HTTP_03 = "http_03"
    CUSTOM_CRAWLER = "custom_crawler"
    HAKRAWLER = "hakrawler"
    HTML_PARSING = "html_parsing"
    REDIRECT = "redirect"


class URLCategory(Enum):
    """URL categorization"""
    ADMIN = "admin"
    API = "api"
    CONFIG = "config"
    AUTH = "auth"
    DOCS = "docs"
    DEV = "dev"
    STATIC = "static"
    APPLICATION = "application"
    ROOT = "root"
    TOPLEVEL = "toplevel"
    OTHER = "other"
    UNKNOWN = "unknown"


class SeverityLevel(Enum):
    """Severity levels for findings"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class CrawledURL(BaseModel):
    """Represents a discovered URL with metadata"""
    url: str = Field(..., description="The discovered URL")
    source: DiscoverySource = Field(..., description="How this URL was discovered")
    status_code: Optional[int] = Field(None, description="HTTP status code if tested")
    content_type: Optional[str] = Field(None, description="Content-Type header")
    content_length: Optional[int] = Field(None, description="Content-Length in bytes")
    response_time: Optional[float] = Field(None, description="Response time in seconds")
    discovered_at: datetime = Field(default_factory=datetime.now, description="When URL was discovered")
    tested_at: Optional[datetime] = Field(None, description="When URL was last tested")
    redirect_url: Optional[str] = Field(None, description="URL redirected to")
    error_message: Optional[str] = Field(None, description="Error message if request failed")
    depth: Optional[int] = Field(None, description="URL depth (path segments)")
    category: Optional[URLCategory] = Field(None, description="URL category")
    
    @validator('url')
    def validate_url(cls, v):
        """Validate URL format"""
        try:
            parsed = urlparse(v)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL format")
            if parsed.scheme not in ['http', 'https']:
                raise ValueError("Only HTTP/HTTPS URLs are supported")
            return v
        except Exception as e:
            raise ValueError(f"Invalid URL: {e}")
    
    @validator('status_code')
    def validate_status_code(cls, v):
        """Validate HTTP status code"""
        if v is not None and (v < 100 or v > 599):
            raise ValueError("Invalid HTTP status code")
        return v
    
    def __hash__(self):
        """Make CrawledURL hashable for deduplication"""
        return hash(self.url)
    
    def __eq__(self, other):
        """Check equality based on URL"""
        if isinstance(other, CrawledURL):
            return self.url == other.url
        return False
    
    class Config:
        use_enum_values = True


class InterestingFinding(BaseModel):
    """Represents an interesting finding from URL analysis"""
    url: str = Field(..., description="The interesting URL")
    finding_type: str = Field(..., description="Type of finding")
    severity: SeverityLevel = Field(..., description="Severity level")
    reason: str = Field(..., description="Why this is interesting")
    pattern: Optional[str] = Field(None, description="Pattern that matched")
    source: DiscoverySource = Field(..., description="How this URL was discovered")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        use_enum_values = True


class CrawlerStats(BaseModel):
    """Statistics from crawling operations"""
    urls_discovered: int = Field(default=0, description="Total URLs discovered")
    urls_tested: int = Field(default=0, description="Total URLs tested")
    successful_requests: int = Field(default=0, description="Successful HTTP requests")
    failed_requests: int = Field(default=0, description="Failed HTTP requests")
    redirects_followed: int = Field(default=0, description="Redirects followed")
    errors_encountered: int = Field(default=0, description="Errors encountered")
    average_response_time: Optional[float] = Field(None, description="Average response time")
    total_bytes_downloaded: int = Field(default=0, description="Total bytes downloaded")
    unique_domains: int = Field(default=0, description="Unique domains discovered")
    
    def add_response(self, success: bool, response_time: Optional[float] = None, 
                    content_length: Optional[int] = None):
        """Add response statistics"""
        self.urls_tested += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        if response_time is not None:
            if self.average_response_time is None:
                self.average_response_time = response_time
            else:
                # Running average
                total_time = self.average_response_time * (self.urls_tested - 1) + response_time
                self.average_response_time = total_time / self.urls_tested
        
        if content_length is not None:
            self.total_bytes_downloaded += content_length


class HakrawlerResult(BaseModel):
    """Results from hakrawler execution"""
    success: bool = Field(..., description="Whether hakrawler executed successfully")
    urls_found: List[str] = Field(default_factory=list, description="URLs discovered by hakrawler")
    execution_time: float = Field(..., description="Execution time in seconds")
    command_used: List[str] = Field(default_factory=list, description="Command line used")
    stdout: Optional[str] = Field(None, description="Standard output")
    stderr: Optional[str] = Field(None, description="Standard error")
    return_code: Optional[int] = Field(None, description="Process return code")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class CustomCrawlerResult(BaseModel):
    """Results from custom crawler execution"""
    success: bool = Field(..., description="Whether custom crawler executed successfully")
    urls_found: List[CrawledURL] = Field(default_factory=list, description="URLs discovered")
    execution_time: float = Field(..., description="Execution time in seconds")
    stats: CrawlerStats = Field(default_factory=CrawlerStats, description="Crawling statistics")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class SpiderStatistics(BaseModel):
    """Overall statistics for the spider workflow"""
    total_seed_urls: int = Field(default=0, description="Number of seed URLs")
    total_discovered_urls: int = Field(default=0, description="Total URLs discovered")
    unique_urls_after_dedup: int = Field(default=0, description="Unique URLs after deduplication")
    urls_by_source: Dict[str, int] = Field(default_factory=dict, description="URLs by discovery source")
    urls_by_category: Dict[str, int] = Field(default_factory=dict, description="URLs by category")
    urls_by_status_code: Dict[int, int] = Field(default_factory=dict, description="URLs by HTTP status")
    interesting_findings_count: int = Field(default=0, description="Number of interesting findings")
    execution_time: float = Field(default=0.0, description="Total execution time")
    tools_used: List[str] = Field(default_factory=list, description="Tools that were used")
    
    def update_from_urls(self, urls: List[CrawledURL]):
        """Update statistics from URL list"""
        self.total_discovered_urls = len(urls)
        
        # Count by source
        self.urls_by_source = {}
        for url in urls:
            source = url.source.value if hasattr(url.source, 'value') else str(url.source)
            self.urls_by_source[source] = self.urls_by_source.get(source, 0) + 1
        
        # Count by category
        self.urls_by_category = {}
        for url in urls:
            if url.category:
                category = url.category.value if hasattr(url.category, 'value') else str(url.category)
                self.urls_by_category[category] = self.urls_by_category.get(category, 0) + 1
        
        # Count by status code
        self.urls_by_status_code = {}
        for url in urls:
            if url.status_code:
                self.urls_by_status_code[url.status_code] = self.urls_by_status_code.get(url.status_code, 0) + 1


class MiniSpiderResult(BaseModel):
    """Complete result from Mini Spider workflow"""
    target: str = Field(..., description="Target that was scanned")
    seed_urls: List[CrawledURL] = Field(default_factory=list, description="Initial seed URLs")
    discovered_urls: List[CrawledURL] = Field(default_factory=list, description="All discovered URLs")
    categorized_results: Dict[str, List[CrawledURL]] = Field(default_factory=dict, description="URLs by category")
    interesting_findings: List[InterestingFinding] = Field(default_factory=list, description="Interesting findings")
    statistics: SpiderStatistics = Field(default_factory=SpiderStatistics, description="Execution statistics")
    summary: Dict[str, Any] = Field(default_factory=dict, description="Summary information")
    execution_time: float = Field(default=0.0, description="Total execution time")
    
    # Tool-specific results
    hakrawler_result: Optional[HakrawlerResult] = Field(None, description="Hakrawler execution result")
    custom_crawler_result: Optional[CustomCrawlerResult] = Field(None, description="Custom crawler result")
    
    # Enhanced analysis results
    enhanced_analysis: Optional[Dict[str, Any]] = Field(None, description="Enhanced intelligence analysis results")
    
    # Metadata
    scan_timestamp: datetime = Field(default_factory=datetime.now, description="When scan was performed")
    workflow_version: str = Field(default="1.0.0", description="Workflow version")
    tools_available: Dict[str, bool] = Field(default_factory=dict, description="Tool availability")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'target': self.target,
            'seed_urls': [url.model_dump() for url in self.seed_urls],
            'discovered_urls': [url.model_dump() for url in self.discovered_urls],
            'categorized_results': {
                category: [url.model_dump() for url in urls] 
                for category, urls in self.categorized_results.items()
            },
            'interesting_findings': [finding.model_dump() for finding in self.interesting_findings],
            'statistics': self.statistics.model_dump() if hasattr(self.statistics, 'model_dump') else self.statistics,
            'summary': self.summary,
            'execution_time': self.execution_time,
            'hakrawler_result': self.hakrawler_result.model_dump() if self.hakrawler_result else None,
            'custom_crawler_result': self.custom_crawler_result.model_dump() if self.custom_crawler_result else None,
            'enhanced_analysis': self.enhanced_analysis,
            'scan_timestamp': self.scan_timestamp.isoformat(),
            'workflow_version': self.workflow_version,
            'tools_available': self.tools_available
        }
    
    def get_urls_by_category(self, category: URLCategory) -> List[CrawledURL]:
        """Get URLs for a specific category"""
        category_str = category.value if hasattr(category, 'value') else str(category)
        return self.categorized_results.get(category_str, [])
    
    def get_urls_by_source(self, source: DiscoverySource) -> List[CrawledURL]:
        """Get URLs discovered by a specific source"""
        return [url for url in self.discovered_urls if url.source == source]
    
    def get_findings_by_severity(self, severity: SeverityLevel) -> List[InterestingFinding]:
        """Get findings for a specific severity level"""
        return [finding for finding in self.interesting_findings if finding.severity == severity]
    
    def add_discovered_url(self, url: CrawledURL):
        """Add a discovered URL and update statistics"""
        if url not in self.discovered_urls:
            self.discovered_urls.append(url)
            
            # Update categorized results
            if url.category:
                category_str = url.category.value if hasattr(url.category, 'value') else str(url.category)
                if category_str not in self.categorized_results:
                    self.categorized_results[category_str] = []
                self.categorized_results[category_str].append(url)
            
            # Update statistics
            self.statistics.update_from_urls(self.discovered_urls)
    
    class Config:
        use_enum_values = True


class ToolCompatibilityResult(BaseModel):
    """Result of tool compatibility check"""
    tool_name: str = Field(..., description="Name of the tool")
    available: bool = Field(..., description="Whether tool is available")
    version: Optional[str] = Field(None, description="Tool version if available")
    path: Optional[str] = Field(None, description="Path to tool executable")
    error_message: Optional[str] = Field(None, description="Error message if not available")
    validated: bool = Field(default=False, description="Whether tool was validated")


class WorkflowConfig(BaseModel):
    """Configuration for the Mini Spider workflow"""
    max_total_urls: int = Field(default=1000, ge=1, le=10000, description="Maximum URLs to discover")
    max_crawl_time: int = Field(default=300, ge=30, le=3600, description="Maximum crawl time in seconds")
    max_concurrent_crawls: int = Field(default=5, ge=1, le=20, description="Maximum concurrent crawls")
    enable_hakrawler: bool = Field(default=True, description="Enable hakrawler tool")
    enable_custom_crawler: bool = Field(default=True, description="Enable custom crawler")
    categorize_results: bool = Field(default=True, description="Categorize discovered URLs")
    extract_interesting: bool = Field(default=True, description="Extract interesting findings")
    save_to_workspace: bool = Field(default=True, description="Save results to workspace")
    
    @validator('max_total_urls')
    def validate_max_urls(cls, v):
        if v < 1:
            raise ValueError("max_total_urls must be at least 1")
        return v
    
    @validator('max_crawl_time')
    def validate_crawl_time(cls, v):
        if v < 30:
            raise ValueError("max_crawl_time must be at least 30 seconds")
        return v