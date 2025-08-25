use crate::core::state::RunState;
use crossterm::style::{Color, Stylize};

pub fn print_summary(state: &RunState) {
    println!(
        "\n{}",
        "═══════════════════════════════════════"
            .with(Color::Green)
            .bold()
    );
    println!("{}", "ipcrawler Run Complete".with(Color::Green).bold());
    println!(
        "{}",
        "═══════════════════════════════════════"
            .with(Color::Green)
            .bold()
    );

    println!("\n{}: {}", "Target".with(Color::Cyan).bold(), state.target);
    println!("{}: {}", "Run ID".with(Color::Cyan).bold(), state.run_id);

    println!("\n{}", "Results:".with(Color::Yellow).bold());
    println!(
        "  Open Ports: {}",
        state.ports_open.len().to_string().with(Color::Green).bold()
    );
    println!(
        "  Services: {}",
        state.services.len().to_string().with(Color::Green).bold()
    );

    println!("\n{}", "Execution:".with(Color::Yellow).bold());
    println!(
        "  Tasks: {}/{}",
        state.tasks_completed.to_string().with(Color::Green).bold(),
        state.tasks_started
    );

    if !state.errors.is_empty() {
        println!(
            "  Errors: {}",
            state.errors.len().to_string().with(Color::Red).bold()
        );
    }

    if !state.ports_open.is_empty() {
        println!("\n{}", "Open Ports:".with(Color::Yellow).bold());
        for (port, service) in &state.ports_open {
            println!("  • {}: {}", port.to_string().with(Color::Cyan), service);
        }
    }

    println!(
        "\n{}",
        "Reports written to artifacts/runs/"
            .with(Color::Green)
            .dim()
    );
}
