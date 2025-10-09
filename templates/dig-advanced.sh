#!/bin/bash
# Comprehensive DNS Reconnaissance Script
# Usage: dig-advanced.sh <target>

TARGET="$1"

echo "=== DNS Reconnaissance for $TARGET ==="
echo ""

# Basic record enumeration
echo "[*] Standard DNS Records"
dig "$TARGET" A "$TARGET" AAAA "$TARGET" MX "$TARGET" TXT "$TARGET" NS "$TARGET" SOA "$TARGET" CNAME +noall +answer +comments
echo ""

# Reverse DNS
echo "[*] Reverse DNS Lookup"
dig -x "$TARGET" +short
echo ""

# Extended record types (DNSSEC, CAA, etc.)
echo "[*] Extended Record Types"
dig "$TARGET" CAA "$TARGET" DNSKEY "$TARGET" DS "$TARGET" NSEC "$TARGET" NSEC3 "$TARGET" RRSIG "$TARGET" TLSA +noall +answer
echo ""

# Email security records (SPF, DMARC, DKIM)
echo "[*] Email Security Records"
dig "$TARGET" TXT +short | grep -i "v=spf1\|v=DMARC1" || echo "No SPF/DMARC found"
dig "_dmarc.$TARGET" TXT +short
dig "default._domainkey.$TARGET" TXT +short
dig "mail._domainkey.$TARGET" TXT +short
echo ""

# Service discovery (SRV records)
echo "[*] Service Discovery (SRV Records)"
for service in _ldap._tcp _kerberos._tcp _kerberos._udp _kpasswd._tcp _autodiscover._tcp _caldav._tcp _carddav._tcp _xmpp-client._tcp _xmpp-server._tcp _sip._tcp _sip._udp _sipfederationtls._tcp _jabber._tcp; do
  result=$(dig "${service}.$TARGET" SRV +short 2>/dev/null)
  if [ ! -z "$result" ]; then
    echo "Found: ${service}.$TARGET"
    echo "$result"
  fi
done
echo ""

# Common subdomain enumeration
echo "[*] Common Subdomain Enumeration"
for sub in www mail ftp smtp pop imap webmail admin portal vpn remote gateway api dev staging test prod internal intranet ns1 ns2 dns mx1 mx2 cdn blog shop store support help docs wiki git svn; do
  result=$(dig "${sub}.$TARGET" A +short 2>/dev/null | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$')
  if [ ! -z "$result" ]; then
    echo "${sub}.$TARGET -> $result"
  fi
done
echo ""

# Wildcard detection
echo "[*] Wildcard Detection"
random_sub=$(cat /dev/urandom | tr -dc 'a-z0-9' | fold -w 32 | head -n 1)
wildcard_result=$(dig "${random_sub}.$TARGET" A +short 2>/dev/null | head -1)
if [ ! -z "$wildcard_result" ]; then
  echo "WARNING: Wildcard DNS detected! *.$TARGET -> $wildcard_result"
else
  echo "No wildcard DNS configuration detected"
fi
echo ""

# Zone transfer attempts (AXFR)
echo "[*] Zone Transfer Attempts (AXFR)"
nameservers=$(dig "$TARGET" NS +short 2>/dev/null)
if [ ! -z "$nameservers" ]; then
  echo "Attempting zone transfer from nameservers:"
  for ns in $nameservers; do
    echo "Trying $ns..."
    axfr_result=$(dig "@${ns}" "$TARGET" AXFR +noall +answer 2>/dev/null | head -20)
    if [ ! -z "$axfr_result" ]; then
      echo "SUCCESS: Zone transfer allowed from $ns"
      echo "$axfr_result"
    else
      echo "Zone transfer denied or failed for $ns"
    fi
  done
else
  echo "No nameservers found"
fi
echo ""

# Query authoritative nameservers directly
echo "[*] Querying Authoritative Nameservers"
if [ ! -z "$nameservers" ]; then
  for ns in $nameservers; do
    echo "Querying $ns directly:"
    dig "@${ns}" "$TARGET" ANY +noall +answer +comments | head -20
  done
fi
echo ""

# TXT Record Deep Dive
echo "[*] TXT Record Deep Dive (potential internal info leakage)"
dig "$TARGET" TXT +noall +answer
echo ""

# Check for internal IP leakage in A records
echo "[*] Checking for Internal/Private IP Leakage"
all_ips=$(dig "$TARGET" A +short 2>/dev/null)
for ip in $all_ips; do
  if echo "$ip" | grep -qE '^10\.|^172\.(1[6-9]|2[0-9]|3[01])\.|^192\.168\.'; then
    echo "WARNING: Internal IP detected: $ip"
  fi
done
echo ""

echo "=== DNS Reconnaissance Complete ==="
