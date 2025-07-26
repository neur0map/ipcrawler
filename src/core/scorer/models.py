"""
"""



    """Confidence levels for scoring results."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


    """Detailed breakdown of scoring components."""
    exact_match: float = Field(0.0, ge=0.0, le=1.0, description="Score from exact tech+port match")
    tech_category: float = Field(0.0, ge=0.0, le=1.0, description="Score from tech category match")
    port_context: float = Field(0.0, ge=0.0, le=1.0, description="Score from port category match")
    service_keywords: float = Field(0.0, ge=0.0, le=1.0, description="Score from service keyword match")
    generic_fallback: float = Field(0.0, ge=0.0, le=1.0, description="Score from generic fallback")
    
    @field_validator('*')
    @classmethod
        """Ensure all scores are between 0 and 1."""
        if not 0.0 <= v <= 1.0:
    
        """Convert to dictionary for easy serialization."""
            "exact_match": self.exact_match,
            "tech_category": self.tech_category,
            "port_context": self.port_context,
            "service_keywords": self.service_keywords,
            "generic_fallback": self.generic_fallback
        }


    """Individual wordlist with its score and reasoning."""
    wordlist: str = Field(..., description="Wordlist filename")
    total_score: float = Field(..., ge=0.0, le=1.0, description="Combined score for this wordlist")
    breakdown: ScoreBreakdown = Field(..., description="Score component breakdown")
    matched_rules: List[str] = Field(default_factory=list, description="Rules that matched")
    confidence: Confidence = Field(..., description="Confidence level based on score")
    
    @field_validator('total_score')
    @classmethod
        """Round total score to 3 decimal places."""


    """Input context for scoring wordlists."""
    target: str = Field(..., description="Target IP or hostname")
    port: int = Field(..., ge=1, le=65535, description="Port number")
    service: Optional[str] = Field(None, description="Service description from scan")
    tech: Optional[str] = Field(None, description="Detected technology/software")
    os: Optional[str] = Field(None, description="Detected operating system")
    version: Optional[str] = Field(None, description="Service version")
    headers: Optional[Dict[str, str]] = Field(None, description="HTTP headers if available")
    spider_data: Optional[Dict[str, Any]] = Field(None, description="Spider intelligence data from mini_spider_04")
    
        """Generate a cache key for this scoring context."""
        anon_context = AnonymizedScoringContext.from_scoring_context(self)


    """Privacy-focused scoring context without sensitive target information."""
    port_category: str = Field(..., description="Port category (web, database, admin, etc.)")
    port: int = Field(..., ge=1, le=65535, description="Port number")
    service_fingerprint: str = Field(..., description="Hash of service details (no target info)")
    service_length: int = Field(..., description="Length of service description for similarity")
    tech_family: str = Field(..., description="Technology family (web_server, cms, etc.)")
    tech: Optional[str] = Field(None, description="Detected technology/software")
    os_family: Optional[str] = Field(None, description="OS family (linux, windows, etc.)")
    version: Optional[str] = Field(None, description="Service version")
    has_headers: bool = Field(False, description="Whether HTTP headers were present")
    
    @field_validator('port')
    @classmethod
        """Validate port is in valid range."""
        if not 1 <= v <= 65535:
    
    @field_validator('tech')
    @classmethod
        """Normalize technology name to lowercase."""
    
    @classmethod
        """Create anonymized context from regular scoring context."""
        
        service_data = f"{context.service}:{context.tech or ''}:{context.version or ''}"
        service_fingerprint = hashlib.md5(service_data.encode()).hexdigest()[:8]
        
        # Determine categories
        port_category = cls._get_port_category(context.port)
        tech_family = cls._get_tech_family(context.tech)
        os_family = cls._get_os_family(context.os) if context.os else None
        
            port_category=port_category,
            port=context.port,
            service_fingerprint=service_fingerprint,
            service_length=len(context.service) if context.service else 0,
            tech_family=tech_family,
            tech=context.tech,
            os_family=os_family,
            version=context.version,
            has_headers=bool(context.headers)
        )
    
    @staticmethod
        """Categorize port for privacy-safe grouping."""
        categories = {
            "web": [80, 8080, 8000, 8888, 3000, 5000, 9000, 4200, 3001],
            "web_secure": [443, 8443, 9443, 4443],
            "database": [3306, 5432, 1433, 27017, 6379, 5984, 9200, 7474, 8529],
            "admin": [8080, 9090, 10000, 8834, 7001, 4848, 8161, 9990],
            "mail": [25, 465, 587, 110, 995, 143, 993, 2525],
            "file_transfer": [21, 22, 873, 445, 139, 2049, 111],
            "remote_access": [22, 23, 3389, 5900, 5901, 1194, 4444],
            "proxy": [3128, 8118, 8123, 1080, 9050],
            "development": [3000, 4200, 5000, 8000, 9000, 3001, 5001, 8001]
        }
        
    
    @staticmethod
        """Categorize technology into families."""
        
        tech_lower = tech.lower()
        
        families = {
            "web_server": ["apache", "nginx", "iis", "lighttpd", "caddy", "tomcat", "jetty"],
            "cms": ["wordpress", "drupal", "joomla", "typo3", "magento", "shopify"],
            "database": ["mysql", "postgresql", "mongodb", "redis", "cassandra", "oracle"],
            "framework": ["django", "flask", "rails", "laravel", "symfony", "express"],
            "admin_panel": ["phpmyadmin", "adminer", "webmin", "cpanel", "plesk"],
            "mail_server": ["postfix", "exim", "sendmail", "exchange", "zimbra"],
            "monitoring": ["nagios", "zabbix", "prometheus", "grafana", "kibana"],
            "ci_cd": ["jenkins", "gitlab", "github", "bitbucket", "bamboo"],
            "container": ["docker", "kubernetes", "openshift", "rancher"]
        }
        
        
    
    @staticmethod
        """Categorize OS into families."""
        
        os_lower = os.lower()
        
    
        """Generate a privacy-safe cache key."""
        # Use only non-sensitive information
        key_parts = [
        ]
    


    """Complete scoring result with explanation."""
    score: float = Field(..., ge=0.0, le=1.0, description="Highest score achieved")
    explanation: ScoreBreakdown = Field(..., description="Score breakdown")
    wordlists: List[str] = Field(..., description="Recommended wordlists")
    matched_rules: List[str] = Field(..., description="All rules that matched")
    fallback_used: bool = Field(..., description="Whether generic fallback was used")
    cache_key: str = Field(..., description="Cache key for this result")
    confidence: Confidence = Field(..., description="Overall confidence level")
    
    # Entropy-related fields
    entropy_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Entropy score for recommendation diversity")
    diversification_applied: bool = Field(False, description="Whether diversification was applied")
    frequency_adjustments: Optional[Dict[str, float]] = Field(None, description="Rule frequency adjustments applied")
    synergy_bonuses: Optional[Dict[str, float]] = Field(None, description="Tech+path synergy bonuses applied")
    
    @field_validator('score')
    @classmethod
        """Round score to 3 decimal places."""
    
    @field_validator('confidence')
    @classmethod
        """Set confidence based on score if not provided."""
            score = info.data['score']
            if score >= 0.8:
            elif score >= 0.6:
    
        """Get summary of entropy-related information."""
            "entropy_score": self.entropy_score,
            "diversification_applied": self.diversification_applied,
            "frequency_adjustments_count": len(self.frequency_adjustments or {}),
            "synergy_bonuses_count": len(self.synergy_bonuses or {}),
            "quality_indicators": {
                "has_entropy_data": self.entropy_score is not None,
                "is_diversified": self.diversification_applied,
                "has_frequency_boost": bool(self.frequency_adjustments),
                "has_synergy": bool(self.synergy_bonuses)
            }
        }


    """Entry for caching scoring results."""
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When this entry was created")
    context: ScoringContext = Field(..., description="Input context")
    result: ScoringResult = Field(..., description="Scoring result")
    outcome: Optional[Dict[str, Any]] = Field(None, description="Actual outcome if tracked")


    """Privacy-focused cache entry without sensitive information."""
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When this entry was created")
    context: AnonymizedScoringContext = Field(..., description="Anonymized context")
    result: ScoringResult = Field(..., description="Scoring result")
    outcome: Optional[Dict[str, Any]] = Field(None, description="Actual outcome if tracked")
    
        json_encoders = {
        }
    
    @classmethod
        """Create anonymized cache entry from regular entry."""
        anon_context = AnonymizedScoringContext.from_scoring_context(entry.context)
            timestamp=entry.timestamp,
            context=anon_context,
            result=entry.result,
            outcome=entry.outcome
        )
    
        """Extract entropy-related data from this cache entry."""
            "timestamp": self.timestamp,
            "wordlists": self.result.wordlists,
            "matched_rules": self.result.matched_rules,
            "context_key": f"{self.context.tech or 'unknown'}:{self.context.port}",
            "entropy_score": self.result.entropy_score,
            "diversification_applied": self.result.diversification_applied
        }
    
        json_encoders = {
        }


    """Index for the cache system."""
    total_selections: int = Field(0, description="Total number of selections cached")
    by_tech: Dict[str, int] = Field(default_factory=dict, description="Selections by technology")
    by_port: Dict[str, int] = Field(default_factory=dict, description="Selections by port category")
    fallback_usage: Dict[str, Any] = Field(
        default_factory=lambda: {"count": 0, "percentage": 0.0},
        description="Fallback usage statistics"
    )
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update time")
    
        json_encoders = {
        }
    
        """Update index statistics with a new entry."""
        self.total_selections += 1
        
        tech = entry.context.tech or "unknown"
        self.by_tech[tech] = self.by_tech.get(tech, 0) + 1
        
        port_category = self._get_port_category(entry.context.port)
        self.by_port[port_category] = self.by_port.get(port_category, 0) + 1
        
            self.fallback_usage["count"] += 1
        
        # Recalculate percentage
            self.fallback_usage["percentage"] = round(
                (self.fallback_usage["count"] / self.total_selections) * 100, 2
            )
        
        self.last_updated = datetime.utcnow()
    
        """Determine port category."""
        web_ports = [80, 443, 8080, 8443, 8000, 8888]
        db_ports = [3306, 5432, 1433, 27017, 6379]
        admin_ports = [8080, 9090, 10000, 8834, 8443]
        


    """Individual scoring rule."""
    name: str = Field(..., description="Rule name")
    weight: float = Field(..., ge=0.0, le=1.0, description="Rule weight")
    description: str = Field(..., description="Rule description")
    category: str = Field(..., description="Rule category (exact, tech, port, generic)")
    
    @field_validator('weight')
    @classmethod
        """Ensure weight is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
