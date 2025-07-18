"""
Port database models and data for ipcrawler.
Provides Pydantic models and utilities for CTF/HTB/OSCP port documentation.
"""

from .models import (
    # Main models
    PortEntry,
    PortDatabase,
    
    # Enums
    ProtocolType,
    ExposureType, 
    RiskLevel,
    ServiceCategory,
    
    # Component models
    TechStack,
    ServiceIndicators,
    ServiceClassification,
    AttackVectors,
    CTFScenarios,
    ExploitationPath,
    
    # Utility functions
    load_port_database,
    create_empty_port_entry
)

__version__ = "1.0.0"
__author__ = "ipcrawler"

# Package metadata
__all__ = [
    # Main models
    'PortEntry',
    'PortDatabase',
    
    # Enums
    'ProtocolType',
    'ExposureType', 
    'RiskLevel',
    'ServiceCategory',
    
    # Component models
    'TechStack',
    'ServiceIndicators',
    'ServiceClassification',
    'AttackVectors',
    'CTFScenarios',
    'ExploitationPath',
    
    # Utility functions
    'load_port_database',
    'create_empty_port_entry'
] 