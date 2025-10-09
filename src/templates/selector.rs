use super::models::Template;
use tracing::{debug, info};

pub struct TemplateSelector {
    is_sudo: bool,
}

impl TemplateSelector {
    pub fn new() -> Self {
        let is_sudo = Self::check_sudo();
        if is_sudo {
            info!("Running with elevated privileges (sudo)");
        } else {
            info!("Running with normal privileges");
        }
        Self { is_sudo }
    }

    #[cfg(unix)]
    fn check_sudo() -> bool {
        unsafe { libc::geteuid() == 0 }
    }

    #[cfg(not(unix))]
    fn check_sudo() -> bool {
        false
    }

    pub fn select_templates(&self, all_templates: Vec<Template>) -> Vec<Template> {
        let mut selected = Vec::new();

        for template in &all_templates {
            if !template.is_enabled() {
                debug!("Skipping disabled template: {}", template.name);
                continue;
            }

            if template.requires_sudo() && !self.is_running_as_root() {
                debug!(
                    "Skipping template '{}' (requires sudo, but not running as root)",
                    template.name
                );
                continue;
            }

            let template_name = &template.name;

            if self.is_running_as_root() && template_name.ends_with("-sudo") {
                selected.push(template.clone());
            } else if self.is_running_as_root() && !template_name.ends_with("-sudo") {
                let sudo_variant_exists = all_templates
                    .iter()
                    .any(|t| t.name == format!("{}-sudo", template_name) && t.is_enabled());

                if !sudo_variant_exists {
                    selected.push(template.clone());
                }
            } else if !self.is_running_as_root() && !template_name.ends_with("-sudo") {
                selected.push(template.clone());
            }
        }

        info!("Selected {} templates to execute", selected.len());
        selected
    }

    pub fn is_running_as_root(&self) -> bool {
        self.is_sudo
    }
}
