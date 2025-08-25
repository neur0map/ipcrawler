#!/usr/bin/env rust-script
//! Debug UI system to understand what's happening
//! 
//! ```cargo
//! [dependencies]
//! tokio = { version = "1", features = ["full"] }
//! indicatif = "0.17"
//! ```

use indicatif::{MultiProgress, ProgressBar, ProgressStyle};
use std::time::Duration;
use tokio::time::sleep;

#[tokio::main]
async fn main() {
    println!("Testing indicatif progress bars directly...");
    
    let mp = MultiProgress::new();
    
    let main_bar = mp.add(ProgressBar::new(4));
    main_bar.set_style(
        ProgressStyle::default_bar()
            .template("┌─ {msg} [{wide_bar:.cyan/blue}] {percent}% │ {pos}/{len} tasks │ {elapsed_precise}")
            .unwrap()
            .progress_chars("█▉▊▋▌▍▎▏ ")
    );
    main_bar.set_message("test.target");
    
    let system_bar = mp.add(ProgressBar::new_spinner());
    system_bar.set_style(
        ProgressStyle::default_spinner()
            .template("└─ System: CPU:10.0% RAM:12.0GB/18.0GB FD:0/1024")
            .unwrap()
    );
    
    let task_bar = mp.add(ProgressBar::new_spinner());
    task_bar.set_style(
        ProgressStyle::default_spinner()
            .template("└─ {spinner:.green} {msg}")
            .unwrap()
            .tick_chars("⠁⠂⠄⡀⢀⠠⠐⠈")
    );
    task_bar.enable_steady_tick(Duration::from_millis(100));
    task_bar.set_message("nmap_portscan(0.0s) - scanning");
    
    println!("Starting progress display...");
    
    for i in 0..40 {
        let elapsed = i as f32 / 10.0;
        task_bar.set_message(format!("nmap_portscan({:.1}s) - scanning", elapsed));
        
        if i == 10 {
            main_bar.inc(1);
            println!("Progress: 1/4 tasks complete");
        }
        if i == 20 {
            main_bar.inc(1);
            println!("Progress: 2/4 tasks complete");
        }
        if i == 30 {
            main_bar.inc(1);
            println!("Progress: 3/4 tasks complete");
        }
        
        sleep(Duration::from_millis(100)).await;
    }
    
    task_bar.finish_with_message("nmap_portscan completed");
    main_bar.inc(1);
    main_bar.finish_with_message("All tasks complete");
    system_bar.finish_and_clear();
    
    println!("Progress display test complete!");
}