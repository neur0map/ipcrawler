FROM python:3-slim

# Install core system packages first
RUN apt-get update && apt-get install -y \
    curl wget git gcc python3-dev build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install basic security tools available in Debian
RUN apt-get update && apt-get install -y \
    nmap dnsutils netcat-traditional \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install core enumeration tools
RUN apt-get update && apt-get install -y \
    smbclient sslscan hydra nikto whatweb \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install enumeration tools with error handling
RUN apt-get update && \
    # Install tools that should always work
    apt-get install -y seclists dnsrecon enum4linux nbtscan onesixtyone redis-tools smbmap snmp sipvicious 2>/dev/null || true && \
    # Try to install additional tools
    apt-get install -y feroxbuster gobuster impacket-scripts oscanner tnscmd10g 2>/dev/null || true && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python-based tools as fallbacks
RUN pip install --no-cache-dir impacket dirsearch

# Install Go-based tools if the apt versions failed
RUN apt-get update && apt-get install -y golang-go 2>/dev/null || true && \
    if command -v go >/dev/null 2>&1; then \
        go install github.com/OJ/gobuster/v3@latest 2>/dev/null || true; \
        go install github.com/epi052/feroxbuster@latest 2>/dev/null || true; \
    fi && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Try to install Oracle tools with multiple methods
RUN apt-get update && \
    # Try tnscmd10g first
    apt-get install -y tnscmd10g 2>/dev/null || \
    # Try Oracle Instant Client as fallback
    apt-get install -y oracle-instantclient-basic oracle-instantclient-devel 2>/dev/null || \
    # If both fail, just continue
    echo "Oracle tools not available in this environment" && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy the local ipcrawler source code
COPY . /app
WORKDIR /app

# Install Python dependencies and ipcrawler
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install .

WORKDIR /scans

# Create enhanced tool verification script
RUN echo '#!/bin/bash\n\
echo "🔍 Security toolkit verification:"\n\
echo ""\n\
\n\
check_tool() {\n\
    if command -v "$1" >/dev/null 2>&1; then\n\
        echo "✅ $2: $1"\n\
    else\n\
        echo "❌ $2: $1 (not available)"\n\
    fi\n\
}\n\
\n\
echo "📡 Network & Port Scanning:"\n\
check_tool "nmap" "Port Scanner"\n\
check_tool "netcat" "Network Tool"\n\
check_tool "dig" "DNS Lookup"\n\
echo ""\n\
\n\
echo "🌐 Web Enumeration:"\n\
check_tool "nikto" "Web Scanner"\n\
check_tool "whatweb" "Web Identifier"\n\
check_tool "feroxbuster" "Directory Buster"\n\
check_tool "gobuster" "Directory/DNS Buster"\n\
check_tool "dirsearch" "Directory Search"\n\
echo ""\n\
\n\
echo "🔐 Service Enumeration:"\n\
check_tool "smbclient" "SMB Client"\n\
check_tool "smbmap" "SMB Mapper"\n\
check_tool "enum4linux" "Linux/SMB Enum"\n\
check_tool "nbtscan" "NetBIOS Scanner"\n\
check_tool "onesixtyone" "SNMP Scanner"\n\
check_tool "snmpwalk" "SNMP Walker"\n\
check_tool "redis-cli" "Redis Client"\n\
echo ""\n\
\n\
echo "🗄️ Database Tools:"\n\
check_tool "tnscmd10g" "Oracle TNS"\n\
check_tool "oscanner" "Oracle Scanner"\n\
echo ""\n\
\n\
echo "🔓 Authentication:"\n\
check_tool "hydra" "Brute Forcer"\n\
check_tool "sslscan" "SSL Scanner"\n\
echo ""\n\
\n\
echo "🪟 Windows Tools:"\n\
check_tool "impacket-smbclient" "Impacket SMB"\n\
check_tool "impacket-secretsdump" "Impacket Secrets"\n\
echo ""\n\
\n\
echo "📝 Wordlists:"\n\
if [ -d "/usr/share/seclists" ]; then\n\
    echo "✅ SecLists: /usr/share/seclists"\n\
else\n\
    echo "❌ SecLists: not available"\n\
fi\n\
echo ""\n\
\n\
echo "🎯 ipcrawler:"\n\
check_tool "ipcrawler" "Main Tool"\n\
echo ""\n\
\n\
echo "💡 Usage:"\n\
echo "  ipcrawler --help                    # Show help"\n\
echo "  ipcrawler --list                    # List available plugins"\n\
echo "  ipcrawler --ignore-plugin-checks IP # Skip tool checks"\n\
echo "  ipcrawler -vvv IP                   # Verbose scanning"\n\
' > /show-tools.sh && chmod +x /show-tools.sh

# Create script to install additional tools if needed
RUN echo '#!/bin/bash\n\
echo "🔧 Installing additional security tools..."\n\
echo ""\n\
\n\
# Update package cache\n\
apt-get update\n\
\n\
# Install any missing tools\n\
echo "📦 Trying to install missing enumeration tools..."\n\
apt-get install -y \\\n\
    masscan dirb wfuzz sqlmap john hashcat \\\n\
    metasploit-framework exploitdb searchsploit \\\n\
    2>/dev/null || echo "Some tools may not be available"\n\
\n\
# Install additional Python tools\n\
echo "🐍 Installing additional Python tools..."\n\
pip install --no-cache-dir \\\n\
    sqlmap wfuzz requests beautifulsoup4 \\\n\
    2>/dev/null || echo "Some Python tools may have failed"\n\
\n\
# Clean up\n\
apt-get clean && rm -rf /var/lib/apt/lists/*\n\
\n\
echo ""\n\
echo "✅ Additional tools installation complete"\n\
echo "📝 Run /show-tools.sh to verify installation"\n\
' > /install-extra-tools.sh && chmod +x /install-extra-tools.sh

CMD ["/bin/bash"]
