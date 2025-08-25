mod app;
mod cli;
mod config;
mod core;
mod dashboard;
mod executors;
mod monitoring;
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
