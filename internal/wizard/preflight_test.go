package wizard

import (
	"testing"

	"github.com/neur0map/ipcrawler/internal/config"
)

func TestExtractBinaries(t *testing.T) {
	tests := []struct {
		name    string
		command string
		want    []string
	}{
		{
			name:    "simple command",
			command: "nmap -sV -p 80 target",
			want:    []string{"nmap"},
		},
		{
			name:    "pipe",
			command: "subfinder -d target -silent | dnsx -a -resp -silent",
			want:    []string{"subfinder", "dnsx"},
		},
		{
			name:    "all builtins",
			command: "[ -s file ] && sudo sed -i.bak 'pattern' /etc/hosts && sudo sh -c 'echo hi' && sudo awk '{print}' file | sudo tee -a /etc/hosts",
			want:    nil,
		},
		{
			name:    "sudo prefix skipped",
			command: "sudo nmap -sV target",
			want:    []string{"nmap"},
		},
		{
			name:    "and-chain",
			command: "subfinder -d target && dnsx -a",
			want:    []string{"subfinder", "dnsx"},
		},
		{
			name:    "or-chain",
			command: "curl -s target || wget target",
			want:    []string{"curl", "wget"},
		},
		{
			name:    "deduplication",
			command: "nmap -sV target | nmap -sC target",
			want:    []string{"nmap"},
		},
		{
			name:    "quoted awk with pipes inside",
			command: "sort -u file | sudo awk '{gsub(/\\[|\\]/, \"\", $2); print $2, $1}' file | sudo tee -a /etc/hosts",
			want:    nil,
		},
		{
			name:    "hosts updater full command",
			command: "[ -s raw/dns_resolved.txt ] && sudo sed -i.bak '/^# ipcrawler START/,/^# ipcrawler END/d' /etc/hosts && sudo sh -c 'echo \"# ipcrawler START\" >> /etc/hosts' && sort -u raw/dns_resolved.txt | sudo awk '{gsub(/\\[|\\]/, \"\", $2); print $2, $1}' | sudo tee -a /etc/hosts > /dev/null && sudo sh -c 'echo \"# ipcrawler END\" >> /etc/hosts' && echo 'Updated /etc/hosts successfully.'",
			want:    nil,
		},
		{
			name:    "hakrevdns command",
			command: "echo 1.2.3.4 | hakrevdns -d | awk -v ip=1.2.3.4 '{print ip, $1}' >> raw/dns_resolved.txt && cat raw/dns_resolved.txt",
			want:    []string{"hakrevdns"},
		},
		{
			name:    "empty command",
			command: "",
			want:    nil,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := extractBinaries(tt.command)
			if len(got) != len(tt.want) {
				t.Fatalf("extractBinaries(%q) = %v, want %v", tt.command, got, tt.want)
			}
			for i := range got {
				if got[i] != tt.want[i] {
					t.Errorf("extractBinaries(%q)[%d] = %q, want %q", tt.command, i, got[i], tt.want[i])
				}
			}
		})
	}
}

func TestFilterMissing(t *testing.T) {
	tools := []config.Template{
		{Name: "Subdomain Resolver", DependsOn: nil},
		{Name: "Hosts Updater", DependsOn: []string{"Subdomain Resolver"}},
		{Name: "Nmap SV Scan", DependsOn: nil},
	}
	commands := map[string]string{
		"Subdomain Resolver": "subfinder -d target | dnsx -a",
		"Hosts Updater":      "[ -s file ] && sudo sed -i.bak 'x' /etc/hosts",
		"Nmap SV Scan":       "nmap -sV target",
	}

	// subfinder is "missing" → Subdomain Resolver removed → Hosts Updater removed (depends_on)
	kept, keptCmds := filterMissing(tools, commands, []string{"subfinder"})

	if len(kept) != 1 {
		t.Fatalf("expected 1 tool remaining, got %d: %v", len(kept), kept)
	}
	if kept[0].Name != "Nmap SV Scan" {
		t.Errorf("expected Nmap SV Scan, got %s", kept[0].Name)
	}
	if _, ok := keptCmds["Nmap SV Scan"]; !ok {
		t.Error("expected Nmap SV Scan in keptCmds")
	}
	if _, ok := keptCmds["Subdomain Resolver"]; ok {
		t.Error("Subdomain Resolver should be removed from keptCmds")
	}
}
