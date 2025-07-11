"""
Unified Rich-powered TUI Wizard for creating IPCrawler plugin templates.
Combines modern Rich patterns with comprehensive intelligence features.
"""

import json
import re
import os
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from urllib.parse import urlparse

from rich.console import Console, Group
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.syntax import Syntax
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.align import Align
from rich.rule import Rule
from rich.columns import Columns
from rich.box import ROUNDED, MINIMAL
from rich.live import Live

from ..models.template import ToolTemplate
from ..core.schema import TemplateSchema


class TemplateWizard:
    """Unified Rich TUI Wizard for creating plugin templates with intelligence."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.console = Console()
        self.template_data = {}
        self.current_step = 1
        self.total_steps = 10
        self.is_chain_template = False
        
        # User context
        self.user_experience_level = "beginner"  # beginner, intermediate, advanced
        self.assessment_type = None
        self.target_info = {}
        self.suggested_tools = []
        
        # Theme colors
        self.theme = config.get("theme", "minimal")
        self.colors = self._get_theme_colors()
        
        # Main layout - set up once and update content
        self.layout = Layout()
        self._setup_layout()
        
        # Assessment types with descriptions and suggested tools
        self.assessment_types = {
            "network_recon": {
                "name": "Find Open Ports & Services",
                "description": "Discover what services are running on a target (like web servers, SSH, etc.)",
                "beginner_description": "Perfect for: Finding what's running on a server or IP address",
                "tools": ["nmap", "ping", "masscan"],
                "common_presets": ["nmap.quick_tcp", "nmap.service_scan", "nmap.htb_scan"],
                "wordlist_hint": None,
                "typical_timeout": 300
            },
            "web_app": {
                "name": "Explore Websites & Web Apps", 
                "description": "Find hidden pages, directories, and files on websites",
                "beginner_description": "Perfect for: Discovering hidden parts of websites",
                "tools": ["curl", "feroxbuster", "gobuster", "nuclei"],
                "common_presets": ["curl.fast_content", "feroxbuster.ctf_fast", "gobuster.ctf_dir_fast"],
                "wordlist_hint": "directory",
                "typical_timeout": 180
            },
            "admin_discovery": {
                "name": "Find Admin Panels",
                "description": "Look for admin login pages and management interfaces",
                "beginner_description": "Perfect for: Finding admin pages like /admin, /login, /dashboard",
                "tools": ["feroxbuster", "gobuster", "curl"],
                "common_presets": ["feroxbuster.ctf_extensions", "gobuster.ctf_dir_fast"],
                "wordlist_hint": "admin",
                "typical_timeout": 120
            },
            "ctf_challenge": {
                "name": "CTF & Hacking Challenges",
                "description": "Optimized for Capture The Flag competitions and practice",
                "beginner_description": "Perfect for: HackTheBox, TryHackMe, and other CTF challenges",
                "tools": ["nmap", "feroxbuster", "gobuster", "curl"],
                "common_presets": ["nmap.htb_scan", "feroxbuster.ctf_fast", "gobuster.ctf_dir_fast"],
                "wordlist_hint": "directory",
                "typical_timeout": 90
            }
        }
        
        # Tool explanations
        self.tool_explanations = {
            "nmap": {
                "description": "Network scanner for discovering hosts, ports, and services",
                "use_cases": ["Port scanning", "Service detection", "OS fingerprinting"],
                "common_args": {"target": "{{target}}", "basic": "-sT", "fast": "-T4", "ports": "--top-ports 1000"}
            },
            "curl": {
                "description": "HTTP client for web requests and header analysis",
                "use_cases": ["HTTP headers", "Content fetching", "API testing"],
                "common_args": {"target": "{{target}}", "headers": "-I", "silent": "-s", "timeout": "--max-time 30"}
            },
            "feroxbuster": {
                "description": "Fast directory and file enumeration tool",
                "use_cases": ["Directory discovery", "File enumeration", "Backup file hunting"],
                "common_args": {"url": "-u {{target}}", "wordlist": "-w auto_wordlist", "threads": "-t 20", "status": "-s 200,403"}
            },
            "gobuster": {
                "description": "Directory and DNS enumeration tool",
                "use_cases": ["Directory discovery", "Virtual host enumeration", "DNS enumeration"],
                "common_args": {"mode": "dir", "url": "-u {{target}}", "wordlist": "-w auto_wordlist", "threads": "-t 20"}
            },
            "nuclei": {
                "description": "Vulnerability scanner with template-based detection",
                "use_cases": ["Vulnerability scanning", "Security testing", "Configuration checks"],
                "common_args": {"target": "-u {{target}}", "severity": "-severity medium,high,critical", "silent": "-silent"}
            },
            "ping": {
                "description": "Network connectivity testing tool",
                "use_cases": ["Connectivity testing", "Network reachability", "Basic network diagnostics"],
                "common_args": {"target": "{{target}}", "count": "-c 4", "timeout": "-W 3"}
            },
            "dig": {
                "description": "DNS lookup and query tool",
                "use_cases": ["DNS resolution", "Domain information", "DNS record lookup"],
                "common_args": {"target": "{{target}}", "short": "+short", "trace": "+trace"}
            },
            "masscan": {
                "description": "High-speed port scanner",
                "use_cases": ["Fast port scanning", "Large network discovery", "Initial reconnaissance"],
                "common_args": {"target": "{{target}}", "ports": "-p1-65535", "rate": "--rate=1000"}
            }
        }
        
        # Chain template patterns
        self.chain_patterns = {
            "recon_to_enum": {
                "name": "Reconnaissance → Enumeration",
                "description": "Network scan followed by web enumeration of discovered services",
                "pattern": [
                    {"tool": "nmap", "preset": "nmap.service_scan", "purpose": "Discover services and open ports"},
                    {"tool": "feroxbuster", "preset": "feroxbuster.ctf_fast", "purpose": "Enumerate web directories on discovered HTTP services"}
                ]
            },
            "discovery_to_analysis": {
                "name": "Discovery → Analysis", 
                "description": "Service discovery followed by vulnerability analysis",
                "pattern": [
                    {"tool": "nmap", "preset": "nmap.quick_tcp", "purpose": "Quick port discovery"},
                    {"tool": "nuclei", "preset": None, "purpose": "Vulnerability analysis of discovered services"}
                ]
            },
            "web_full_enum": {
                "name": "Complete Web Enumeration",
                "description": "HTTP analysis followed by comprehensive directory enumeration",
                "pattern": [
                    {"tool": "curl", "preset": "curl.basic_info", "purpose": "Analyze HTTP headers and server info"},
                    {"tool": "feroxbuster", "preset": "feroxbuster.ctf_deep", "purpose": "Deep directory scan with extensions"}
                ]
            },
            "comprehensive_recon": {
                "name": "Comprehensive Reconnaissance",
                "description": "Full reconnaissance workflow: discovery → enumeration → analysis",
                "pattern": [
                    {"tool": "nmap", "preset": "nmap.service_scan", "purpose": "Discover services and versions"},
                    {"tool": "feroxbuster", "preset": "feroxbuster.ctf_fast", "purpose": "Enumerate web directories"},
                    {"tool": "nuclei", "preset": None, "purpose": "Vulnerability scanning"}
                ]
            },
            "ctf_workflow": {
                "name": "CTF Optimized Workflow",
                "description": "Fast CTF workflow optimized for speed and noise reduction",
                "pattern": [
                    {"tool": "nmap", "preset": "nmap.htb_scan", "purpose": "Quick service discovery"},
                    {"tool": "gobuster", "preset": "gobuster.ctf_dir_fast", "purpose": "Fast directory enumeration"},
                    {"tool": "feroxbuster", "preset": "feroxbuster.ctf_extensions", "purpose": "Extension-based file discovery"}
                ]
            }
        }

        # Template categories
        self.template_categories = ["default", "recon", "custom", "htb"]
        
        # Wordlist hints for enumeration tools
        self.wordlist_hints = [
            "directory", "admin", "api", "vhost", "backup", 
            "php", "asp", "wordpress", "drupal", "joomla",
            "cms", "files", "extensions"
        ]
    
    def _get_theme_colors(self) -> Dict[str, str]:
        """Get theme colors."""
        themes = {
            "minimal": {
                "border": "white", "header": "bright_white", "info": "blue", 
                "success": "green", "warning": "yellow", "error": "red", "accent": "cyan"
            },
            "dark": {
                "border": "dim white", "header": "bright_white", "info": "bright_blue",
                "success": "bright_green", "warning": "bright_yellow", "error": "bright_red", "accent": "bright_cyan"
            },
            "matrix": {
                "border": "bright_green", "header": "bright_green", "info": "green",
                "success": "bright_green", "warning": "yellow", "error": "red", "accent": "bright_green"
            },
            "cyber": {
                "border": "bright_cyan", "header": "bright_magenta", "info": "cyan",
                "success": "green", "warning": "yellow", "error": "red", "accent": "bright_cyan"
            },
            "hacker": {
                "border": "bright_green", "header": "bright_green", "info": "green",
                "success": "bright_green", "warning": "bright_yellow", "error": "bright_red", "accent": "bright_green"
            },
            "corporate": {
                "border": "blue", "header": "bright_blue", "info": "blue",
                "success": "green", "warning": "yellow", "error": "red", "accent": "bright_blue"
            }
        }
        return themes.get(self.theme, themes["minimal"])
    
    def _setup_layout(self) -> None:
        """Set up the main layout structure once."""
        # Create main layout split: header + content
        self.layout.split_column(
            Layout(name="header", size=5),
            Layout(name="content", ratio=1)
        )
        
        # Split content: question + preview
        self.layout["content"].split_row(
            Layout(name="question", size=70),
            Layout(name="preview", ratio=1)
        )
    
    def _create_header(self) -> Panel:
        """Create wizard header."""
        title = Text("🧙 Enhanced IPCrawler Template Wizard", style=f"bold {self.colors['header']}")
        subtitle = Text(f"Step {self.current_step} of {self.total_steps} • {self.user_experience_level.title()} Mode", 
                       style=self.colors['info'])
        header_text = Text.assemble(title, "\n", subtitle)
        
        return Panel(
            Align.center(header_text),
            box=ROUNDED,
            border_style=self.colors['border'],
            padding=(1, 2)
        )
    
    def _create_json_preview(self) -> Panel:
        """Create JSON preview panel."""
        if not self.template_data:
            content = Text.assemble(
                Text("🔍 Live JSON Preview", style=f"bold {self.colors['header']}"),
                "\n\n",
                Text("Your template will appear here as you", style=self.colors['info']),
                "\n",
                Text("answer questions step by step.", style=self.colors['info']),
                "\n\n",
                Text("💡 Pro tip: Preview updates in real-time!", style=self.colors['accent'])
            )
        else:
            # Create clean template data for preview
            preview_data = dict(self.template_data)
            if "_metadata" in preview_data:
                del preview_data["_metadata"]
            if "template_complexity" in preview_data:
                del preview_data["template_complexity"]
            
            json_str = json.dumps(preview_data, indent=2)
            content = Syntax(json_str, "json", theme="monokai", line_numbers=True)
        
        return Panel(
            content,
            title="🔍 Live Template Preview",
            title_align="left",
            box=ROUNDED,
            border_style=self.colors['accent'],
            padding=(1, 2)
        )
    
    def _update_display(self, question_panel: Panel) -> None:
        """Update the display with new content - without Live context for input visibility."""
        # Clear screen and display the layout
        self.console.clear()
        
        # Update all layout components
        self.layout["header"].update(self._create_header())
        self.layout["question"].update(question_panel)
        self.layout["preview"].update(self._create_json_preview())
        
        # Print the layout directly
        self.console.print(self.layout)
    
    def _analyze_target(self, target: str) -> Dict[str, Any]:
        """Analyze target to provide intelligent suggestions."""
        analysis = {
            "type": "unknown",
            "protocol": None,
            "domain": None,
            "ip": None,
            "port": None,
            "suggested_tools": [],
            "suggested_assessment": None
        }
        
        # URL analysis
        if target.startswith(('http://', 'https://')):
            parsed = urlparse(target)
            analysis["type"] = "url"
            analysis["protocol"] = parsed.scheme
            analysis["domain"] = parsed.netloc
            analysis["suggested_tools"] = ["curl", "feroxbuster", "nuclei"]
            analysis["suggested_assessment"] = "web_app"
            
        # IP address analysis
        elif re.match(r'^(\d{1,3}\.){3}\d{1,3}$', target):
            analysis["type"] = "ip"
            analysis["ip"] = target
            analysis["suggested_tools"] = ["nmap", "ping"]
            analysis["suggested_assessment"] = "network_recon"
            
        # Domain analysis
        elif re.match(r'^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]*\..*$', target):
            analysis["type"] = "domain"
            analysis["domain"] = target
            analysis["suggested_tools"] = ["nmap", "curl", "feroxbuster"]
            analysis["suggested_assessment"] = "comprehensive_scan"
            
        # Port specification (IP:PORT)
        elif ':' in target and re.match(r'^(\d{1,3}\.){3}\d{1,3}:\d+$', target):
            ip, port = target.split(':')
            analysis["type"] = "ip_port"
            analysis["ip"] = ip
            analysis["port"] = int(port)
            analysis["suggested_tools"] = ["nmap", "curl"] if port in ['80', '443', '8080', '8443'] else ["nmap"]
            analysis["suggested_assessment"] = "network_recon"
            
        return analysis
    
    def _ask_multiple_choice(self, question: str, options: List[str], 
                           descriptions: List[str] = None, help_text: str = "") -> Tuple[int, str]:
        """Ask multiple choice question with proper layout update."""
        # Create options table
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Choice", style=self.colors['accent'], width=4)
        table.add_column("Option", style="white", width=25)
        if descriptions:
            table.add_column("Description", style=self.colors['info'])
        
        for i, option in enumerate(options, 1):
            if descriptions and i <= len(descriptions):
                table.add_row(f"{i}.", option, descriptions[i-1])
            else:
                table.add_row(f"{i}.", option)
        
        content_items = [
            Text(question, style=f"bold {self.colors['header']}"),
            Text(""),
        ]
        
        if help_text:
            content_items.extend([
                Text(help_text, style=self.colors['info']),
                Text("")
            ])
        
        content_items.extend([
            table,
            Text(""),
            Text("💡 Press Ctrl+C to cancel at any time", style=self.colors['warning'])
        ])
        
        question_panel = Panel(
            Group(*content_items),
            title="❓ Question",
            title_align="left",
            box=ROUNDED,
            border_style=self.colors['border'],
            padding=(1, 2)
        )
        
        # Update the layout
        self._update_display(question_panel)
        
        while True:
            try:
                self.console.print()  # Add space before prompt for visibility
                choice = IntPrompt.ask(
                    f"[{self.colors['accent']}]➤ Enter your choice (1-{len(options)})[/]",
                    default=1,
                    console=self.console
                )
                if 1 <= choice <= len(options):
                    return choice, options[choice - 1]
                else:
                    self.console.print(f"[{self.colors['error']}]❌ Please enter a number between 1 and {len(options)}[/]")
            except KeyboardInterrupt:
                self.console.print(f"\n[{self.colors['warning']}]⚠️  Wizard cancelled by user[/]")
                raise KeyboardInterrupt("User cancelled wizard")
            except ValueError:
                self.console.print(f"[{self.colors['error']}]❌ Please enter a valid number[/]")
    
    def _ask_text_input(self, question: str, help_text: str = "", 
                       default: str = "", required: bool = True, 
                       validation_pattern: str = None) -> str:
        """Ask text input question with proper layout update."""
        content_items = [
            Text(question, style=f"bold {self.colors['header']}"),
            Text(""),
        ]
        
        if help_text:
            content_items.extend([
                Text(help_text, style=self.colors['info']),
                Text("")
            ])
        
        if default:
            content_items.extend([
                Text(f"💡 Default: {default}", style=self.colors['accent']),
                Text("")
            ])
        
        content_items.extend([
            Text("💡 Press Ctrl+C to cancel at any time", style=self.colors['warning'])
        ])
        
        question_panel = Panel(
            Group(*content_items),
            title="❓ Question",
            title_align="left",
            box=ROUNDED,
            border_style=self.colors['border'],
            padding=(1, 2)
        )
        
        # Update the layout
        self._update_display(question_panel)
        
        while True:
            try:
                self.console.print()  # Add space before prompt for visibility
                answer = Prompt.ask(
                    f"[{self.colors['accent']}]➤ Your answer[/]",
                    default=default if default else None,
                    console=self.console
                )
                if answer is None:
                    answer = ""
                    
                # Validation
                if validation_pattern and answer:
                    if not re.match(validation_pattern, answer):
                        self.console.print(f"[{self.colors['error']}]❌ Invalid format. Please try again.[/]")
                        continue
                
                if answer.strip() or not required:
                    return answer.strip()
                else:
                    self.console.print(f"[{self.colors['error']}]❌ This field is required[/]")
            except KeyboardInterrupt:
                self.console.print(f"\n[{self.colors['warning']}]⚠️  Wizard cancelled by user[/]")
                raise KeyboardInterrupt("User cancelled wizard")
    
    def _ask_yes_no(self, question: str, help_text: str = "", default: bool = False) -> bool:
        """Ask yes/no question with proper layout update."""
        content_items = [
            Text(question, style=f"bold {self.colors['header']}"),
            Text(""),
        ]
        
        if help_text:
            content_items.extend([
                Text(help_text, style=self.colors['info']),
                Text("")
            ])
        
        content_items.extend([
            Text("💡 Press Ctrl+C to cancel at any time", style=self.colors['warning'])
        ])
        
        question_panel = Panel(
            Group(*content_items),
            title="❓ Question",
            title_align="left",
            box=ROUNDED,
            border_style=self.colors['border'],
            padding=(1, 2)
        )
        
        # Update the layout
        self._update_display(question_panel)
        
        try:
            self.console.print()  # Add space before prompt for visibility
            return Confirm.ask(
                f"[{self.colors['accent']}]➤ Your choice (y/n)[/]",
                default=default,
                console=self.console
            )
        except KeyboardInterrupt:
            self.console.print(f"\n[{self.colors['warning']}]⚠️  Wizard cancelled by user[/]")
            raise KeyboardInterrupt("User cancelled wizard")
    
    # Wizard steps
    def step1_experience_level(self) -> None:
        """Step 1: Experience level selection."""
        self.current_step = 1
        
        options = [
            "Beginner - Guide me with smart defaults",
            "Intermediate - Balance of automation and customization", 
            "Advanced - Full control over all settings"
        ]
        
        descriptions = [
            "Perfect for new users with optimal presets",
            "Great balance of automation and customization",
            "Full control with advanced options"
        ]
        
        choice, _ = self._ask_multiple_choice(
            "What's your experience level with security tools?",
            options,
            descriptions,
            "This determines the wizard flow complexity and available options."
        )
        
        levels = ["beginner", "intermediate", "advanced"]
        self.user_experience_level = levels[choice - 1]
        # Dramatically different flows for different experience levels
        self.total_steps = 4 if self.user_experience_level == "beginner" else 11
    
    def step2_assessment_type(self) -> None:
        """Step 2: Assessment type selection."""
        self.current_step = 2
        
        options = []
        descriptions = []
        for key, assessment in self.assessment_types.items():
            options.append(assessment["name"])
            if self.user_experience_level == "beginner" and "beginner_description" in assessment:
                descriptions.append(assessment["beginner_description"])
            else:
                descriptions.append(assessment["description"])
        
        question = "What do you want your security template to do?" if self.user_experience_level == "beginner" else "What type of security assessment do you want to perform?"
        help_text = "Choose what you want to accomplish with this template." if self.user_experience_level == "beginner" else "Choose the assessment type that matches your security goals."
        
        choice, selected = self._ask_multiple_choice(
            question,
            options,
            descriptions,
            help_text
        )
        
        assessment_keys = list(self.assessment_types.keys())
        self.assessment_type = assessment_keys[choice - 1]
        assessment_info = self.assessment_types[self.assessment_type]
        
        # Set intelligent defaults
        self.suggested_tools = assessment_info["tools"]
        self.is_chain_template = assessment_info.get("is_chain", False)
        
        if self.user_experience_level == "beginner":
            self.template_data.update({
                "timeout": assessment_info["typical_timeout"],
                "tags": [self.assessment_type.replace("_", "-"), "wizard-created"]
            })
            if assessment_info["wordlist_hint"]:
                self.template_data["wordlist_hint"] = assessment_info["wordlist_hint"]
    
    def step3_beginner_simple_config(self) -> None:
        """Step 3: Super simple configuration for beginners."""
        if self.user_experience_level != "beginner":
            return self.step3_basic_template_info()
            
        self.current_step = 3
        
        # For beginners: Just get a simple name, everything else is auto-configured
        assessment_info = self.assessment_types[self.assessment_type]
        suggested_name = f"my-{self.assessment_type.replace('_', '-')}"
        
        name = self._ask_text_input(
            "What should we call your security template?",
            f"This will create a template for: {assessment_info['name']}",
            default=suggested_name,
            validation_pattern=r"^[a-zA-Z0-9_-]+$"
        )
        
        self.template_data["name"] = name
        self.template_data["description"] = f"{assessment_info['name']} - {assessment_info['description']}"
        
        # Auto-configure everything for beginners
        self._auto_configure_beginner_template()
    
    def _auto_configure_beginner_template(self) -> None:
        """Automatically configure template for beginners - no technical questions."""
        assessment_info = self.assessment_types[self.assessment_type]
        
        # Auto-select best tool for this assessment
        best_tool = assessment_info["tools"][0]  # First tool is usually the primary one
        self.template_data["tool"] = best_tool
        
        # Auto-apply best preset
        tool_presets = [preset for preset in assessment_info["common_presets"] if preset.startswith(f"{best_tool}.")]
        if tool_presets:
            self.template_data["preset"] = tool_presets[0]
            self.template_data["args"] = ["{{target}}"]
        else:
            # Fallback args if no preset
            self.template_data["args"] = ["{{target}}"]
        
        # Auto-configure wordlist for enumeration tools
        if best_tool in ["feroxbuster", "gobuster"] and assessment_info["wordlist_hint"]:
            if best_tool == "feroxbuster":
                self.template_data["args"] = ["-u", "{{target}}", "-w", "auto_wordlist"]
            elif best_tool == "gobuster":
                self.template_data["args"] = ["dir", "-u", "{{target}}", "-w", "auto_wordlist"]
            self.template_data["wordlist"] = "auto_wordlist"
            self.template_data["wordlist_hint"] = assessment_info["wordlist_hint"]
        
        # Auto-set timeout and tags
        self.template_data["timeout"] = assessment_info["typical_timeout"]
        self.template_data["tags"] = [
            self.assessment_type.replace("_", "-"),
            "beginner-friendly", 
            "auto-configured",
            "wizard-created"
        ]
        
        # Show what was auto-configured
        self._show_auto_configuration()
    
    def _show_auto_configuration(self) -> None:
        """Show beginners what was automatically configured."""
        content_items = [
            Text("🎉 Your template has been automatically configured!", style=f"bold {self.colors['success']}"),
            Text(""),
            Text("Here's what I set up for you:", style=self.colors['info']),
            Text(""),
            Text(f"🔧 Tool: {self.template_data['tool']}", style="white"),
            Text(f"⚡ Preset: {self.template_data.get('preset', 'Default configuration')}", style="white"),
            Text(f"⏱️  Timeout: {self.template_data['timeout']} seconds", style="white"),
        ]
        
        if self.template_data.get('wordlist'):
            content_items.append(Text(f"📝 Wordlist: Auto-selected for {self.template_data['wordlist_hint']} discovery", style="white"))
        
        content_items.extend([
            Text(""),
            Text("✨ This template is ready to use - no technical configuration needed!", style=self.colors['success'])
        ])
        
        info_panel = Panel(
            Group(*content_items),
            title="🤖 Auto-Configuration Complete",
            title_align="left",
            box=ROUNDED,
            border_style=self.colors['success'],
            padding=(1, 2)
        )
        
        self._update_display(info_panel)
        
        # Just ask if they want to continue
        self._ask_yes_no(
            "Does this look good to you?",
            "If yes, we'll save this template. If no, you can choose a different assessment type.",
            default=True
        )

    def step3_basic_template_info(self) -> None:
        """Step 3: Basic template information (for intermediate/advanced)."""
        self.current_step = 3
        
        # Template name with intelligent suggestion
        if self.assessment_type:
            suggested_name = f"{self.assessment_type.replace('_', '-')}-template"
        else:
            suggested_name = "my-security-template"
        
        name = self._ask_text_input(
            "What should we name this template?",
            "Use lowercase letters, numbers, hyphens, and underscores only.",
            default=suggested_name,
            validation_pattern=r"^[a-zA-Z0-9_-]+$"
        )
        
        self.template_data["name"] = name
        
        # Description with intelligent suggestion
        if self.assessment_type:
            assessment_info = self.assessment_types[self.assessment_type]
            suggested_description = f"{assessment_info['name']} - {assessment_info['description']}"
        else:
            suggested_description = ""
        
        description = self._ask_text_input(
            "Enter a description for this template:",
            "Brief description of what this template does.",
            default=suggested_description,
            required=False
        )
        
        if description:
            self.template_data["description"] = description
    
    def step4_tool_selection(self) -> None:
        """Step 4: Tool selection with intelligent defaults."""
        self.current_step = 4
        
        # For beginners, auto-select first suggested tool
        if self.user_experience_level == "beginner" and self.suggested_tools:
            selected_tool = self.suggested_tools[0]
            self.template_data["tool"] = selected_tool
            
            # Auto-apply preset
            assessment_info = self.assessment_types[self.assessment_type]
            tool_presets = [preset for preset in assessment_info["common_presets"] if preset.startswith(f"{selected_tool}.")]
            if tool_presets:
                self.template_data["preset"] = tool_presets[0]
                self.template_data["args"] = ["{{target}}"]
                
                # Add wordlist for enumeration tools
                if selected_tool in ["feroxbuster", "gobuster"] and assessment_info["wordlist_hint"]:
                    if selected_tool == "feroxbuster":
                        self.template_data["args"] = ["-u", "{{target}}", "-w", "auto_wordlist"]
                    elif selected_tool == "gobuster":
                        self.template_data["args"] = ["dir", "-u", "{{target}}", "-w", "auto_wordlist"]
                    self.template_data["wordlist"] = "auto_wordlist"
                    self.template_data["wordlist_hint"] = assessment_info["wordlist_hint"]
            return
        
        # For intermediate/advanced users, show tool selection
        if self.suggested_tools:
            use_suggested = self._ask_yes_no(
                f"Use suggested tools for {self.assessment_types[self.assessment_type]['name']}?",
                f"Recommended: {', '.join(self.suggested_tools)}",
                default=True
            )
            
            if use_suggested:
                if len(self.suggested_tools) == 1:
                    selected_tool = self.suggested_tools[0]
                else:
                    choice, selected_tool = self._ask_multiple_choice(
                        "Which suggested tool would you like to use?",
                        self.suggested_tools,
                        [self.tool_explanations[tool]["description"] for tool in self.suggested_tools]
                    )
            else:
                all_tools = list(self.tool_explanations.keys())
                choice, selected_tool = self._ask_multiple_choice(
                    "Which tool would you like to use?",
                    all_tools,
                    [self.tool_explanations[tool]["description"] for tool in all_tools]
                )
        else:
            all_tools = list(self.tool_explanations.keys())
            choice, selected_tool = self._ask_multiple_choice(
                "Which tool would you like to use?",
                all_tools,
                [self.tool_explanations[tool]["description"] for tool in all_tools]
            )
        
        self.template_data["tool"] = selected_tool
        
        # Configure tool with preset or manual args
        self._configure_tool_with_presets(selected_tool)
    
    def _configure_tool_with_presets(self, tool: str) -> None:
        """Configure tool with preset options."""
        assessment_info = self.assessment_types[self.assessment_type]
        tool_presets = [preset for preset in assessment_info["common_presets"] if preset.startswith(f"{tool}.")]
        
        if tool_presets and self.user_experience_level != "advanced":
            preset_options = []
            for preset in tool_presets:
                preset_name = preset.split(".", 1)[1]
                preset_options.append(preset_name)
            
            preset_options.append("Custom arguments")
            
            choice, selected_preset = self._ask_multiple_choice(
                f"Choose configuration for {tool}:",
                preset_options,
                [f"Optimized preset for {assessment_info['name'].lower()}"] * len(tool_presets) + ["Manual configuration"]
            )
            
            if choice <= len(tool_presets):
                # Use preset
                self.template_data["preset"] = tool_presets[choice - 1]
                self.template_data["args"] = ["{{target}}"]
                
                # Add wordlist for enumeration tools
                if tool in ["feroxbuster", "gobuster"] and assessment_info["wordlist_hint"]:
                    if tool == "feroxbuster":
                        self.template_data["args"] = ["-u", "{{target}}", "-w", "auto_wordlist"]
                    elif tool == "gobuster":
                        self.template_data["args"] = ["dir", "-u", "{{target}}", "-w", "auto_wordlist"]
                    self.template_data["wordlist"] = "auto_wordlist"
                    self.template_data["wordlist_hint"] = assessment_info["wordlist_hint"]
            else:
                # Custom arguments
                self._configure_custom_arguments(tool)
        else:
            # No presets or advanced user
            self._configure_custom_arguments(tool)
    
    def _configure_custom_arguments(self, tool: str) -> None:
        """Configure custom arguments with guidance."""
        args = []
        
        # Show instructions as part of the first question
        help_text = f"💡 Enter arguments for {tool}. Use {{{{target}}}} as placeholder. Press Enter with empty line to finish."
        
        while len(args) < 10:  # Reasonable limit
            arg = self._ask_text_input(
                f"Argument {len(args) + 1} for {tool}:",
                help_text if len(args) == 0 else "Enter command line argument or press Enter to finish",
                required=False
            )
            if not arg:
                break
            args.append(arg)
        
        if not args:
            args = ["{{target}}"]
        
        self.template_data["args"] = args
    
    def step5_chain_template_options(self) -> None:
        """Step 5: Chain template creation (if applicable)."""
        if self.user_experience_level == "beginner":
            return
            
        self.current_step = 5
        
        # Check if this assessment type supports chaining or if user wants to create a chain
        if self.is_chain_template or self.assessment_type == "comprehensive_scan":
            create_chain = self._ask_yes_no(
                "Create a chain template with multiple tools?",
                f"Chain templates run multiple tools in sequence, passing results between them. Great for comprehensive workflows.",
                default=True
            )
        else:
            create_chain = self._ask_yes_no(
                "Convert this to a chain template with multiple tools?",
                "Chain templates run multiple tools in sequence. For example: nmap → feroxbuster for discovered web services.",
                default=False
            )
        
        if create_chain:
            self._configure_chain_template()
    
    def _configure_chain_template(self) -> None:
        """Configure chain template with multiple tools."""
        # Ask if user wants to use a predefined pattern or create custom
        use_pattern = self._ask_yes_no(
            "Use a predefined workflow pattern?",
            "Predefined patterns provide tested tool combinations for common security workflows.",
            default=True
        )
        
        if use_pattern:
            self._select_chain_pattern()
        else:
            self._create_custom_chain()
    
    def _select_chain_pattern(self) -> None:
        """Select from predefined chain patterns."""
        pattern_options = []
        pattern_descriptions = []
        pattern_keys = []
        
        for key, pattern in self.chain_patterns.items():
            pattern_options.append(pattern["name"])
            pattern_descriptions.append(pattern["description"])
            pattern_keys.append(key)
        
        # Add custom option
        pattern_options.append("Create custom chain")
        pattern_descriptions.append("Build your own tool chain step by step")
        
        choice, selected = self._ask_multiple_choice(
            "Choose a workflow pattern:",
            pattern_options,
            pattern_descriptions,
            "Select a proven workflow pattern for your security assessment."
        )
        
        if choice <= len(pattern_keys):
            # Use predefined pattern
            selected_pattern = self.chain_patterns[pattern_keys[choice - 1]]
            self._apply_chain_pattern(selected_pattern)
        else:
            # Create custom chain
            self._create_custom_chain()
    
    def _apply_chain_pattern(self, pattern: Dict[str, Any]) -> None:
        """Apply a predefined chain pattern."""
        self.template_data["chain_template"] = True
        self.template_data["workflow_pattern"] = pattern["name"]
        self.template_data["chain_steps"] = []
        
        for i, step in enumerate(pattern["pattern"]):
            step_data = {
                "step_number": i + 1,
                "tool": step["tool"],
                "purpose": step["purpose"],
                "args": ["{{target}}"]  # Default args
            }
            
            if step["preset"]:
                step_data["preset"] = step["preset"]
            
            # Add result passing for subsequent steps
            if i > 0:
                step_data["input_from_step"] = i  # Previous step (0-indexed)
                # Modify args to use results from previous step
                if step["tool"] in ["feroxbuster", "gobuster"]:
                    # For directory enumeration, use discovered web services
                    step_data["args"] = ["-u", "{{target}}", "-w", "auto_wordlist"]
                    step_data["condition"] = "web_service_found"
                elif step["tool"] == "nuclei":
                    # For vulnerability scanning, use discovered services
                    step_data["args"] = ["-u", "{{target}}", "-severity", "medium,high,critical"]
                    step_data["condition"] = "service_discovered"
            
            self.template_data["chain_steps"].append(step_data)
        
        # Update main template fields to reflect the first tool in chain
        first_step = pattern["pattern"][0]
        self.template_data["tool"] = first_step["tool"]
        if first_step["preset"]:
            self.template_data["preset"] = first_step["preset"]
        
        # Add chain-specific metadata
        self.template_data["description"] = f"Chain template: {pattern['description']}"
        if "tags" not in self.template_data:
            self.template_data["tags"] = []
        self.template_data["tags"].extend(["chain", "workflow", "multi-tool"])
    
    def _create_custom_chain(self) -> None:
        """Create a custom chain template."""
        self.template_data["chain_template"] = True
        self.template_data["chain_steps"] = []
        
        # Start with the currently selected tool as first step
        first_step = {
            "step_number": 1,
            "tool": self.template_data["tool"],
            "purpose": f"{self.template_data['tool']} analysis",
            "args": self.template_data.get("args", ["{{target}}"])
        }
        
        if "preset" in self.template_data:
            first_step["preset"] = self.template_data["preset"]
        
        self.template_data["chain_steps"].append(first_step)
        
        # Add additional steps
        while len(self.template_data["chain_steps"]) < 5:  # Limit to 5 steps
            step_num = len(self.template_data["chain_steps"]) + 1
            
            add_step = self._ask_yes_no(
                f"Add step {step_num} to the chain?",
                f"Current chain: {' → '.join([step['tool'] for step in self.template_data['chain_steps']])}",
                default=True if step_num == 2 else False
            )
            
            if not add_step:
                break
            
            # Select tool for this step
            available_tools = [tool for tool in self.tool_explanations.keys() 
                             if tool not in [step["tool"] for step in self.template_data["chain_steps"]]]
            
            if not available_tools:
                self.console.print(f"[{self.colors['warning']}]No more unique tools available for chaining.[/]")
                break
            
            choice, selected_tool = self._ask_multiple_choice(
                f"Choose tool for step {step_num}:",
                available_tools,
                [self.tool_explanations[tool]["description"] for tool in available_tools],
                f"This tool will receive results from step {step_num - 1} ({self.template_data['chain_steps'][-1]['tool']})"
            )
            
            # Get purpose for this step
            purpose = self._ask_text_input(
                f"What is the purpose of {selected_tool} in this workflow?",
                f"Example: 'Enumerate directories on discovered web services'",
                default=f"{selected_tool} analysis"
            )
            
            # Configure the step
            step_data = {
                "step_number": step_num,
                "tool": selected_tool,
                "purpose": purpose,
                "input_from_step": step_num - 1,  # Previous step
                "args": ["{{target}}"]
            }
            
            # Auto-configure common tool chains
            previous_tool = self.template_data["chain_steps"][-1]["tool"]
            if previous_tool == "nmap" and selected_tool in ["feroxbuster", "gobuster"]:
                step_data["args"] = ["-u", "{{target}}", "-w", "auto_wordlist"]
                step_data["condition"] = "web_service_found"
                step_data["wordlist"] = "auto_wordlist"
                step_data["wordlist_hint"] = "directory"
            elif previous_tool in ["nmap", "feroxbuster"] and selected_tool == "nuclei":
                step_data["args"] = ["-u", "{{target}}", "-severity", "medium,high,critical"]
                step_data["condition"] = "service_discovered"
            
            self.template_data["chain_steps"].append(step_data)
        
        # Add chain-specific metadata
        if "tags" not in self.template_data:
            self.template_data["tags"] = []
        self.template_data["tags"].extend(["chain", "custom-workflow", "multi-tool"])
        
        # Update description
        tool_chain = " → ".join([step["tool"] for step in self.template_data["chain_steps"]])
        self.template_data["description"] = f"Custom chain template: {tool_chain}"
    
    def step6_advanced_options(self) -> None:
        """Step 6: Advanced options (only for intermediate/advanced users)."""
        if self.user_experience_level == "beginner":
            return
            
        self.current_step = 6
        
        # Timeout customization
        use_custom_timeout = self._ask_yes_no(
            "Set custom timeout?",
            f"Default timeout is {self.template_data.get('timeout', 60)} seconds.",
            default=False
        )
        
        if use_custom_timeout:
            timeout_panel = Panel(
                Text("Enter timeout in seconds (1-600):", style=f"bold {self.colors['header']}"),
                title="❓ Question",
                title_align="left",
                box=ROUNDED,
                border_style=self.colors['border']
            )
            self._update_display(timeout_panel)
            
            timeout = IntPrompt.ask(
                f"\n[{self.colors['accent']}]Timeout (seconds)[/]",
                default=self.template_data.get("timeout", 60)
            )
            if 1 <= timeout <= 600:
                self.template_data["timeout"] = timeout
        
        # Tags customization
        current_tags = self.template_data.get("tags", [])
        if current_tags:
            modify_tags = self._ask_yes_no(
                f"Modify current tags? Current: {', '.join(current_tags)}",
                "You can add additional tags or replace existing ones.",
                default=False
            )
        else:
            modify_tags = self._ask_yes_no(
                "Add tags for categorization?",
                "Tags help organize and filter templates. Example: web, recon, fast",
                default=True
            )
        
        if modify_tags:
            tags = list(current_tags) if current_tags else []
            
            while len(tags) < 10:  # Limit to 10 tags
                tag = self._ask_text_input(
                    f"Tag {len(tags) + 1}:",
                    "Add tags one by one. Enter tag name or press Enter to finish",
                    required=False
                )
                if not tag:
                    break
                if tag not in tags:  # Avoid duplicates
                    tags.append(tag)
            
            if tags:
                self.template_data["tags"] = tags
    
    def step4_beginner_save(self) -> bool:
        """Step 4: Simple save for beginners."""
        if self.user_experience_level != "beginner":
            return False  # This step is only for beginners
            
        self.current_step = 4
        
        # Simple category selection for beginners
        assessment_info = self.assessment_types[self.assessment_type]
        
        # Auto-suggest category based on assessment type
        if self.assessment_type in ["network_recon"]:
            suggested_category = "recon"
        elif self.assessment_type in ["ctf_challenge"]:
            suggested_category = "htb"
        else:
            suggested_category = "custom"
        
        simple_categories = {
            "recon": "Reconnaissance (network discovery)",
            "custom": "Custom (general security tools)", 
            "htb": "CTF/HTB (capture the flag challenges)"
        }
        
        choice, category = self._ask_multiple_choice(
            "Where should we save your template?",
            list(simple_categories.keys()),
            list(simple_categories.values()),
            "Choose the folder that best matches your template's purpose."
        )
        
        return self._save_template(category)

    def step7_finalize_and_save(self) -> bool:
        """Step 7: Finalize and save template (for intermediate/advanced)."""
        self.current_step = 11
        
        # Show final template summary
        summary_items = [
            Text("🎯 Template Summary", style=f"bold {self.colors['header']}"),
            Text(""),
            Text(f"Name: {self.template_data.get('name', 'Unnamed')}", style="white"),
            Text(f"Tool: {self.template_data.get('tool', 'Unknown')}", style="white"),
            Text(f"Assessment: {self.assessment_types[self.assessment_type]['name']}", style="white"),
        ]
        
        if self.template_data.get('preset'):
            summary_items.append(Text(f"Preset: {self.template_data['preset']}", style=self.colors['accent']))
        
        # Show chain information if it's a chain template
        if self.template_data.get('chain_template'):
            summary_items.append(Text(f"🔗 Chain Template: {len(self.template_data.get('chain_steps', []))} steps", style=self.colors['accent']))
            tool_chain = " → ".join([step["tool"] for step in self.template_data.get("chain_steps", [])])
            summary_items.append(Text(f"Workflow: {tool_chain}", style=self.colors['info']))
            
            if self.template_data.get('workflow_pattern'):
                summary_items.append(Text(f"Pattern: {self.template_data['workflow_pattern']}", style=self.colors['info']))
        
        summary_items.extend([
            Text(""),
            Text("💾 Ready to save this template?", style=f"bold {self.colors['success']}")
        ])
        
        question_panel = Panel(
            Group(*summary_items),
            title="✅ Final Review",
            title_align="left",
            box=ROUNDED,
            border_style=self.colors['success'],
            padding=(1, 2)
        )
        
        # Update layout for final review
        self._update_display(question_panel)
        
        save_template = self._ask_yes_no(
            "Save this template?",
            "The template will be saved and ready to use immediately.",
            default=True
        )
        
        if not save_template:
            return False
        
        # Category selection
        categories = ["default", "recon", "custom", "htb"]
        category_descriptions = [
            "Basic templates for simple tasks",
            "Reconnaissance and discovery templates", 
            "Custom security templates",
            "CTF and HTB optimized templates"
        ]
        
        choice, category = self._ask_multiple_choice(
            "Choose template category:",
            categories,
            category_descriptions
        )
        
        return self._save_template(category)
    
    def _save_template(self, category: str) -> bool:
        """Save the template with validation."""
        try:
            # Clean up template data
            if "_metadata" in self.template_data:
                del self.template_data["_metadata"]
            if "template_complexity" in self.template_data:
                del self.template_data["template_complexity"]
            
            # Validate template
            try:
                TemplateSchema.validate_template(self.template_data)
            except Exception as validation_error:
                self.console.print(f"[{self.colors['error']}]❌ Template validation failed:[/]")
                self.console.print(f"[{self.colors['error']}]{validation_error}[/]")
                return False
            
            # Create directory and save
            template_dir = Path("templates") / category
            template_dir.mkdir(parents=True, exist_ok=True)
            
            template_name = self.template_data["name"]
            filename = f"{template_name}.json"
            filepath = template_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(self.template_data, f, indent=2)
            
            # Success message
            self.console.print(f"\n[{self.colors['success']}]🎉 Template created successfully![/]")
            self.console.print(f"[{self.colors['info']}]📁 Saved to: {filepath}[/]")
            self.console.print(f"[{self.colors['info']}]📂 Category: {category}[/]")
            
            # Usage examples
            self.console.print(f"\n[{self.colors['accent']}]🚀 Ready to use! Try these commands:[/]")
            example_target = "target.com"
            usage_examples = [
                f"python ipcrawler.py run {category}/{template_name} {example_target}",
                f"python ipcrawler.py -{category} {example_target}",
                f"python ipcrawler.py list --category {category}"
            ]
            
            for example in usage_examples:
                self.console.print(f"[white]  {example}[/]")
            
            return True
            
        except Exception as e:
            self.console.print(f"[{self.colors['error']}]❌ Failed to save template: {e}[/]")
            return False
    
    def run(self) -> bool:
        """Run the unified wizard with proper Rich patterns."""
        try:
            # Welcome message (outside Live context)
            welcome_panel = Panel(
                Text.assemble(
                    Text("🧙 Enhanced IPCrawler Template Wizard", style=f"bold {self.colors['header']}"),
                    "\n\n",
                    Text("✨ Create professional security templates without coding!", style=self.colors['info']),
                    "\n",
                    Text("🎯 Intelligent defaults • Smart tool selection • Expert guidance", style=self.colors['accent']),
                    "\n\n",
                    Text("🔧 Perfect for beginners and experts alike", style=self.colors['info']),
                    "\n",
                    Text("🚀 Get from idea to working template in minutes", style=self.colors['success']),
                    "\n\n",
                    Text("💡 Press Ctrl+C at any time to cancel.", style=self.colors['warning'])
                ),
                title="🎯 Enhanced Template Creation Wizard",
                title_align="center",
                box=ROUNDED,
                border_style=self.colors['accent'],
                padding=(2, 4)
            )
            
            self.console.print(Align.center(welcome_panel))
            self.console.print()
            
            try:
                if not Confirm.ask(f"[{self.colors['accent']}]➤ Ready to create an awesome security template?[/]", default=True, console=self.console):
                    return False
            except KeyboardInterrupt:
                self.console.print(f"\n[{self.colors['warning']}]⚠️  Wizard cancelled by user[/]")
                return False
            
            # Run wizard steps WITHOUT Live context to ensure input visibility
            self.step1_experience_level()
            self.step2_assessment_type()
            
            if self.user_experience_level == "beginner":
                # Super simplified flow for beginners
                self.step3_beginner_simple_config()
                return self.step4_beginner_save()
            else:
                # Full flow for intermediate/advanced users
                self.step3_basic_template_info()
                self.step4_tool_selection()
                self.step5_chain_template_options()
                self.step6_advanced_options()
                return self.step7_finalize_and_save()
            
        except KeyboardInterrupt:
            self.console.print(f"\n\n[{self.colors['warning']}]⚠️  Wizard cancelled by user[/]")
            return False
        except Exception as e:
            self.console.print(f"\n\n[{self.colors['error']}]❌ Wizard error: {e}[/]")
            return False