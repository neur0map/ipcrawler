mod app;
mod cli;
mod config;
mod core;
mod executors;
// mod monitoring;  // Disabled - replaced by ui::progress system
mod organizers;
mod plugins;
mod reporters;
mod ui;
mod utils;

use clap::Parser;

#[tokio::main]
async fn main() {
    let cli = cli::args::Cli::parse();
    if let Err(err) = app::run(cli).await {
        eprintln!("fatal: {:#}", err);
        std::process::exit(1);
    }
}
