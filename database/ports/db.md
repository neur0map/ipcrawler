# Port Database Status and Instructions

## **MISSION: Document Top 100 CTF, Hack the Box & OSCP Ports**

**Current Status:** 43 ports documented | **Target:** 100 ports | **Progress:** 43%  
**Last completed port:** 9200 (Elasticsearch - Search and Analytics Engine)  
**Date last updated:** 2025-07-16

---

## Strategic Priority List for CTF/HTB/OSCP Environments

### **✅ Tier 1: Database & Remote Access (Ports 24-33)** - COMPLETED
**Critical Infrastructure Services - 10 Ports**

| Port | Service | Priority Level | CTF/HTB Frequency |
|------|---------|----------------|-------------------|
| **1433** | Microsoft SQL Server | CRITICAL | Very Common |
| **3306** | MySQL | CRITICAL | Very Common |
| **3389** | RDP | CRITICAL | Extremely Common |
| **5432** | PostgreSQL | HIGH | Common |
| **5985** | WinRM HTTP | CRITICAL | Very Common |
| **5986** | WinRM HTTPS | CRITICAL | Very Common |
| **6379** | Redis | HIGH | Common |
| **27017** | MongoDB | HIGH | Common |
| **1521** | Oracle Database | MEDIUM | Occasional |
| **5900** | VNC | HIGH | Common |

### **✅ Tier 2: Secure Communications & Web Services (Ports 34-43)** - COMPLETED
**Enhanced Security Protocols - 10 Ports**

| Port | Service | Priority Level | CTF/HTB Frequency |
|------|---------|----------------|-------------------|
| **993** | IMAPS | HIGH | Very Common |
| **995** | POP3S | HIGH | Common |
| **8761** | Eureka Server (Spring Cloud) | HIGH | Very Common |
| **3000** | Gitea/Node.js/Dev Servers | HIGH | Very Common |
| **8080** | HTTP Proxy/Jenkins/Tomcat | HIGH | Very Common |
| **8000** | HTTP Alternative/Git Web | HIGH | Very Common |
| **5000** | Flask/Python Default | HIGH | Very Common |
| **8443** | HTTPS Alternative | HIGH | Very Common |
| **10000** | Webmin | HIGH | Common |
| **9200** | Elasticsearch | HIGH | Common |

### **Tier 3: Development & CI/CD Services (Ports 44-53)**
**Git, Jenkins & Development Tools - 10 Ports**

| Port | Service | Priority Level | CTF/HTB Frequency |
|------|---------|----------------|-------------------|
| **9418** | Git Protocol | MEDIUM | Common |
| **3001** | Gitea/Alt Dev Server | MEDIUM | Common |
| **8090** | Jenkins/Confluence | MEDIUM | Common |
| **8081** | HTTP Alternative | MEDIUM | Common |
| **8888** | HTTP Alternative/Jupyter | HIGH | Common |
| **9000** | SonarQube/Various | MEDIUM | Common |
| **5601** | Kibana | MEDIUM | Common |
| **8181** | GlassFish | MEDIUM | Occasional |
| **4444** | Metasploit | MEDIUM | Common |
| **7001** | Cassandra | MEDIUM | Occasional |

### **Tier 4: Network Infrastructure (Ports 54-63)**
**File Systems & Network Services - 10 Ports**

| Port | Service | Priority Level | CTF/HTB Frequency |
|------|---------|----------------|-------------------|
| **2049** | NFS | HIGH | Common |
| **873** | rsync | MEDIUM | Common |
| **1080** | SOCKS Proxy | MEDIUM | Common |
| **3128** | Squid Proxy | MEDIUM | Common |
| **1194** | OpenVPN | MEDIUM | Occasional |
| **1434** | MSSQL Monitor | MEDIUM | Common |
| **11211** | Memcached | MEDIUM | Common |
| **623** | IPMI | MEDIUM | Occasional |
| **1900** | UPnP | MEDIUM | Common |
| **5353** | mDNS | MEDIUM | Common |

### **Tier 5: Legacy & Specialized Protocols (Ports 64-73)**
**Unix/Legacy Services & VoIP - 10 Ports**

| Port | Service | Priority Level | CTF/HTB Frequency |
|------|---------|----------------|-------------------|
| **69** | TFTP | MEDIUM | Common |
| **79** | Finger | LOW | Rare |
| **123** | NTP | MEDIUM | Common |
| **631** | CUPS/IPP | MEDIUM | Common |
| **464** | Kpasswd | MEDIUM | Occasional |
| **500** | IKE/IPSec | MEDIUM | Occasional |
| **5060** | SIP | MEDIUM | Occasional |
| **5061** | SIP TLS | MEDIUM | Occasional |
| **1701** | L2TP | MEDIUM | Occasional |
| **4500** | IPSec NAT-T | MEDIUM | Occasional |

### **Tier 6: Communication & Chat Services (Ports 74-83)**
**IRC, Messaging & Communication - 10 Ports**

