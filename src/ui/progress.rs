use indicatif::{MultiProgress, ProgressBar, ProgressStyle};
use std::time::Duration;

pub struct ProgressManager {
    multi: MultiProgress,
    main_bar: ProgressBar,
}

impl ProgressManager {
    pub fn new() -> Self {
        let multi = MultiProgress::new();
        let main_bar = multi.add(ProgressBar::new_spinner());
        
        main_bar.set_style(
            ProgressStyle::default_spinner()
                .template("{spinner:.green} {msg}")
                .unwrap()
                .tick_chars("⠁⠂⠄⡀⢀⠠⠐⠈ ")
        );
        
        main_bar.enable_steady_tick(Duration::from_millis(100));
        
        Self { multi, main_bar }
    }
    
    pub fn update(&self, msg: &str) {
        self.main_bar.set_message(msg.to_string());
    }
    
    pub fn finish(&self, msg: &str) {
        self.main_bar.finish_with_message(msg.to_string());
    }
}
