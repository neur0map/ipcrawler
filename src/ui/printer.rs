use crate::core::state::RunState;
use yansi::Paint;

pub fn print_summary(state: &RunState) {
    println!("\n{}", "═══════════════════════════════════════".green().bold());
    println!("{}", "ipcrawler Run Complete".green().bold());
    println!("{}", "═══════════════════════════════════════".green().bold());
    
    println!("\n{}: {}", "Target".cyan().bold(), state.target);
    println!("{}: {}", "Run ID".cyan().bold(), state.run_id);
    
    println!("\n{}", "Results:".yellow().bold());
    println!("  Open Ports: {}", state.ports_open.len().to_string().green().bold());
    println!("  Services: {}", state.services.len().to_string().green().bold());
    
    println!("\n{}", "Execution:".yellow().bold());
    println!("  Tasks: {}/{}", 
        state.tasks_completed.to_string().green().bold(),
        state.tasks_started
    );
    
    if !state.errors.is_empty() {
        println!("  Errors: {}", state.errors.len().to_string().red().bold());
    }
    
    if !state.ports_open.is_empty() {
        println!("\n{}", "Open Ports:".yellow().bold());
        for (port, service) in &state.ports_open {
            println!("  • {}: {}", port.to_string().cyan(), service);
        }
    }
    
    println!("\n{}", "Reports written to artifacts/runs/".green().dim());
}