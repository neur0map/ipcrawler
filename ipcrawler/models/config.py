"""
Enhanced application configuration models for multi-file support.
"""

from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field, validator
from pathlib import Path
import toml


def _get_config_version() -> str:
    """Get version from config.toml if it exists."""
    try:
        config_path = Path("config.toml")
        if config_path.exists():
            with open(config_path, 'r') as f:
                config_data = toml.load(f)
                return config_data.get("application", {}).get("version", "2.0.0")
    except Exception:
        pass
    return "2.0.0"


# =============================================================================
# CORE APPLICATION MODELS
# =============================================================================

class ApplicationConfig(BaseModel):
    """Application metadata configuration."""
    name: str = "ipcrawler"
    version: str = Field(default_factory=_get_config_version)
    debug: bool = False
    environment: str = "production"


class PerformanceConfig(BaseModel):
    """Performance and resource configuration."""
    concurrent_limit: int = Field(10, ge=1, le=100)
    default_timeout: int = Field(60, ge=1, le=300)
    max_output_size: int = Field(1024 * 1024, ge=1024, le=100 * 1024 * 1024)
    memory_limit: int = Field(512, ge=64, le=8192)  # MB


class SecurityCoreConfig(BaseModel):
    """Core security configuration."""
    enforce_validation: bool = True
    allow_shell_commands: bool = False
    max_template_size: int = Field(1024 * 1024, ge=1024, le=10 * 1024 * 1024)


class SystemConfig(BaseModel):
    """System paths and directories."""
    config_dir: str = "configs"
    templates_dir: str = "templates"
    results_dir: str = "results"
    cache_dir: str = ".cache"