| Port | Service | Priority Level | CTF/HTB Frequency |
|------|---------|----------------|-------------------|
| **6667** | IRC | MEDIUM | Occasional |
| **6697** | IRC SSL | MEDIUM | Occasional |
| **6660** | IRC Alt 1 | MEDIUM | Occasional |
| **6661** | IRC Alt 2 | MEDIUM | Occasional |
| **6662** | IRC Alt 3 | MEDIUM | Occasional |
| **6663** | IRC Alt 4 | MEDIUM | Occasional |
| **6664** | IRC Alt 5 | MEDIUM | Occasional |
| **6665** | IRC Alt 6 | MEDIUM | Occasional |
| **6668** | IRC Alt 8 | MEDIUM | Occasional |
| **6669** | IRC Alt 9 | MEDIUM | Occasional |

### **Tier 7: Enterprise & Virtualization (Ports 84-93)**
**VMware, Enterprise Apps & Storage - 10 Ports**

| Port | Service | Priority Level | CTF/HTB Frequency |
|------|---------|----------------|-------------------|
| **902** | VMware | MEDIUM | Occasional |
| **903** | VMware | MEDIUM | Occasional |
| **3260** | iSCSI | MEDIUM | Occasional |
| **3268** | Global Catalog LDAP | MEDIUM | Occasional |
| **7000** | Cassandra | MEDIUM | Occasional |
| **7002** | Cassandra | MEDIUM | Occasional |
| **9043** | WebSphere | MEDIUM | Occasional |
| **9080** | WebSphere | MEDIUM | Occasional |
| **9443** | WebSphere SSL | MEDIUM | Occasional |
| **9090** | Openfire Admin | MEDIUM | Occasional |

### **Tier 8: Backdoors & Uncommon Services (Ports 94-100)**
**Final 7 Ports - Backdoors & Rare Services**

| Port | Service | Priority Level | CTF/HTB Frequency |
|------|---------|----------------|-------------------|
| **1337** | WASTE | LOW | Rare |
| **31337** | Back Orifice | LOW | Rare |
| **12345** | NetBus | LOW | Rare |
| **1234** | VLC/Insight Manager | MEDIUM | Occasional |
| **4445** | I2P | LOW | Rare |
| **9001** | ETL Service/Tor | MEDIUM | Occasional |
| **5050** | Yahoo Messenger | LOW | Rare |

---

## Current Port List Status

### **✅ Completed Ports (43/100) - 43%**
- **File Transfer:** 21 (FTP), 22 (SSH), 23 (Telnet)
- **Mail Services:** 25 (SMTP), 110 (POP3), 143 (IMAP)
- **Network Core:** 53 (DNS), 80 (HTTP), 443 (HTTPS)
- **Windows Services:** 88 (Kerberos), 135 (MS-RPC), 139 (NetBIOS-SSN), 445 (SMB)
- **Directory Services:** 161 (SNMP), 389 (LDAP)
- **Legacy/Unix:** 111 (RPCbind), 512 (rexec), 513 (rlogin), 514 (rsh/syslog), 515 (LPD), 548 (AFP)
- **Database Services:** 1433 (MSSQL), 3306 (MySQL), 5432 (PostgreSQL), 6379 (Redis), 27017 (MongoDB), 1521 (Oracle)
- **Remote Access:** 3389 (RDP), 5985 (WinRM HTTP), 5986 (WinRM HTTPS), 5900 (VNC)
- **Secure Mail:** 993 (IMAPS), 995 (POP3S)
- **Web Services:** 3000 (Gitea/Node.js), 5000 (Flask), 8000 (HTTP Alt), 8080 (HTTP Proxy), 8443 (HTTPS Alt), 10000 (Webmin)
- **Enterprise/Analytics:** 8761 (Eureka Server), 9200 (Elasticsearch)

### **🎯 Immediate Next Targets (Tier 3 - Ports 44-53)**
**Development & CI/CD Services - Git, Jenkins & Development Tools**
1. **9418 (Git Protocol)** - Git version control system
2. **3001 (Gitea/Alt Dev Server)** - Alternative Git services
3. **8090 (Jenkins/Confluence)** - CI/CD and collaboration tools
4. **8081 (HTTP Alternative)** - Alternative web services
5. **8888 (HTTP Alternative/Jupyter)** - Jupyter notebooks and dev servers
6. **9000 (SonarQube/Various)** - Code quality and analysis tools
7. **5601 (Kibana)** - Elasticsearch visualization
8. **8181 (GlassFish)** - Java application server
9. **4444 (Metasploit)** - Penetration testing framework
10. **7001 (Cassandra)** - NoSQL database cluster

---

## Port Metadata Building Instructions

### **CTF/HTB/OSCP-Focused Requirements**

Each port entry must emphasize **practical penetration testing scenarios**:

