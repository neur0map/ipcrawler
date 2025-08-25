use sysinfo::System;

pub fn get_system_stats() -> Result<(f32, f64), std::io::Error> {
    let mut sys = System::new_all();
    sys.refresh_all();
    
    let cpu_usage = sys.global_cpu_info().cpu_usage();
    let used_memory = sys.used_memory();
    let memory_gb = used_memory as f64 / 1_073_741_824.0; // Convert bytes to GB
    
    Ok((cpu_usage, memory_gb))
}