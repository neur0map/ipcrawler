use comfy_table::{Table, Cell, Attribute, Color, ContentArrangement};
use comfy_table::presets::UTF8_FULL;
use comfy_table::modifiers::UTF8_ROUND_CORNERS;
use crate::gradient::gradient_ports;

pub struct TableBuilder {
    table: Table,
}

impl TableBuilder {
    pub fn new() -> Self {
        let mut table = Table::new();
        table.load_preset(UTF8_FULL)
            .apply_modifier(UTF8_ROUND_CORNERS)
            .set_content_arrangement(ContentArrangement::Dynamic);
        
        Self { table }
    }
    
    pub fn discovery_summary(
        ports: &[String],
        services: &[String], 
        vulns: &[String]
    ) -> String {
        let mut builder = Self::new();
        
        builder.table.set_header(vec![
            Cell::new("Type").add_attribute(Attribute::Bold),
            Cell::new("Count").add_attribute(Attribute::Bold),
            Cell::new("Details").add_attribute(Attribute::Bold),
        ]);
        
        builder.table.add_row(vec![
            Cell::new("Ports").fg(Color::Green),
            Cell::new(ports.len().to_string()),
            Cell::new(gradient_ports(&ports.join(", "))),
        ]);
        
        builder.table.add_row(vec![
            Cell::new("Services").fg(Color::Blue),
            Cell::new(services.len().to_string()),
            Cell::new(services.join(", ")),
        ]);
        
        builder.table.add_row(vec![
            Cell::new("Vulnerabilities").fg(Color::Red),
            Cell::new(vulns.len().to_string()),
            Cell::new(vulns.join(", ")),
        ]);
        
        builder.table.to_string()
    }
    
    pub fn tool_execution_summary(results: &[crate::executor::ToolResult]) -> String {
        let mut builder = Self::new();
        
        builder.table.set_header(vec![
            Cell::new("Tool").add_attribute(Attribute::Bold),
            Cell::new("Status").add_attribute(Attribute::Bold),
            Cell::new("Duration").add_attribute(Attribute::Bold),
            Cell::new("Output Size").add_attribute(Attribute::Bold),
        ]);
        
        for result in results {
            let status_cell = if result.exit_code == 0 {
                Cell::new("✓ Success").fg(Color::Green)
            } else {
                Cell::new("✗ Failed").fg(Color::Red)
            };
            
            // Get file size if possible
            let output_size = if result.stdout_file.exists() {
                std::fs::metadata(&result.stdout_file)
                    .map(|m| m.len())
                    .unwrap_or(0)
            } else {
                0
            };
            
            builder.table.add_row(vec![
                Cell::new(&result.tool_name),
                status_cell,
                Cell::new(format!("{:.2}s", result.duration.as_secs_f64())),
                Cell::new(format!("{} bytes", output_size)),
            ]);
        }
        
        builder.table.to_string()
    }
}