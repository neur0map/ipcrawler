use crossterm::{
    cursor::MoveTo,
    queue,
    style::{Color, Print, ResetColor, SetForegroundColor},
};
use std::io::{self, Write};

use crate::dashboard::layout::Rect;

/// Draw a box with optional title
pub fn draw_box<W: Write>(w: &mut W, rect: &Rect, title: &str) -> io::Result<()> {
    // Top border
    queue!(
        w,
        MoveTo(rect.x, rect.y),
        SetForegroundColor(Color::DarkGrey),
        Print("┌")
    )?;

    if !title.is_empty() && rect.width > title.len() as u16 + 4 {
        queue!(
            w,
            Print("─ "),
            SetForegroundColor(Color::White),
            Print(title),
            SetForegroundColor(Color::DarkGrey),
            Print(" ")
        )?;
        let remaining = rect.width - title.len() as u16 - 5;
        queue!(w, Print("─".repeat(remaining as usize)))?;
    } else {
        queue!(w, Print("─".repeat((rect.width - 2) as usize)))?;
    }

    queue!(w, Print("┐"))?;

    // Sides
    for y in 1..rect.height - 1 {
        queue!(
            w,
            MoveTo(rect.x, rect.y + y),
            Print("│"),
            MoveTo(rect.x + rect.width - 1, rect.y + y),
            Print("│")
        )?;
    }

    // Bottom border
    queue!(
        w,
        MoveTo(rect.x, rect.y + rect.height - 1),
        Print("└"),
        Print("─".repeat((rect.width - 2) as usize)),
        Print("┘"),
        ResetColor
    )
}

/// Draw a progress bar
pub fn draw_progress_bar<W: Write>(
    w: &mut W,
    x: u16,
    y: u16,
    width: u16,
    percent: u8,
) -> io::Result<()> {
    let filled = ((percent as f32 / 100.0) * width as f32) as u16;
    let empty = width.saturating_sub(filled);

    queue!(
        w,
        MoveTo(x, y),
        SetForegroundColor(Color::Green),
        Print("█".repeat(filled as usize)),
        SetForegroundColor(Color::DarkGrey),
        Print("░".repeat(empty as usize)),
        ResetColor
    )?;

    // Percentage text
    let pct_str = format!(" {}%", percent);
    if width > pct_str.len() as u16 + 2 {
        queue!(
            w,
            MoveTo(x + width + 1, y),
            SetForegroundColor(Color::Yellow),
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
