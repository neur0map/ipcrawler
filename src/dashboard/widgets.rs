use crossterm::{
    cursor::MoveTo,
    queue,
    style::{Color, Print, ResetColor, SetForegroundColor},
};
use std::io::{self, Write};

use crate::dashboard::layout::Rect;

/// Draw an enhanced box with optional title and visual flair
pub fn draw_box<W: Write>(w: &mut W, rect: &Rect, title: &str) -> io::Result<()> {
    // Enhanced corners with rounded appearance
    queue!(
        w,
        MoveTo(rect.x, rect.y),
        SetForegroundColor(Color::Cyan),
        Print("╭")
    )?;

    if !title.is_empty() && rect.width > title.len() as u16 + 6 {
        // Enhanced title styling with brackets
        queue!(
            w,
            SetForegroundColor(Color::DarkGrey),
            Print("── "),
            SetForegroundColor(Color::Green),
            Print("◦ "),
            SetForegroundColor(Color::White),
            Print(title),
            SetForegroundColor(Color::Green),
            Print(" ◦"),
            SetForegroundColor(Color::DarkGrey),
            Print(" ")
        )?;
        let remaining = rect.width - title.len() as u16 - 9;
        queue!(w, Print("─".repeat(remaining as usize)))?;
    } else {
        queue!(
            w,
            SetForegroundColor(Color::DarkGrey),
            Print("─".repeat((rect.width - 2) as usize))
        )?;
    }

    queue!(
        w,
        SetForegroundColor(Color::Cyan),
        Print("╮")
    )?;

    // Enhanced sides with subtle gradient effect
    for y in 1..rect.height - 1 {
        let side_color = if y == 1 || y == rect.height - 2 {
            Color::Cyan
        } else {
            Color::DarkGrey
        };
        
        queue!(
            w,
            MoveTo(rect.x, rect.y + y),
            SetForegroundColor(side_color),
            Print("│"),
            MoveTo(rect.x + rect.width - 1, rect.y + y),
            Print("│")
        )?;
    }

    // Enhanced bottom border with rounded corners
    queue!(
        w,
        MoveTo(rect.x, rect.y + rect.height - 1),
        SetForegroundColor(Color::Cyan),
        Print("╰"),
        SetForegroundColor(Color::DarkGrey),
        Print("─".repeat((rect.width - 2) as usize)),
        SetForegroundColor(Color::Cyan),
        Print("╯"),
        ResetColor
    )
}

/// Draw a gradient progress bar with enhanced visual appeal
pub fn draw_progress_bar<W: Write>(
    w: &mut W,
    x: u16,
    y: u16,
    width: u16,
    percent: u8,
) -> io::Result<()> {
    let filled = ((percent as f32 / 100.0) * width as f32) as u16;
    let empty = width.saturating_sub(filled);

    // Create gradient effect for filled portion
    for i in 0..filled {
        let progress_ratio = i as f32 / width.max(1) as f32;
        let color = if progress_ratio < 0.3 {
            Color::Red
        } else if progress_ratio < 0.6 {
            Color::Yellow
        } else if progress_ratio < 0.8 {
            Color::Cyan
        } else {
            Color::Green
        };

        queue!(
            w,
            MoveTo(x + i, y),
            SetForegroundColor(color),
            Print("▓"),
        )?;
    }

    // Draw empty portion with subtle styling
    if empty > 0 {
        queue!(
            w,
            MoveTo(x + filled, y),
            SetForegroundColor(Color::DarkGrey),
            Print("▒".repeat(empty as usize)),
        )?;
    }

    queue!(w, ResetColor)?;

    // Enhanced percentage display with styling
    let pct_str = format!(" {}%", percent);
    if width > pct_str.len() as u16 + 2 {
        let pct_color = if percent >= 100 {
            Color::Green
        } else if percent >= 75 {
            Color::Cyan
        } else if percent >= 50 {
            Color::Yellow
        } else {
            Color::White
        };

        queue!(
            w,
            MoveTo(x + width + 1, y),
            SetForegroundColor(pct_color),
            Print(pct_str),
            ResetColor
        )?;
    }

    Ok(())
}

/// Truncate string with ellipsis if too long
pub fn truncate_string(s: &str, max_len: usize) -> String {
    if max_len == 0 {
        return String::new();
    }

    // Use grapheme clusters to handle unicode properly
    let chars: Vec<char> = s.chars().collect();
    let char_count = chars.len();

    if char_count <= max_len {
        s.to_string()
    } else if max_len < 3 {
        chars.iter().take(max_len).collect()
    } else {
        let truncated: String = chars.iter().take(max_len - 3).collect();
        format!("{}...", truncated)
    }
}

/// Draw an animated spinner for loading states
pub fn draw_spinner<W: Write>(
    w: &mut W,
    x: u16,
    y: u16,
    frame: usize,
) -> io::Result<()> {
    let spinner_chars = ["◐", "◓", "◑", "◒"];
    let spinner_char = spinner_chars[frame % spinner_chars.len()];
    
    queue!(
        w,
        MoveTo(x, y),
        SetForegroundColor(Color::Cyan),
        Print(spinner_char),
        ResetColor
    )
}

/// Draw a status indicator with color coding
pub fn draw_status_indicator<W: Write>(
    w: &mut W,
    x: u16,
    y: u16,
    status: &str,
) -> io::Result<()> {
    let (color, symbol) = match status.to_lowercase().as_str() {
        "running" | "active" => (Color::Green, "●"),
        "completed" | "done" => (Color::Blue, "◉"),
        "failed" | "error" => (Color::Red, "◎"),
        "warning" | "warn" => (Color::Yellow, "◐"),
        _ => (Color::White, "○"),
    };
    
    queue!(
        w,
        MoveTo(x, y),
        SetForegroundColor(color),
        Print(symbol),
        ResetColor
    )
}