class LoggingConfig(BaseModel):
    """Enhanced logging configuration."""
    silent: bool = True
    level: str = Field("INFO", pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    file_rotation: bool = True
    max_log_size: int = Field(10 * 1024 * 1024, ge=1024)  # 10MB


class RetryConfig(BaseModel):
    """Retry configuration."""
    count: int = Field(3, ge=1, le=10)
    backoff_multiplier: float = Field(2.0, ge=0.1, le=10.0)
    max_wait_time: int = Field(60, ge=1, le=300)


# =============================================================================
# TEMPLATES CONFIGURATION MODELS
# =============================================================================

class TemplatesMetadataConfig(BaseModel):
    """Template discovery and caching settings."""
    scan_depth: int = Field(3, ge=1, le=10)
    auto_discover: bool = True
    cache_templates: bool = True
    refresh_cache_hours: int = Field(24, ge=1, le=168)


class TemplatesFilterConfig(BaseModel):
    """Template filtering options."""
    exclude_patterns: List[str] = Field(default_factory=lambda: ["*test*", "*.backup"])
    include_tags: List[str] = Field(default_factory=list)
    exclude_tags: List[str] = Field(default_factory=lambda: ["experimental", "broken"])
    min_quality_score: int = Field(7, ge=1, le=10)
    max_timeout: int = Field(300, ge=1, le=3600)


class TemplatesValidationConfig(BaseModel):
    """Template validation rules."""
    require_description: bool = True
    require_tags: bool = True
    require_author: bool = False
    validate_syntax: bool = True
    validate_security: bool = True
    allowed_tools: List[str] = Field(default_factory=lambda: [
        "nmap", "curl", "dig", "nuclei", "feroxbuster", "gobuster",
        "ping", "echo", "openssl", "nslookup"
    ])
    blocked_tools: List[str] = Field(default_factory=lambda: ["rm", "del", "format"])


class TemplatesOrganizationConfig(BaseModel):
    """Template organization preferences."""
    group_by_tool: bool = False
    group_by_category: bool = True
    auto_categorize: bool = True
    show_hidden: bool = False
    sort_by: str = Field("name", pattern=r"^(name|date|author|quality)$")


class TemplatesDisplayConfig(BaseModel):
    """Template display settings."""
    show_descriptions: bool = True
    show_tags: bool = True
    show_author: bool = False
    show_timeout: bool = True
    truncate_description: int = Field(100, ge=20, le=500)


class TemplatesDefaultsConfig(BaseModel):
    """Default values for new templates."""
    default_timeout: int = Field(60, ge=1, le=300)
    default_tags: List[str] = Field(default_factory=lambda: ["custom"])
    default_parallel_safe: bool = True


class TemplatesConfig(BaseModel):
    """Complete templates configuration."""
    categories: Dict[str, str] = Field(default_factory=dict)
    metadata: TemplatesMetadataConfig = Field(default_factory=TemplatesMetadataConfig)
    filters: TemplatesFilterConfig = Field(default_factory=TemplatesFilterConfig)
    validation: TemplatesValidationConfig = Field(default_factory=TemplatesValidationConfig)
    organization: TemplatesOrganizationConfig = Field(default_factory=TemplatesOrganizationConfig)
    display: TemplatesDisplayConfig = Field(default_factory=TemplatesDisplayConfig)
    defaults: TemplatesDefaultsConfig = Field(default_factory=TemplatesDefaultsConfig)


# =============================================================================
# PRESETS CONFIGURATION MODELS
# =============================================================================

class PresetsConfig(BaseModel):
    """Tool presets configuration."""
    global_presets: Dict[str, List[str]] = Field(default_factory=dict, alias="global")
    tool_presets: Dict[str, Dict[str, List[str]]] = Field(default_factory=dict)
    
    class Config:
        validate_by_name = True
    
    @validator('global_presets', 'tool_presets')
    def validate_presets(cls, v):
        """Validate preset structure."""
        if isinstance(v, dict):
            for preset_name, args in v.items():
                if isinstance(args, dict):
                    # Tool presets (nested)
                    for sub_preset_name, sub_args in args.items():
                        if not isinstance(sub_args, list):
                            raise ValueError(f'Preset args must be list: {preset_name}.{sub_preset_name}')
                elif not isinstance(args, list):
                    raise ValueError(f'Preset args must be list: {preset_name}')
        return v


# =============================================================================
# WORKFLOWS CONFIGURATION MODELS  
# =============================================================================

class WorkflowStep(BaseModel):
    """Individual workflow step."""
    template: str
    condition: str = "always"
    priority: int = Field(1, ge=1, le=10)
    timeout: Optional[int] = None
    retry_count: Optional[int] = None


class WorkflowSequence(BaseModel):
    """Workflow sequence definition."""
    name: str
    description: str
    enabled: bool = False
    parallel: bool = True
    steps: List[WorkflowStep]


class WorkflowTriggers(BaseModel):
    """Workflow trigger patterns."""
    web_technologies: Dict[str, List[str]] = Field(default_factory=dict)
    services: Dict[str, Dict[str, Union[List[int], List[str]]]] = Field(default_factory=dict)


class WorkflowAutomation(BaseModel):
    """Workflow automation settings."""
    auto_trigger: bool = False
    max_depth: int = Field(3, ge=1, le=10)
    parallel_workflows: bool = True
    smart_scheduling: bool = True
    respect_rate_limits: bool = True
    timeout_per_workflow: int = Field(1800, ge=60, le=7200)


class WorkflowsConfig(BaseModel):
    """Complete workflows configuration."""
    triggers: WorkflowTriggers = Field(default_factory=WorkflowTriggers)
    sequences: Dict[str, WorkflowSequence] = Field(default_factory=dict)
    automation: WorkflowAutomation = Field(default_factory=WorkflowAutomation)
    conditions: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


# =============================================================================
# SECURITY CONFIGURATION MODELS
# =============================================================================

class SecurityValidationConfig(BaseModel):
    """Security validation settings."""
    max_arg_length: int = Field(1000, ge=100, le=10000)
    max_args_count: int = Field(50, ge=1, le=200)
    max_template_size: int = Field(1024 * 1024, ge=1024)
    max_target_length: int = Field(500, ge=50, le=2000)
    dangerous_patterns: List[str] = Field(default_factory=lambda: [
        "[;&|`$()]", "\\.\\./", "[<>]", "\\$\\(", "`", "&&", "\\|\\|", ";"
    ])
    whitelist_mode: bool = False
    validate_all_inputs: bool = True
    sanitize_inputs: bool = True
    escape_special_chars: bool = True


class SecurityExecutionConfig(BaseModel):
    """Security execution settings."""
    allow_shell_execution: bool = False
    sandbox_mode: bool = True
    resource_limits: bool = True
    network_restrictions: bool = False
    chroot_jail: bool = False
    max_execution_time: int = Field(300, ge=30, le=3600)
    max_memory_usage: int = Field(512, ge=64, le=4096)
    max_file_descriptors: int = Field(100, ge=10, le=1000)
    max_subprocess_count: int = Field(10, ge=1, le=100)
    allowed_tools: List[str] = Field(default_factory=lambda: [
        "nmap", "curl", "dig", "nuclei", "feroxbuster", "gobuster"
    ])
    blocked_tools: List[str] = Field(default_factory=lambda: [
        "rm", "del", "shutdown", "reboot", "su", "sudo"
    ])


class SecurityMonitoringConfig(BaseModel):
    """Security monitoring settings."""
    log_all_executions: bool = True
    log_failed_validations: bool = True
    log_security_events: bool = True
    detect_anomalies: bool = True
    rate_limiting: bool = True
    max_executions_per_minute: int = Field(100, ge=1, le=1000)
    max_failed_attempts: int = Field(10, ge=1, le=100)
    cooldown_period: int = Field(300, ge=60, le=3600)


class SecurityConfig(BaseModel):
    """Complete security configuration."""
    validation: SecurityValidationConfig = Field(default_factory=SecurityValidationConfig)
    execution: SecurityExecutionConfig = Field(default_factory=SecurityExecutionConfig)
    monitoring: SecurityMonitoringConfig = Field(default_factory=SecurityMonitoringConfig)


# =============================================================================
# OUTPUT CONFIGURATION MODELS
# =============================================================================

class OutputFormatsConfig(BaseModel):
    """Output format settings."""
    default_readable: str = Field("txt", pattern=r"^(txt|md|html)$")
    machine_readable: str = Field("jsonl", pattern=r"^(json|jsonl|xml|csv)$")
    export_formats: List[str] = Field(default_factory=lambda: ["txt", "md", "json", "xml", "csv"])


class OutputStorageConfig(BaseModel):
    """Output storage settings."""
    base_directory: str = "results"
    auto_compress_after_days: int = Field(30, ge=1, le=365)
    max_historical_runs: int = Field(50, ge=1, le=1000)
    compress_format: str = Field("gzip", pattern=r"^(gzip|bzip2|xz)$")
    retention_policy: str = Field("time_based", pattern=r"^(time_based|count_based|size_based)$")
    max_result_size: int = Field(100 * 1024 * 1024, ge=1024)  # 100MB
    max_total_storage: int = Field(10 * 1024 * 1024 * 1024, ge=1024 * 1024)  # 10GB


class OutputOrganizationConfig(BaseModel):
    """Output organization settings."""
    use_run_numbers: bool = True
    separate_by_date: bool = False
    group_by_target: bool = True
    create_summaries: bool = True
    timestamp_format: str = Field("ISO8601", pattern=r"^(ISO8601|UNIX|HUMAN)$")
    create_subdirectories: bool = True
    subdirectory_structure: List[str] = Field(default_factory=lambda: [
        "readable", "machine", "success", "errors"
    ])


class OutputExportConfig(BaseModel):
    """Output export settings."""
    include_metadata: bool = True
    include_timestamps: bool = True
    include_execution_time: bool = True
    include_tool_versions: bool = False
    include_environment: bool = False
    exclude_empty_results: bool = True
    exclude_failed_scans: bool = False
    min_execution_time: int = Field(0, ge=0)
    max_execution_time: int = Field(0, ge=0)
    # CTF noise filtering (for cleaner results in competitive scenarios)
    enable_ctf_filtering: bool = True
    filter_nmap_fingerprints: bool = True
    filter_submission_prompts: bool = True
    filter_version_banners: bool = False
    filter_debug_output: bool = True


class OutputConfig(BaseModel):
    """Complete output configuration."""
    formats: OutputFormatsConfig = Field(default_factory=OutputFormatsConfig)
    storage: OutputStorageConfig = Field(default_factory=OutputStorageConfig)
    organization: OutputOrganizationConfig = Field(default_factory=OutputOrganizationConfig)
    export: OutputExportConfig = Field(default_factory=OutputExportConfig)


# =============================================================================
# MAIN APPLICATION CONFIG (ENHANCED)
# =============================================================================

class EnhancedAppConfig(BaseModel):
    """Enhanced main application configuration with multi-file support."""
    application: ApplicationConfig = Field(default_factory=ApplicationConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    security: SecurityCoreConfig = Field(default_factory=SecurityCoreConfig)
    system: SystemConfig = Field(default_factory=SystemConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)


# =============================================================================
# BACKWARDS COMPATIBILITY MODELS
# =============================================================================

class LegacySettingsConfig(BaseModel):
    """Legacy settings for backwards compatibility."""
    concurrent_limit: int = Field(10, ge=1, le=100)
    default_timeout: int = Field(60, ge=1, le=300)
    max_output_size: int = Field(1024 * 1024, ge=1024, le=100 * 1024 * 1024)


class LegacyLoggingConfig(BaseModel):
    """Legacy logging configuration."""
    silent: bool = True


class LegacyRetryConfig(BaseModel):
    """Legacy retry configuration."""
    max_attempts: int = Field(3, ge=1, le=10)
    wait_multiplier: float = Field(1.0, ge=0.1, le=10.0)
    wait_max: int = Field(60, ge=1, le=300)


class UIConfig(BaseModel):
    """User interface configuration."""
    enable_rich_ui: bool = True
    fullscreen_mode: bool = False
    refresh_rate: int = Field(2, ge=1, le=60)  # 1-5 recommended for smooth time display
    theme: str = Field("minimal", pattern=r"^(minimal|dark|matrix|cyber|hacker|corporate)$")
    
    @validator('theme')
    def validate_theme(cls, v):
        """Validate theme selection."""
        valid_themes = ["minimal", "dark", "matrix", "cyber", "hacker", "corporate"]
        if v not in valid_themes:
            raise ValueError(f'Theme must be one of: {", ".join(valid_themes)}')
        return v


class WordlistConfig(BaseModel):
    """Wordlist management configuration."""
    seclists_path: str = str(Path.home() / ".local" / "share" / "seclists")
    enable_auto_selection: bool = True
    fallback_wordlist: str = "auto"
    analysis_timeout: int = Field(10, ge=1, le=60)


class AppConfig(BaseModel):
    """Main application configuration (backwards compatible)."""
    application: ApplicationConfig = Field(default_factory=ApplicationConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    security: SecurityCoreConfig = Field(default_factory=SecurityCoreConfig)
    system: SystemConfig = Field(default_factory=SystemConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    wordlists: WordlistConfig = Field(default_factory=WordlistConfig)
    templates: Dict[str, str] = Field({}, max_items=50)
    settings: LegacySettingsConfig = Field(default_factory=LegacySettingsConfig)
    logging: LegacyLoggingConfig = Field(default_factory=LegacyLoggingConfig)
    retry: LegacyRetryConfig = Field(default_factory=LegacyRetryConfig)
    presets: Optional[Dict[str, Any]] = Field(None)
    
    @validator('templates')
    def validate_templates(cls, v):
        """Validate template mappings."""
        for key, value in v.items():
            if len(key) > 50 or len(value) > 100:
                raise ValueError('Template mapping key/value too long')
            if not key.replace('_', '').replace('-', '').isalnum():
                raise ValueError(f'Invalid template key: {key}')
        return v