use crate::core::{models::RunDirs, state::RunState};
use crate::utils::fs::atomic_write;
use anyhow::Result;
use minijinja::{context, Environment};
use serde_json;
use std::fs;

pub fn write_all(state: &RunState, dirs: &RunDirs, start_time: std::time::Instant) -> Result<()> {
    write_text_summary(state, dirs, start_time)?;
    write_markdown_summary(state, dirs, start_time)?;
    write_json_summary(state, dirs)?;
    Ok(())
}

fn write_text_summary(
    state: &RunState,
    dirs: &RunDirs,
    start_time: std::time::Instant,
) -> Result<()> {
    let env = Environment::new();

    // Load template from file
    let template_path = std::path::Path::new("report_templates/summary.txt.j2");
    let template_content = fs::read_to_string(template_path)?;
    let template = env.template_from_str(&template_content)?;

    let duration = start_time.elapsed();
    let scan_date = chrono::Utc::now()
        .format("%Y-%m-%d %H:%M:%S UTC")
        .to_string();

    let rendered = template.render(context! {
        target => &state.target,
        run_id => &state.run_id,
        duration_seconds => duration.as_secs(),
        scan_date => scan_date,
        ports_open => &state.ports_open,
        services => &state.services,
        tasks_started => state.tasks_started,
        tasks_completed => state.tasks_completed,
        errors => &state.errors,
        plugin_findings => &state.plugin_findings,
        scans_dir => dirs.scans.display().to_string(),
        report_dir => dirs.report.display().to_string(),
        version => env!("CARGO_PKG_VERSION")
    })?;

    let path = dirs.report.join("summary.txt");
    atomic_write(path, rendered.as_bytes())?;
    Ok(())
}

fn write_markdown_summary(
    state: &RunState,
    dirs: &RunDirs,
    start_time: std::time::Instant,
) -> Result<()> {
    let env = Environment::new();

    // Load template from file
    let template_path = std::path::Path::new("report_templates/summary.md.j2");
    let template_content = fs::read_to_string(template_path)?;
    let template = env.template_from_str(&template_content)?;

    let duration = start_time.elapsed();
    let scan_date = chrono::Utc::now()
        .format("%Y-%m-%d %H:%M:%S UTC")
        .to_string();

    let rendered = template.render(context! {
        target => &state.target,
        run_id => &state.run_id,
        duration_seconds => duration.as_secs(),
        scan_date => scan_date,
        ports_open => &state.ports_open,
        services => &state.services,
        tasks_started => state.tasks_started,
        tasks_completed => state.tasks_completed,
        errors => &state.errors,
        plugin_findings => &state.plugin_findings,
        scans_dir => dirs.scans.display().to_string(),
        report_dir => dirs.report.display().to_string(),
        version => env!("CARGO_PKG_VERSION")
    })?;

    let path = dirs.report.join("summary.md");
    atomic_write(path, rendered.as_bytes())?;
    Ok(())
}

fn write_json_summary(state: &RunState, dirs: &RunDirs) -> Result<()> {
    let path = dirs.report.join("summary.json");
    let json = serde_json::to_string_pretty(state)?;
    atomic_write(path, json.as_bytes())?;
    Ok(())
}
