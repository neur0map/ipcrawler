mod app;
mod cli;
mod config;
mod core;
mod executors;
mod organizers;
mod plugins;
mod reporters;
mod ui;
mod utils;

use clap::Parser;

fn main() {
    let cli = cli::args::Cli::parse();
    if let Err(err) = app::run(cli) {
        eprintln!("fatal: {:#}", err);
        std::process::exit(1);
    }
}
