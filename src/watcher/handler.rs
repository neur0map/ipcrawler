use anyhow::Result;
use notify::{EventKind, RecursiveMode, Watcher};
use notify_debouncer_full::{new_debouncer, DebounceEventResult};
use std::path::Path;
use std::time::Duration;
use tokio::sync::mpsc;

pub struct FileWatcher {
    pub rx: mpsc::Receiver<Vec<std::path::PathBuf>>,
}

impl FileWatcher {
    pub fn new(watch_path: &Path) -> Result<Self> {
        let (tx, rx) = mpsc::channel(100);
        let watch_path = watch_path.to_path_buf();
        
        std::thread::spawn(move || {
            let rt = tokio::runtime::Runtime::new().unwrap();
            let tx_clone = tx.clone();
            
            let mut debouncer = new_debouncer(
                Duration::from_secs(2),
                None,
                move |result: DebounceEventResult| {
                    match result {
                        Ok(events) => {
                            let paths: Vec<_> = events
                                .iter()
                                .filter(|e| matches!(
                                    e.event.kind,
                                    EventKind::Create(_) | EventKind::Modify(_)
                                ))
                                .flat_map(|e| e.event.paths.clone())
                                .filter(|p| p.is_file())
                                .collect();
                            
                            if !paths.is_empty() {
                                let tx = tx_clone.clone();
                                rt.block_on(async move {
                                    let _ = tx.send(paths).await;
                                });
                            }
                        }
                        Err(e) => {
                            tracing::error!("File watcher error: {:?}", e);
                        }
                    }
                },
            ).expect("Failed to create file watcher");
            
            debouncer
                .watcher()
                .watch(&watch_path, RecursiveMode::Recursive)
                .expect("Failed to watch path");
            
            tracing::info!("File watcher started on: {}", watch_path.display());
            
            loop {
                std::thread::sleep(Duration::from_secs(1));
            }
        });
        
        Ok(Self { rx })
    }
    
    pub async fn next(&mut self) -> Option<Vec<std::path::PathBuf>> {
        self.rx.recv().await
    }
}
