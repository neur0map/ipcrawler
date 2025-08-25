use crate::dashboard::metrics;
use crate::ui::events::UiEvent;
use std::time::Duration;
use tokio::sync::mpsc;

pub fn start_system_stats_task(
    ui_sender: mpsc::UnboundedSender<UiEvent>,
) -> tokio::task::JoinHandle<()> {
    tokio::spawn(async move {
        let mut interval = tokio::time::interval(Duration::from_secs(1));

        loop {
            interval.tick().await;

            if let Ok((cpu, mem)) = metrics::get_system_stats() {
                let _ = ui_sender.send(UiEvent::SystemStats {
                    cpu_percent: cpu,
                    memory_used_gb: mem,
                });
            }
        }
    })
}
