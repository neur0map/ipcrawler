"""
Database module for ipcrawler.
Provides access to port database models and other database components.
"""

from .ports import (
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