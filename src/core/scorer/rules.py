"""
"""

)

logger = logging.getLogger(__name__)


    """Engine for applying scoring rules with fallback hierarchy."""
    
        self.rules: List[ScoringRule] = []
        self._rule_frequency_cache = {}  # Cache for rule frequency data
        self._last_frequency_update = None
    
        """Pre-compile regex patterns for efficiency."""
        self.tech_patterns = {}
                self.tech_patterns[category] = re.compile(
                )
    
        """
        
        """
        
        wordlists = get_exact_match(context.tech, context.port)
            rule_name = f"exact:{context.tech}:{context.port}"
            
            # Apply frequency-based scoring adjustment
            base_score = 1.0
            adjusted_score = self._apply_frequency_adjustment(rule_name, base_score)
            
            # Add synergy bonus for tech+path combinations
            synergy_bonus = self._calculate_synergy_bonus(context, wordlists)
            final_score = min(1.0, adjusted_score + synergy_bonus)
            
            logger.debug(f"Exact match scoring: base={base_score:.3f}, adjusted={adjusted_score:.3f}, synergy={synergy_bonus:.3f}, final={final_score:.3f}")
            
        
    
        """
        
        """
        wordlists = []
        matched_rules = []
        score = 0.0
        
        # First try exact tech match
                    rule_name = f"tech_category:{category}"
                    
                    # Apply frequency-based scoring
                    base_score = config["weight"]
                    adjusted_score = self._apply_frequency_adjustment(rule_name, base_score)
                    synergy_bonus = self._calculate_synergy_bonus(context, wordlists)
                    score = min(1.0, adjusted_score + synergy_bonus)
                    
        
        # Fallback to pattern matching on service description
                config = TECH_CATEGORY_RULES[category]
                rule_name = f"tech_pattern:{category}"
                
                # Lower base score for pattern match vs exact match
                base_score = config["weight"] * 0.75
                adjusted_score = self._apply_frequency_adjustment(rule_name, base_score)
                synergy_bonus = self._calculate_synergy_bonus(context, wordlists)
                score = min(1.0, adjusted_score + synergy_bonus)
                
        
    
        """
        
        """
        wordlists = []
        matched_rules = []
        score = 0.0
        
        # Find all matching categories and sort by priority
        matching_categories = []
                priority = config.get("priority", 999)  # Default to low priority
        
            # Sort by priority (lower number = higher priority)
            matching_categories.sort(key=lambda x: x[0])
            
            # Use the highest priority category
            priority, category, config = matching_categories[0]
            
            rule_name = f"port:{category}"
            
            # Apply frequency-based scoring with priority bonus
            base_score = config["weight"]
            if priority == 1:  # Highest priority gets bonus
                base_score += 0.1
            
            adjusted_score = self._apply_frequency_adjustment(rule_name, base_score)
            synergy_bonus = self._calculate_synergy_bonus(context, wordlists)
            score = min(1.0, adjusted_score + synergy_bonus)
        
    
        """
        
        """
        wordlists = []
        matched_rules = []
        score = 0.0
        
        service_lower = context.service.lower() if context.service else ""
        
                rule_name = f"keyword:{keyword}"
                
                # Apply frequency-based scoring
                base_score = 0.5  # Keyword matches get moderate base score
                adjusted_score = self._apply_frequency_adjustment(rule_name, base_score)
                score = max(score, adjusted_score)
        
    
        """
        Get priority for a rule (lower number = higher priority).
        """
    
        """Remove duplicates while preserving order."""
        seen = set()
        result = []
    
        """
        
        """
        issues = {
            "warnings": [],
            "errors": []
        }
        
        # Check for wordlist references
        all_wordlists = set()
        
        # Collect all referenced wordlists
        
        
        
        
        # Check for duplicate wordlist names (potential typos)
        wordlist_counts = {}
            base_name = wl.lower()
            wordlist_counts[base_name] = wordlist_counts.get(base_name, 0) + 1
        
                )
        
        # Check for overlapping port definitions
        port_usage = {}
                    )
                    port_usage[port] = category
        
        # Check weight values
                weight = config["weight"]
                if not 0.0 <= weight <= 1.0:
                    )
        
    
        """
        
            
        """
        frequency = self._get_rule_frequency(rule_name)
        
        # Frequency-based adjustments
            adjustment = 0.1
            adjustment = -0.1
            adjustment = 0.0
        
    
        """
        
            
        """
        
        synergy_patterns = {
            "tomcat": ["manager", "servlet", "jsp"],
            "jenkins": ["jenkins", "build", "ci"],
            "gitlab": ["gitlab", "git", "repository"],
            "phpmyadmin": ["pma", "phpmyadmin", "mysql"],
            "wordpress": ["wp-", "wordpress", "blog"],
            "drupal": ["drupal", "node", "module"],
            "grafana": ["grafana", "dashboard", "metrics"]
        }
        
        tech_lower = context.tech.lower() if context.tech else ""
            synergy_terms = synergy_patterns[tech_lower]
            
            # Check if any wordlists contain synergy terms
                wordlist_lower = wordlist.lower()
        
    
        """
        
            
        """
        
    
        """
        """
        now = datetime.utcnow()
        
            (now - self._last_frequency_update) > timedelta(hours=1)):
            
                # Import here to avoid circular imports
                
                # Get recent selections (last 30 days)
                entries = cache.search_selections(days_back=30, limit=500)
                
                    # Count rule usage
                    rule_counts = Counter()
                    total_selections = len(entries)
                    
                            rule_counts[rule] += 1
                    
                    # Calculate frequencies
                    self._rule_frequency_cache = {
                    }
                    
                
                self._last_frequency_update = now
                
                # Use default frequencies if cache update fails
                    self._rule_frequency_cache = {}


# Global rule engine instance
rule_engine = RuleEngine()


    """
    
    """
    
    frequencies = rule_engine._rule_frequency_cache
    
    sorted_frequencies = sorted(frequencies.items(), key=lambda x: x[1], reverse=True)
    
        "total_rules": len(frequencies),
        "most_frequent": sorted_frequencies[:5],
        "least_frequent": sorted_frequencies[-5:],
        "average_frequency": sum(frequencies.values()) / len(frequencies)
    }