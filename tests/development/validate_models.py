#!/usr/bin/env python3
"""
Validation script for port database Pydantic models.
Tests compatibility with existing port_db.json data.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import (
    PortDatabase, PortEntry, ServiceCategory, RiskLevel, 
    ExposureType, load_port_database
)


def load_existing_database() -> Dict[str, Any]:
    """Load the existing port_db.json file."""
    db_path = Path(__file__).parent.parent / "database" / "ports" / "port_db.json"
    
    if not db_path.exists():
        raise FileNotFoundError(f"Database file not found: {db_path}")
    
    with open(db_path, 'r') as f:
        return json.load(f)


def validate_database_structure():
    """Validate the existing database against Pydantic models."""
    print("🔍 Loading existing port database...")
    
    try:
        json_data = load_existing_database()
        print(f"✅ Successfully loaded JSON with {len(json_data)} ports")
        
        print("\n🔍 Validating against Pydantic models...")
        port_db = load_port_database(json_data)
        print(f"✅ Successfully validated all {len(port_db.ports)} port entries")
        
        return port_db
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        raise


def analyze_database_completeness(port_db: PortDatabase):
    """Analyze the current database completeness."""
    print("\n📊 Database Analysis:")
    
    stats = port_db.get_completion_stats()
    print(f"📈 Progress: {stats['total_ports']}/100 ports ({stats['completion_percentage']}%)")
    
    print(f"\n📂 Categories:")
    for category, count in stats['categories'].items():
        print(f"   • {category}: {count} ports")
    
    print(f"\n⚠️  Risk Levels:")
    for risk, count in stats['risk_levels'].items():
        print(f"   • {risk}: {count} ports")


def test_database_methods(port_db: PortDatabase):
    """Test various database query methods."""
    print("\n🧪 Testing Database Methods:")
    
    # Test category queries
    db_ports = port_db.get_database_ports()
    web_ports = port_db.get_web_ports()
    remote_ports = port_db.get_remote_access_ports()
    critical_ports = port_db.get_critical_ports()
    external_ports = port_db.get_external_ports()
    
    print(f"   • Database ports: {len(db_ports)}")
    print(f"   • Web application ports: {len(web_ports)}")
    print(f"   • Remote access ports: {len(remote_ports)}")
    print(f"   • Critical risk ports: {len(critical_ports)}")
    print(f"   • External ports: {len(external_ports)}")
    
    # Test specific port retrieval
    ssh_port = port_db.get_port(22)
    if ssh_port:
        print(f"   • Port 22 (SSH): {ssh_port.name}")
    
    https_port = port_db.get_port("443")
    if https_port:
        print(f"   • Port 443 (HTTPS): {https_port.name}")


def demonstrate_ctf_enhancements():
    """Demonstrate the CTF/HTB/OSCP enhancements."""
    print("\n🎯 CTF/HTB/OSCP Enhancement Demonstration:")
    
    # Create a sample enhanced port entry
    from database import (
        PortEntry, ServiceIndicators, ServiceClassification,
        AttackVectors, CTFScenarios, ExploitationPath,
        ProtocolType, ServiceCategory, ExposureType, RiskLevel
    )
    
    enhanced_port = PortEntry(
        name="MySQL - Database Server",
        protocol=ProtocolType.TCP,
        default_service="mysql",
        alternative_services=["mariadb", "percona"],
        description="MySQL database server commonly found in CTF web challenges with SQL injection vulnerabilities",
        indicators=ServiceIndicators(
            ports=[3306],
            banners=["mysql", "MySQL", "MariaDB"],
            headers=[]
        ),
        classification=ServiceClassification(
            category=ServiceCategory.DATABASE,
            exposure=ExposureType.INTERNAL,
            auth_required=True,
            misuse_potential=RiskLevel.CRITICAL
        ),
        attack_vectors=AttackVectors(
            primary=["SQL Injection", "Credential Brute Force", "Privilege Escalation"],
            secondary=["UDF Exploitation", "File Read/Write", "Configuration Disclosure"],
            tools=["sqlmap", "hydra", "mysql", "nmap", "metasploit"]
        ),
        ctf_scenarios=CTFScenarios(
            beginner="Default credentials (root/password, root/root) for database access",
            intermediate="SQL injection through web application leading to database compromise",
            advanced="UDF injection for code execution and lateral movement to system level"
        ),
        exploitation_paths={
            "/login": ExploitationPath(
                confidence=0.8,
                risk=RiskLevel.HIGH,
                technique="SQL injection in login form",
                tools=["sqlmap", "burp"]
            ),
            "/admin": ExploitationPath(
                confidence=0.9,
                risk=RiskLevel.CRITICAL,
                technique="Admin panel with SQL injection",
                tools=["sqlmap", "manual"]
            )
        },
        common_vulnerabilities=[
            "CVE-2012-2122: Authentication bypass",
            "Default credentials: root/password, root/root, root/''",
            "Privilege escalation via UDF",
            "File system access via LOAD_FILE/INTO OUTFILE"
        ],
        scoring_modifiers={
            "default_credentials": 1.0,
            "version_disclosure": 0.9,
            "file_privileges": 0.95
        },
        last_updated="2025-01-16"
    )
    
    print(f"   ✅ Created enhanced MySQL port entry")
    print(f"   🔧 Attack vectors: {len(enhanced_port.attack_vectors.primary)} primary")
    print(f"   🎯 CTF scenarios: {'✅' if enhanced_port.ctf_scenarios.beginner else '❌'} beginner")
    print(f"   🛡️  Vulnerabilities: {len(enhanced_port.common_vulnerabilities)} documented")
    print(f"   🔍 Exploitation paths: {len(enhanced_port.exploitation_paths)} paths")


def main():
    """Main validation function."""
    print("🚀 Port Database Pydantic Model Validation")
    print("=" * 50)
    
    try:
        # Validate existing database
        port_db = validate_database_structure()
        
        # Analyze completeness
        analyze_database_completeness(port_db)
        
        # Test methods
        test_database_methods(port_db)
        
        # Demonstrate enhancements
        demonstrate_ctf_enhancements()
        
        print(f"\n✅ All validations passed! The Pydantic models are working correctly.")
        print(f"🎯 Ready to continue documenting CTF/HTB/OSCP ports (23/100 complete)")
        
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 