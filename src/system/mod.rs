pub mod detect;
pub mod script_security;

pub use detect::{
    check_tool_installed, detect_package_manager, execute_installer_command, is_running_as_root,
};
pub use script_security::ScriptSecurity;
