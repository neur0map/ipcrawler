"""Base model classes for IPCrawler

"""



    """Base enum that serializes to string value"""
    
    
    @classmethod
        """Create enum from string value"""
            if item.value == value:


    """Base model for all IPCrawler data models"""
    
    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        arbitrary_types_allowed=True
    )
    
    # Common fields
    id: Optional[str] = Field(None, description="Unique identifier")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
        """Update the updated_at timestamp"""
        self.updated_at = datetime.now()
    
        """Convert model to dictionary with enum handling"""
        return self.model_dump(mode='json')
    
    def to_json(self, indent: Optional[int] = 2) -> str:
        """Convert model to JSON string"""
        return self.model_dump_json(indent=indent)
    
    @classmethod
        """Create model from dictionary"""
    
    @classmethod
        """Create model from JSON string"""
        data = json.loads(json_str)
    
        """Merge another model's data into this one"""
        
        other_data = other.model_dump(exclude={'id', 'created_at'})
        


    """Base model for workflow results"""
    
    workflow_name: str = Field(..., description="Name of the workflow")
    target: str = Field(..., description="Scan target")
    success: bool = Field(True, description="Whether the workflow succeeded")
    execution_time: float = Field(0.0, description="Execution time in seconds")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    data: Dict[str, Any] = Field(default_factory=dict, description="Result data")
    
        """Add data to result"""
        self.data[key] = value
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Get data from result"""


    """Base model for scan targets"""
    
    target: str = Field(..., description="Target identifier (IP, hostname, URL)")
    target_type: str = Field("unknown", description="Type of target")
    resolved_addresses: List[str] = Field(default_factory=list, description="Resolved IP addresses")
    ports: List[int] = Field(default_factory=list, description="Ports to scan")
    tags: List[str] = Field(default_factory=list, description="Target tags")
    
        """Add a resolved address"""
    
        """Add a port to scan"""
    
        """Add a tag"""


    """Base model for collections of items"""
    
    items: List[BaseIPCrawlerModel] = Field(default_factory=list, description="Collection items")
    total_count: int = Field(0, description="Total number of items")
    
        """Add an item to the collection"""
        self.total_count = len(self.items)
    
        """Remove an item by ID"""
        self.items = [item for item in self.items if item.id != item_id]
        self.total_count = len(self.items)
    
        """Get an item by ID"""
            if item.id == item_id:
    
        """Clear all items"""
        self.total_count = 0
    
        """Filter items by attributes"""
        filtered = []
            match = True
                if not hasattr(item, key) or getattr(item, key) != value:
                    match = False


    """Mixin for models that need custom validation"""
    
        """Validate model fields and return list of errors"""
        errors = []
        # Override in subclasses
    
        """Check if model is valid"""
        return len(self.validate_fields()) == 0
    
        """Assert that model is valid, raise if not"""
        errors = self.validate_fields()


    """Mixin for models that need comparison"""
    
    @abstractmethod
        """Get key for comparison"""
    
        return self.get_comparison_key() == other.get_comparison_key()
    
    