```json
{
  "PORT_NUMBER": {
    "name": "Service Name - Full Description",
    "protocol": "tcp|udp|tcp/udp",
    "default_service": "service_name",
    "alternative_services": ["common_alternatives"],
    "description": "**CTF/HTB/OSCP context** - Common vulnerabilities and attack vectors",
    "tech_stack": {
      "language": "Implementation language",
      "framework": "Common implementations",
      "http_stack": "Web stack if applicable"
    },
    "indicators": {
      "ports": [PORT_NUMBER],
      "headers": ["detection_headers"],
      "paths": ["common_endpoints"],
      "banners": ["service_banners"]
    },
    "classification": {
      "category": "attack_category",
      "exposure": "external|internal|both",
      "auth_required": true|false,
      "misuse_potential": "critical|high|medium|low"
    },
    "attack_vectors": {
      "primary": ["main_attack_methods"],
      "secondary": ["additional_vectors"],
      "tools": ["recommended_tools"]
    },
    "ctf_scenarios": {
      "beginner": "Common easy box scenarios",
      "intermediate": "Medium difficulty exploitation",
      "advanced": "Advanced attack chains"
    },
    "associated_wordlists": {
      "high": ["pentesting_specific.txt"],
      "medium": ["common_service.txt"],
      "fallback": ["generic_list.txt"]
    },
    "exploitation_paths": {
      "/endpoint": {
        "confidence": 0.0-1.0,
        "risk": "critical|high|medium|low",
        "technique": "Exploitation method",
        "tools": ["tool1", "tool2"]
      }
    },
    "common_vulnerabilities": [
      "CVE-XXXX-XXXX: Description",
      "Known misconfigurations",
      "Default credentials"
    ],
    "scoring_modifiers": {
      "default_creds": 1.0,
      "version_disclosure": 0.9,
      "config_file_exposure": 0.8
    },
    "last_updated": "YYYY-MM-DD"
  }
}
```

### **CTF/HTB/OSCP-Specific Field Definitions**

#### **Attack-Focused Documentation**
- **attack_vectors**: Primary and secondary attack methods
- **ctf_scenarios**: Difficulty-based exploitation scenarios
- **exploitation_paths**: Specific endpoints and techniques
- **common_vulnerabilities**: Known CVEs and misconfigurations

#### **Penetration Testing Context**
- **description**: Must include common attack scenarios from HTB/CTF
- **misuse_potential**: Rate based on actual exploitation frequency
- **tools**: Pentesting-specific tools for each service

#### **Real-World Application Categories**
- `web-application`, `database`, `remote-access`, `file-transfer`
- `windows-infrastructure`, `linux-service`, `network-appliance`
- `iot-device`, `scada-industrial`, `cloud-service`

### **Research Sources for CTF/HTB/OSCP Context**

1. **HackTheBox writeups** and machine analysis
2. **OSCP lab documentation** and known vulnerabilities  
3. **CTF challenge databases** (PicoCTF, OverTheWire, etc.)
4. **Metasploit modules** for each service
5. **ExploitDB** for known exploits
6. **NIST vulnerability database** for CVE information
7. **SecLists** for service-specific wordlists

### **Quality Standards for CTF/HTB/OSCP**

- **Exploitation Focus**: Every entry must include real attack scenarios
- **Tool Integration**: Compatible with common pentesting tools
- **Difficulty Scaling**: Scenarios from beginner to advanced
- **Current Relevance**: Emphasize services actually seen in modern CTF/HTB
- **Practical Application**: Focus on techniques used in OSCP labs

### **Strategic Completion Roadmap (8 Tiers × 10 Ports)**

**Tier 1 (Week 1): Database & Remote Access**
- Complete ports 24-33: Critical infrastructure services
- Focus: Database injection, remote access, credential attacks

**Tier 2 (Week 2): Secure Communications & Web Services**  
- Complete ports 34-43: Enhanced security protocols
- Focus: Encrypted services, modern web applications

**Tier 3 (Week 3): Development & CI/CD Services**
- Complete ports 44-53: Git, Jenkins, development tools
- Focus: Source code access, CI/CD vulnerabilities

**Tier 4 (Week 4): Network Infrastructure**
- Complete ports 54-63: File systems, network services
- Focus: Network-based attacks, file sharing

**Tier 5 (Week 5): Legacy & Specialized Protocols**
- Complete ports 64-73: Unix/legacy services, VoIP
- Focus: Legacy vulnerabilities, specialized protocols

**Tier 6 (Week 6): Communication & Chat Services**
- Complete ports 74-83: IRC, messaging systems
- Focus: Communication protocol exploitation

**Tier 7 (Week 7): Enterprise & Virtualization**
- Complete ports 84-93: VMware, enterprise applications
- Focus: Enterprise environments, virtualization

**Tier 8 (Week 8): Backdoors & Uncommon Services**
- Complete ports 94-100: Final 7 ports
- Focus: Backdoor detection, rare service exploitation

### **Success Metrics**
- **Coverage**: 100 most common CTF/HTB/OSCP ports documented
- **Quality**: Each port includes real-world attack scenarios
- **Usability**: Compatible with existing ipcrawler workflows
- **Relevance**: Focused on current pentesting methodologies
