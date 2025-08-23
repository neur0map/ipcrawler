use colored::Colorize;

/// Convert HSL to RGB color space
/// H: 0.0-360.0 (hue), S: 0.0-1.0 (saturation), L: 0.0-1.0 (lightness)
/// Returns (r, g, b) as u8 values (0-255)
fn hsl_to_rgb(h: f32, s: f32, l: f32) -> (u8, u8, u8) {
    let h = h % 360.0;
    let c = (1.0 - (2.0 * l - 1.0).abs()) * s;
    let x = c * (1.0 - ((h / 60.0) % 2.0 - 1.0).abs());
    let m = l - c / 2.0;

    let (r, g, b) = if h < 60.0 {
        (c, x, 0.0)
    } else if h < 120.0 {
        (x, c, 0.0)
    } else if h < 180.0 {
        (0.0, c, x)
    } else if h < 240.0 {
        (0.0, x, c)
    } else if h < 300.0 {
        (x, 0.0, c)
    } else {
        (c, 0.0, x)
    };

    (
        ((r + m) * 255.0) as u8,
        ((g + m) * 255.0) as u8,
        ((b + m) * 255.0) as u8,
    )
}

/// Apply a gradient color to text, with each character getting a slightly different hue
///
/// # Arguments
/// * `text` - The text to colorize
/// * `start_hue` - Starting hue value (0.0-360.0)
/// * `hue_range` - How much the hue should change across the text (default: 60.0 degrees)
///
/// # Example
/// ```rust
/// let colored = gradient_text("22,80,443", 0.0, 120.0);
/// println!("{}", colored);
/// ```
pub fn gradient_text(text: &str, start_hue: f32, hue_range: f32) -> String {
    if text.is_empty() {
        return String::new();
    }

    // Check if colors are disabled
    if std::env::var("NO_COLOR").is_ok() || !colored::control::SHOULD_COLORIZE.should_colorize() {
        return text.to_string();
    }

    let chars: Vec<char> = text.chars().collect();
    let char_count = chars.len();

    if char_count == 1 {
        // Single character, just use start hue
        let (r, g, b) = hsl_to_rgb(start_hue, 0.8, 0.6);
        return format!("{}", chars[0].to_string().truecolor(r, g, b));
    }

    let mut result = String::new();

    for (i, ch) in chars.iter().enumerate() {
        // Calculate hue for this character
        let progress = i as f32 / (char_count - 1) as f32;
        let hue = start_hue + (progress * hue_range);

        // Convert to RGB with nice saturation and lightness
        let (r, g, b) = hsl_to_rgb(hue, 0.8, 0.6);

        // Apply color to character
        let colored_char = ch.to_string().truecolor(r, g, b);
        result.push_str(&colored_char.to_string());
    }

    result
}

/// Apply gradient specifically optimized for port lists (comma-separated numbers)
/// Uses a pleasing color range that works well for network port displays with randomness
pub fn gradient_ports(port_text: &str) -> String {
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};

    // Generate random start hue based on port text content for consistency within scan
    let mut hasher = DefaultHasher::new();
    port_text.hash(&mut hasher);
    let hash = hasher.finish();
    let start_hue = (hash % 360) as f32;

    gradient_text(port_text, start_hue, 120.0) // Random start with good range
}

/// Apply gradient specifically for service names
/// Uses warm colors that work well for service identification
#[allow(dead_code)]
pub fn gradient_services(service_text: &str) -> String {
    gradient_text(service_text, 30.0, 90.0) // Orange to yellow-green range
}

/// Apply a rainbow gradient across the full spectrum
/// Good for longer text or when you want maximum color variation
#[allow(dead_code)]
pub fn rainbow_gradient(text: &str) -> String {
    gradient_text(text, 0.0, 300.0) // Nearly full spectrum
}

/// Apply gradient to tool names with random colors per scan
pub fn gradient_tool(tool_name: &str) -> String {
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};

    // Generate consistent random start hue for this tool name
    let mut hasher = DefaultHasher::new();
    tool_name.hash(&mut hasher);
    let hash = hasher.finish();
    let start_hue = (hash % 360) as f32;

    gradient_text(tool_name, start_hue, 80.0) // Tool names get moderate range
}

/// Apply gradient to file paths with random colors
pub fn gradient_path(path: &str) -> String {
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};

    // Generate consistent random start hue for this path
    let mut hasher = DefaultHasher::new();
    path.hash(&mut hasher);
    let hash = hasher.finish();
    let start_hue = (hash % 360) as f32;

    gradient_text(path, start_hue, 100.0) // Paths get wider range
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hsl_to_rgb() {
        // Test pure red
        let (r, g, b) = hsl_to_rgb(0.0, 1.0, 0.5);
        assert_eq!((r, g, b), (255, 0, 0));

        // Test pure green
        let (r, g, b) = hsl_to_rgb(120.0, 1.0, 0.5);
        assert_eq!((r, g, b), (0, 255, 0));

        // Test pure blue
        let (r, g, b) = hsl_to_rgb(240.0, 1.0, 0.5);
        assert_eq!((r, g, b), (0, 0, 255));
    }

    #[test]
    fn test_gradient_text_empty() {
        assert_eq!(gradient_text("", 0.0, 60.0), "");
    }

    #[test]
    fn test_gradient_text_single_char() {
        // Should not panic and should return some colored version
        let result = gradient_text("A", 0.0, 60.0);
        assert!(!result.is_empty());
    }

    #[test]
    fn test_gradient_ports() {
        let result = gradient_ports("22,80,443");
        assert!(!result.is_empty());
        // Should contain the original text content (though colored)
        assert!(result.contains("2") && result.contains("8") && result.contains("4"));
    }
}
