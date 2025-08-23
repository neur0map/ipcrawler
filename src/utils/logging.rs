use anyhow::Result;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

pub fn level_from_cli(cli: &crate::cli::args::Cli) -> tracing::Level {
    if cli.debug {
        tracing::Level::DEBUG
    } else if cli.verbose {
        tracing::Level::INFO
    } else {
        tracing::Level::WARN
    }
}

pub fn init(level: tracing::Level) -> Result<()> {
    let filter = EnvFilter::from_default_env()
        .add_directive(format!("ipcrawler={}", level).parse()?)
        .add_directive(level.into());

    tracing_subscriber::registry()
        .with(filter)
        .with(tracing_subscriber::fmt::layer()
            .compact()
            .with_target(false)
            .with_thread_ids(false)
            .with_thread_names(false))
        .try_init()
        .map_err(|e| anyhow::anyhow!("Failed to initialize logging: {}", e))?;
    
    Ok(())
}