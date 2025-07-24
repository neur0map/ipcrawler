"""Base model classes for IPCrawler

Provides base classes for all data models.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Type
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
import json
from enum import Enum


class SerializableEnum(str, Enum):
    """Base enum that serializes to string value"""
    
    def __str__(self):
        return self.value
    
    @classmethod
    def from_string(cls, value: str):
        """Create enum from string value"""
        for item in cls:
            if item.value == value:
                return item
        raise ValueError(f"No {cls.__name__} with value: {value}")


class BaseIPCrawlerModel(BaseModel):
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
    
    def update_timestamp(self):
        """Update the updated_at timestamp"""
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary with enum handling"""
        return self.model_dump(mode='json')
    
    def to_json(self, indent: Optional[int] = 2) -> str:
        """Convert model to JSON string"""
        return self.model_dump_json(indent=indent)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create model from dictionary"""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str):
        """Create model from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def merge(self, other: 'BaseIPCrawlerModel'):
        """Merge another model's data into this one"""
        if not isinstance(other, self.__class__):
            raise TypeError(f"Cannot merge {type(other)} into {type(self)}")
        
        other_data = other.model_dump(exclude={'id', 'created_at'})
        for key, value in other_data.items():
            if value is not None:
                setattr(self, key, value)
        
        self.update_timestamp()


class WorkflowResult(BaseIPCrawlerModel):
    """Base model for workflow results"""
    
    workflow_name: str = Field(..., description="Name of the workflow")
    target: str = Field(..., description="Scan target")
    success: bool = Field(True, description="Whether the workflow succeeded")
    execution_time: float = Field(0.0, description="Execution time in seconds")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    data: Dict[str, Any] = Field(default_factory=dict, description="Result data")
    
    def add_data(self, key: str, value: Any):
        """Add data to result"""
        self.data[key] = value
        self.update_timestamp()
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Get data from result"""
        return self.data.get(key, default)


class ScanTarget(BaseIPCrawlerModel):
    """Base model for scan targets"""
    
    target: str = Field(..., description="Target identifier (IP, hostname, URL)")
    target_type: str = Field("unknown", description="Type of target")
    resolved_addresses: List[str] = Field(default_factory=list, description="Resolved IP addresses")
    ports: List[int] = Field(default_factory=list, description="Ports to scan")
    tags: List[str] = Field(default_factory=list, description="Target tags")
    
    def add_resolved_address(self, address: str):
        """Add a resolved address"""
        if address not in self.resolved_addresses:
            self.resolved_addresses.append(address)
            self.update_timestamp()
    
    def add_port(self, port: int):
        """Add a port to scan"""
        if port not in self.ports:
            self.ports.append(port)
            self.ports.sort()
            self.update_timestamp()
    
    def add_tag(self, tag: str):
        """Add a tag"""
        if tag not in self.tags:
            self.tags.append(tag)
            self.update_timestamp()


class BaseCollection(BaseIPCrawlerModel):
    """Base model for collections of items"""
    
    items: List[BaseIPCrawlerModel] = Field(default_factory=list, description="Collection items")
    total_count: int = Field(0, description="Total number of items")
    
    def add_item(self, item: BaseIPCrawlerModel):
        """Add an item to the collection"""
        self.items.append(item)
        self.total_count = len(self.items)
        self.update_timestamp()
    
    def remove_item(self, item_id: str):
        """Remove an item by ID"""
        self.items = [item for item in self.items if item.id != item_id]
        self.total_count = len(self.items)
        self.update_timestamp()
    
    def get_item(self, item_id: str) -> Optional[BaseIPCrawlerModel]:
        """Get an item by ID"""
        for item in self.items:
            if item.id == item_id:
                return item
        return None
    
    def clear(self):
        """Clear all items"""
        self.items.clear()
        self.total_count = 0
        self.update_timestamp()
    
    def filter_by(self, **kwargs) -> List[BaseIPCrawlerModel]:
        """Filter items by attributes"""
        filtered = []
        for item in self.items:
            match = True
            for key, value in kwargs.items():
                if not hasattr(item, key) or getattr(item, key) != value:
                    match = False
                    break
            if match:
                filtered.append(item)
        return filtered


class ValidationMixin:
    """Mixin for models that need custom validation"""
    
    def validate_fields(self) -> List[str]:
        """Validate model fields and return list of errors"""
        errors = []
        # Override in subclasses
        return errors
    
    def is_valid(self) -> bool:
        """Check if model is valid"""
        return len(self.validate_fields()) == 0
    
    def assert_valid(self):
        """Assert that model is valid, raise if not"""
        errors = self.validate_fields()
        if errors:
            raise ValueError(f"Validation failed: {', '.join(errors)}")


class ComparableMixin:
    """Mixin for models that need comparison"""
    
    @abstractmethod
    def get_comparison_key(self) -> Any:
        """Get key for comparison"""
        pass
    
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.get_comparison_key() == other.get_comparison_key()
    
    def __lt__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.get_comparison_key() < other.get_comparison_key()
    
    def __hash__(self):
        return hash(self.get_comparison_key())