use std::fs;
use std::io;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

/// Returns the state directory, checking LBRIGHT_STATE_DIR override if set.
pub fn get_state_dir() -> PathBuf {
    if let Ok(dir) = std::env::var("LBRIGHT_STATE_DIR") {
        return PathBuf::from(dir);
    }
    let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
    PathBuf::from(home).join(".local/state/lbrightness")
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PauseState {
    Active,
    PausedUntil(u64), // Unix epoch in seconds
    PausedIndefinite,
}

impl PauseState {
    pub fn is_paused(&self) -> bool {
        match self {
            PauseState::Active => false,
            PauseState::PausedIndefinite => true,
            PauseState::PausedUntil(ts) => {
                let now = SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_secs();
                now < *ts
            }
        }
    }

    pub fn remaining_seconds(&self) -> Option<u64> {
        match self {
            PauseState::Active => None,
            PauseState::PausedIndefinite => None,
            PauseState::PausedUntil(ts) => {
                let now = SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_secs();
                if *ts > now {
                    Some(*ts - now)
                } else {
                    None
                }
            }
        }
    }
}

/// Reads the pause state from disk.
pub fn read_pause_state(state_dir: &Path) -> PauseState {
    let pause_file = state_dir.join("paused");
    if !pause_file.exists() {
        return PauseState::Active;
    }
    match fs::read_to_string(&pause_file) {
        Ok(content) => {
            let s = content.trim();
            if s.eq_ignore_ascii_case("indefinite") {
                PauseState::PausedIndefinite
            } else if let Ok(ts) = s.parse::<u64>() {
                let now = SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_secs();
                if now < ts {
                    PauseState::PausedUntil(ts)
                } else {
                    // Expired, clean up
                    let _ = fs::remove_file(&pause_file);
                    PauseState::Active
                }
            } else {
                PauseState::Active
            }
        }
        Err(_) => PauseState::Active,
    }
}

/// Sets the pause state on disk.
pub fn set_pause_state(state_dir: &Path, state: &PauseState) -> io::Result<()> {
    let _ = fs::create_dir_all(state_dir);
    let pause_file = state_dir.join("paused");
    match state {
        PauseState::Active => {
            if pause_file.exists() {
                let _ = fs::remove_file(&pause_file);
            }
            Ok(())
        }
        PauseState::PausedIndefinite => fs::write(&pause_file, "indefinite"),
        PauseState::PausedUntil(ts) => fs::write(&pause_file, ts.to_string()),
    }
}

/// Parses a human duration string (e.g. "30m", "1h", "8h", "off", "indefinite") into a PauseState.
pub fn parse_pause_arg(arg: &str) -> Result<PauseState, String> {
    let clean = arg.trim().to_ascii_lowercase();
    if clean == "off" || clean == "resume" || clean == "0" {
        return Ok(PauseState::Active);
    }
    if clean == "indefinite" || clean == "inf" || clean == "forever" {
        return Ok(PauseState::PausedIndefinite);
    }

    let (num_str, unit) = if clean.ends_with('m') || clean.ends_with("min") {
        (clean.trim_end_matches("min").trim_end_matches('m'), "m")
    } else if clean.ends_with('h') || clean.ends_with("hr") {
        (clean.trim_end_matches("hr").trim_end_matches('h'), "h")
    } else if clean.ends_with('s') || clean.ends_with("sec") {
        (clean.trim_end_matches("sec").trim_end_matches('s'), "s")
    } else {
        // Default to minutes if just a number
        (clean.as_str(), "m")
    };

    let num: u64 = num_str
        .parse()
        .map_err(|_| format!("Invalid pause duration: '{}'", arg))?;

    let seconds = match unit {
        "s" => num,
        "m" => num * 60,
        "h" => num * 3600,
        _ => num * 60,
    };

    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();

    Ok(PauseState::PausedUntil(now + seconds))
}

#[allow(dead_code)]
#[derive(Debug, Clone)]
pub struct DeviceState {
    pub last_applied_pct: u8,
    pub last_applied_time: u64,
}

/// Reads the last known applied brightness state for a device.
#[allow(dead_code)]
pub fn read_device_state(state_dir: &Path, device_key: &str) -> Option<DeviceState> {
    let path = state_dir.join(format!("{}.state", device_key));
    let content = fs::read_to_string(path).ok()?;
    let parts: Vec<&str> = content.split_whitespace().collect();
    if parts.len() >= 2 {
        let pct = parts[0].parse().ok()?;
        let time = parts[1].parse().ok()?;
        Some(DeviceState {
            last_applied_pct: pct,
            last_applied_time: time,
        })
    } else {
        None
    }
}

/// Writes the last applied brightness state for a device.
pub fn write_device_state(state_dir: &Path, device_key: &str, pct: u8) -> io::Result<()> {
    let _ = fs::create_dir_all(state_dir);
    let path = state_dir.join(format!("{}.state", device_key));
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    fs::write(path, format!("{} {}\n", pct, now))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pause_parsing() {
        assert_eq!(parse_pause_arg("off").unwrap(), PauseState::Active);
        assert_eq!(
            parse_pause_arg("indefinite").unwrap(),
            PauseState::PausedIndefinite
        );

        let p10m = parse_pause_arg("10m").unwrap();
        assert!(p10m.is_paused());
        let rem = p10m.remaining_seconds().unwrap();
        assert!(rem >= 590 && rem <= 600);

        let p2h = parse_pause_arg("2h").unwrap();
        assert!(p2h.is_paused());
        let rem2 = p2h.remaining_seconds().unwrap();
        assert!(rem2 >= 7190 && rem2 <= 7200);
    }

    #[test]
    fn test_pause_file_io() {
        let tmp = std::env::temp_dir().join("lbright_test_state_pause");
        let _ = fs::remove_dir_all(&tmp);

        assert_eq!(read_pause_state(&tmp), PauseState::Active);

        set_pause_state(&tmp, &PauseState::PausedIndefinite).unwrap();
        assert_eq!(read_pause_state(&tmp), PauseState::PausedIndefinite);

        set_pause_state(&tmp, &PauseState::Active).unwrap();
        assert_eq!(read_pause_state(&tmp), PauseState::Active);
    }
}
