use std::io;
use std::process::{Command, Stdio};
use std::sync::mpsc::{self, Sender};
use std::thread;
use std::time::{Duration, Instant};

use crate::config::DdcId;

/// Executes a child process with a hard timeout, killing the child if it exceeds timeout.
pub fn run_with_timeout(cmd: &mut Command, timeout: Duration) -> io::Result<(bool, String)> {
    let mut child = cmd
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()?;

    let start = Instant::now();

    loop {
        match child.try_wait()? {
            Some(status) => {
                let output = child.wait_with_output()?;
                let stdout = String::from_utf8_lossy(&output.stdout).to_string();
                return Ok((status.success(), stdout));
            }
            None => {
                if start.elapsed() > timeout {
                    let _ = child.kill();
                    let _ = child.wait();
                    return Ok((false, "Command timed out".to_string()));
                }
                thread::sleep(Duration::from_millis(50));
            }
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DdcDisplay {
    pub display_index: u8,
    pub bus: Option<u8>,
    pub serial: Option<String>,
    pub edid: Option<String>,
    pub model: Option<String>,
}

impl DdcDisplay {
    /// Checks if a display matches the given DdcId according to priority.
    pub fn matches(&self, id: &DdcId) -> bool {
        match id {
            DdcId::Default => true,
            DdcId::Index(idx) => self.display_index == *idx,
            DdcId::Bus(bus) => self.bus == Some(*bus),
            DdcId::Serial(s) => self.serial.as_ref().map_or(false, |val| val == s),
            DdcId::Edid(e) => self.edid.as_ref().map_or(false, |val| val == e),
            DdcId::Model(m) => self.model.as_ref().map_or(false, |val| val == m),
            DdcId::Unmatched(_) => false,
        }
    }
}

/// Parses output from `ddcutil detect --brief`.
pub fn parse_ddc_detect_output(output: &str) -> Vec<DdcDisplay> {
    let mut displays = Vec::new();
    let mut current_idx: Option<u8> = None;
    let mut current_bus: Option<u8> = None;
    let mut current_serial: Option<String> = None;
    let mut current_edid: Option<String> = None;
    let mut current_model: Option<String> = None;

    for line in output.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with("Display ") {
            if let Some(idx) = current_idx {
                displays.push(DdcDisplay {
                    display_index: idx,
                    bus: current_bus,
                    serial: current_serial.take(),
                    edid: current_edid.take(),
                    model: current_model.take(),
                });
            }
            let parts: Vec<&str> = trimmed.split_whitespace().collect();
            if parts.len() >= 2 {
                current_idx = parts[1].parse::<u8>().ok();
            } else {
                current_idx = None;
            }
            current_bus = None;
        } else if trimmed.starts_with("I2C bus:") {
            if let Some(bus_part) = trimmed.split("/dev/i2c-").nth(1) {
                current_bus = bus_part.trim().parse::<u8>().ok();
            }
        } else if trimmed.starts_with("Monitor:") {
            let model = trimmed.trim_start_matches("Monitor:").trim();
            if !model.is_empty() {
                current_model = Some(model.to_string());
            }
        } else if trimmed.starts_with("Serial number:") {
            let sn = trimmed.trim_start_matches("Serial number:").trim();
            if !sn.is_empty() {
                current_serial = Some(sn.to_string());
            }
        } else if trimmed.starts_with("EDID synopsis:") {
            let edid = trimmed.trim_start_matches("EDID synopsis:").trim();
            if !edid.is_empty() {
                current_edid = Some(edid.to_string());
            }
        }
    }

    if let Some(idx) = current_idx {
        displays.push(DdcDisplay {
            display_index: idx,
            bus: current_bus,
            serial: current_serial,
            edid: current_edid,
            model: current_model,
        });
    }

    displays
}

/// Scans connected DDC displays by running `ddcutil detect --brief`.
pub fn scan_ddc_displays(timeout: Duration) -> Vec<DdcDisplay> {
    let mut cmd = Command::new("ddcutil");
    cmd.args(["detect", "--brief"]);

    match run_with_timeout(&mut cmd, timeout) {
        Ok((true, stdout)) => parse_ddc_detect_output(&stdout),
        Ok((false, err)) => {
            eprintln!("Warning: ddcutil detect failed: {}", err);
            Vec::new()
        }
        Err(_) => Vec::new(),
    }
}

/// Sets brightness (VCP code 0x10) on a specific display index via ddcutil.
pub fn ddc_set_vcp(display_index: u8, pct: u8, timeout: Duration) -> bool {
    let mut cmd = Command::new("ddcutil");
    cmd.args([
        "setvcp",
        "10",
        &pct.to_string(),
        "--display",
        &display_index.to_string(),
    ]);

    match run_with_timeout(&mut cmd, timeout) {
        Ok((true, _)) => true,
        Ok((false, err)) => {
            eprintln!(
                "Warning: ddcutil setvcp 10 {} failed on display {}: {}",
                pct, display_index, err
            );
            false
        }
        Err(e) => {
            eprintln!("Error executing ddcutil: {}", e);
            false
        }
    }
}

#[derive(Debug, Clone)]
pub enum DdcCommand {
    Set { id: DdcId, pct: u8 },
    Rescan,
}

pub struct DdcWorkerHandle {
    pub tx: Sender<DdcCommand>,
}

/// Spawns a dedicated DDC background worker thread with serialization, timeouts, and rate limiting.
pub fn start_ddc_worker(
    set_timeout: Duration,
    detect_timeout: Duration,
    cooldown: Duration,
) -> DdcWorkerHandle {
    let (tx, rx) = mpsc::channel::<DdcCommand>();

    thread::spawn(move || {
        let mut cached_displays = scan_ddc_displays(detect_timeout);
        let mut last_set_time = Instant::now() - cooldown;

        while let Ok(cmd) = rx.recv() {
            match cmd {
                DdcCommand::Rescan => {
                    cached_displays = scan_ddc_displays(detect_timeout);
                }
                DdcCommand::Set { id, pct } => {
                    // Rate limiting check
                    if last_set_time.elapsed() < cooldown {
                        thread::sleep(cooldown - last_set_time.elapsed());
                    }

                    // Find matching display index
                    let matched_index = cached_displays
                        .iter()
                        .find(|d| d.matches(&id))
                        .map(|d| d.display_index);

                    if let Some(idx) = matched_index {
                        if ddc_set_vcp(idx, pct, set_timeout) {
                            last_set_time = Instant::now();
                        }
                    } else if id == DdcId::Default && !cached_displays.is_empty() {
                        // Default fallback to first display
                        let idx = cached_displays[0].display_index;
                        if ddc_set_vcp(idx, pct, set_timeout) {
                            last_set_time = Instant::now();
                        }
                    }
                }
            }
        }
    });

    DdcWorkerHandle { tx }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_ddc_detect() {
        let sample_output = r#"
Display 1
   I2C bus:  /dev/i2c-7
   EDID synopsis:
      Model:               DELL U2720QM
      Serial number:       ABC12345
   VCP version:         2.1

Display 2
   I2C bus:  /dev/i2c-8
   EDID synopsis:
      Model:               LG ULTRAGEAR
      Serial number:       XYZ98765
   VCP version:         2.1
"#;
        let displays = parse_ddc_detect_output(sample_output);
        assert_eq!(displays.len(), 2);
        assert_eq!(displays[0].display_index, 1);
        assert_eq!(displays[0].bus, Some(7));
        assert_eq!(displays[0].serial, Some("ABC12345".to_string()));

        assert_eq!(displays[1].display_index, 2);
        assert_eq!(displays[1].bus, Some(8));
        assert_eq!(displays[1].serial, Some("XYZ98765".to_string()));

        // Matching
        assert!(displays[0].matches(&DdcId::Serial("ABC12345".to_string())));
        assert!(displays[0].matches(&DdcId::Bus(7)));
        assert!(displays[0].matches(&DdcId::Index(1)));
        assert!(!displays[0].matches(&DdcId::Serial("OTHER".to_string())));
    }
}
