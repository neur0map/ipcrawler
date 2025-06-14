FROM python:3-slim

# Install core system packages first
RUN apt-get update && apt-get install -y \
    curl wget git gcc python3-dev build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install basic security tools available in Debian
RUN apt-get update && apt-get install -y \
    nmap dnsutils netcat-traditional \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install additional tools one by one to avoid conflicts
RUN apt-get update && apt-get install -y smbclient \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y sslscan \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y hydra \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python-based tools
RUN pip install --no-cache-dir impacket

# Copy the local ipcrawler source code
COPY . /app
WORKDIR /app

# Install Python dependencies and ipcrawler
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install .

WORKDIR /scans

# Create a simple tool verification script
RUN echo '#!/bin/bash\n\
echo "🔍 Basic security toolkit installed:"\n\
echo ""\n\
echo "✅ Port Scanning: nmap"\n\
echo "✅ Network: netcat, curl, wget"\n\
echo "✅ DNS: dnsutils (dig, nslookup)"\n\
echo "✅ SMB: smbclient"\n\
echo "✅ SSL: sslscan"\n\
echo "✅ Brute Force: hydra"\n\
echo "✅ Windows Tools: impacket suite"\n\
echo "✅ Python: ipcrawler"\n\
echo ""\n\
echo "🎯 Basic reconnaissance toolkit ready!"\n\
echo "📝 Run: ipcrawler --help to get started"\n\
' > /show-tools.sh && chmod +x /show-tools.sh

CMD ["/bin/bash"]
