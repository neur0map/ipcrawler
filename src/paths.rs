use directories::ProjectDirs;
use std::path::{Path, PathBuf};
use std::fs;

#[derive(Debug)]
pub struct ReconPaths {
    pub system_templates: PathBuf,
    pub user_config: PathBuf,
    pub user_data: PathBuf,
    pub working_dir: PathBuf,
}

impl ReconPaths {
    pub fn new() -> Result<Self, Box<dyn std::error::Error>> {
        let proj_dirs = ProjectDirs::from("io", "recon-tool", "recon-tool")
            .ok_or("Failed to determine user directories")?;
            
        Ok(Self {
            system_templates: Self::get_system_templates_dir(),
            user_config: proj_dirs.config_dir().to_path_buf(),
            user_data: proj_dirs.data_dir().to_path_buf(),
            working_dir: std::env::current_dir()?,
        })
    }
    
    fn get_system_templates_dir() -> PathBuf {
        // Try different standard locations based on OS
        let candidates = vec![
            PathBuf::from("/usr/local/share/recon-tool"),
            PathBuf::from("/usr/share/recon-tool"),
            PathBuf::from("/opt/recon-tool/share"),
        ];
        
        for candidate in candidates {
            if candidate.exists() {
                return candidate;
            }
        }
        
        // Fallback to development directory if no system installation
        std::env::current_dir()
            .unwrap_or_default()
            .join("config")
    }
    
    pub fn resolve_config(&self, name_or_path: &str) -> Result<PathBuf, String> {
        // If it's already a file path (contains / or \), use as-is
        if name_or_path.contains('/') || name_or_path.contains('\\') {
            let mut path = PathBuf::from(name_or_path);
            
            // If no extension, try adding .yaml
            if path.extension().is_none() {
                path.set_extension("yaml");
            }
            
            if path.exists() {
                return Ok(path);
            } else {
                // Also try without extension in case user provided full path
                let path_without_ext = PathBuf::from(name_or_path);
                if path_without_ext.exists() {
                    return Ok(path_without_ext);
                }
                return Err(format!("Config file not found: {} (tried with and without .yaml extension)", name_or_path));
            }
        }
        
        // Otherwise, resolve as profile name
        let candidates = vec![
            // 1. Working directory
            self.working_dir.join(format!("{}.yaml", name_or_path)),
            self.working_dir.join("recon-tool.yaml"), // Project default
            
            // 2. User config directory  
            self.user_config.join(format!("{}.yaml", name_or_path)),
            self.user_config.join("profiles").join(format!("{}.yaml", name_or_path)),
            self.user_config.join("config.yaml"), // User default
            
            // 3. System templates
            self.system_templates.join(format!("{}.yaml", name_or_path)),
            self.system_templates.join("templates").join(format!("{}.yaml", name_or_path)),
        ];
        
        
        for candidate in candidates {
            if candidate.exists() {
                return Ok(candidate);
            }
        }
        
        Err(format!("Config profile '{}' not found in any location", name_or_path))
    }
    
    pub fn default_output_dir(&self) -> PathBuf {
        // In production (when binary is installed system-wide), use user data directory
        // In development (when running from project), use project directory
        if self.working_dir.join("Cargo.toml").exists() {
            // Development mode - project directory
            self.working_dir.join("recon-results")
        } else {
            // Production mode - user data directory
            self.user_data.join("results")
        }
    }
    
    pub fn production_output_dir(&self) -> PathBuf {
        self.user_data.join("results")
    }
    
    pub fn development_output_dir(&self) -> PathBuf {
        self.working_dir.join("recon-results")
    }
    
    pub fn ensure_user_dirs(&self) -> Result<(), Box<dyn std::error::Error>> {
        fs::create_dir_all(&self.user_config)?;
        fs::create_dir_all(self.user_config.join("profiles"))?;
        fs::create_dir_all(&self.user_data)?;
        fs::create_dir_all(self.user_data.join("results"))?;
        Ok(())
    }
    
    pub fn list_available_configs(&self) -> Vec<(String, PathBuf)> {
        let mut configs = Vec::new();
        
        // Scan working directory
        self.scan_directory(&self.working_dir, "Working Directory", &mut configs);
        
        // Scan user config directory
        self.scan_directory(&self.user_config, "User Config", &mut configs);
        self.scan_directory(&self.user_config.join("profiles"), "User Profiles", &mut configs);
        
        // Scan system templates
        self.scan_directory(&self.system_templates, "System Templates", &mut configs);
        self.scan_directory(&self.system_templates.join("templates"), "System Templates", &mut configs);
        
        configs
    }
    
    fn scan_directory(&self, dir: &Path, source: &str, configs: &mut Vec<(String, PathBuf)>) {
        if let Ok(entries) = fs::read_dir(dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.extension().map_or(false, |ext| ext == "yaml" || ext == "yml") {
                    if let Some(name) = path.file_stem().and_then(|s| s.to_str()) {
                        configs.push((format!("{} ({})", name, source), path));
                    }
                }
            }
        }
    }
    
    pub fn get_config_info(&self) -> String {
        format!(
            "Configuration Locations:\n\
             • Working Directory: {}\n\
             • User Config: {}\n\
             • User Data: {}\n\
             • System Templates: {}",
            self.working_dir.display(),
            self.user_config.display(),
            self.user_data.display(),
            self.system_templates.display()
        )
    }
}