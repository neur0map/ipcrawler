FROM python:3.13-slim

# Install core system tools and available security tools
RUN apt-get update && apt-get install -y \
    # Core system tools
    curl wget git gcc python3-dev ruby-full build-essential \
    # Core security tools available in Debian repos
    nmap dnsrecon gobuster nbtscan redis-tools \
    smbclient sslscan \
    # Network and DNS tools
    netcat-traditional dnsutils whois host \
    # Additional tools available in Debian
    hydra john binwalk exiftool \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install tools not available in standard Debian repos
RUN echo "Installing additional security tools..." && \
    # Add Kali repositories for missing tools
    echo "deb http://http.kali.org/kali kali-rolling main non-free contrib" > /etc/apt/sources.list.d/kali.list && \
    curl -fsSL https://archive.kali.org/archive-key.asc | apt-key add - && \
    apt-get update && \
    apt-get install -y --no-install-recommends nikto enum4linux sqlmap 2>/dev/null || \
    echo "Some Kali tools unavailable, continuing..." && \
    rm -f /etc/apt/sources.list.d/kali.list && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Ruby gems and WhatWeb from source since apt version is often broken
RUN gem install bundler && \
    git clone https://github.com/urbanadventurer/WhatWeb.git /tmp/whatweb && \
    cd /tmp/whatweb && \
    bundle install && \
    make install && \
    rm -rf /tmp/whatweb

# Install additional tools via other methods
RUN echo "Installing feroxbuster..." && \
    curl -sL https://github.com/epi052/feroxbuster/releases/latest/download/x86_64-linux-feroxbuster.tar.gz | tar -xz -C /usr/local/bin 2>/dev/null && \
    chmod +x /usr/local/bin/feroxbuster

# Copy the local ipcrawler source code
COPY . /app
WORKDIR /app

# Install Python dependencies and ipcrawler
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install .

WORKDIR /scans

# Create tool management scripts
RUN echo '#!/bin/bash\n\
echo "🔍 Comprehensive security toolkit installed:"\n\
echo ""\n\
echo "✅ Port Scanning: nmap, nbtscan"\n\
echo "✅ Web Discovery: gobuster, feroxbuster, nikto"\n\
echo "✅ Web Analysis: whatweb, sslscan"\n\
echo "✅ SMB/Network: smbclient, enum4linux, redis-tools"\n\
echo "✅ DNS: dnsrecon, dnsutils, host, whois"\n\
echo "✅ Exploitation: hydra, john, sqlmap"\n\
echo "✅ Forensics: binwalk, exiftool"\n\
echo "✅ Network: netcat"\n\
echo ""\n\
echo "🎯 Ready for comprehensive reconnaissance!"\n\
echo "📝 Run: ipcrawler --help to get started"\n\
' > /show-tools.sh && chmod +x /show-tools.sh

# Script to install additional tools (that may not be in Debian repos)
RUN echo '#!/bin/bash\n\
echo "🔧 Installing additional security tools..."\n\
echo "Note: Some tools may not be available in standard Debian repos"\n\
apt-get update\n\
# Try to install additional tools, continue on failure\n\
apt-get install -y nikto enum4linux smbmap snmp sipvicious || echo "Some tools unavailable in Debian repos"\n\
# Install tools via other methods\n\
echo "📥 Installing feroxbuster via GitHub releases..."\n\
curl -sL https://github.com/epi052/feroxbuster/releases/latest/download/x86_64-linux-feroxbuster.tar.gz | tar -xz -C /usr/local/bin 2>/dev/null || echo "feroxbuster install failed"\n\
echo "📥 Installing additional Python tools..."\n\
pip install impacket 2>/dev/null || echo "impacket install failed"\n\
echo ""\n\
echo "✅ Additional tool installation complete!"\n\
echo "Run /show-tools.sh to see what is available"\n\
' > /install-extra-tools.sh && chmod +x /install-extra-tools.sh

CMD ["/bin/bash"]
