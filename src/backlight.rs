use std::fs;
use std::io;
use std::path::PathBuf;
use std::process::{Command, Stdio};

/// Resolves sysfs backlight root path (default: /sys/class/backlight).
pub fn get_backlight_root() -> PathBuf {
    if let Ok(root) = std::env::var("LBRIGHT_SYSFS_ROOT") {
        return PathBuf::from(root).join("class/backlight");
    }
    PathBuf::from("/sys/class/backlight")
}

#[derive(Debug, Clone)]
pub struct InternalPanel {
    pub name: String,
    pub path: PathBuf,
    pub max_raw: i64,
}

impl InternalPanel {
    /// Detects all internal backlight devices present in sysfs.
    pub fn detect_all() -> Vec<Self> {
        let base = get_backlight_root();
        let mut panels = Vec::new();

        if let Ok(entries) = fs::read_dir(&base) {
            for entry in entries.flatten() {
                let name = entry.file_name().to_string_lossy().to_string();
                let dev_path = base.join(&name);

                let max_path = dev_path.join("max_brightness");
                if let Ok(max_str) = fs::read_to_string(&max_path) {
                    if let Ok(max_raw) = max_str.trim().parse::<i64>() {
                        if max_raw > 0 {
                            panels.push(Self {
                                name,
                                path: dev_path,
                                max_raw,
                            });
                        }
                    }
                }
            }
        }

        // Sort so intel_backlight or amdgpu_bl comes first predictably
        panels.sort_by(|a, b| a.name.cmp(&b.name));
        panels
    }

    /// Detects the primary internal panel.
    pub fn detect_primary() -> Option<Self> {
        let all = Self::detect_all();
        all.into_iter().next()
    }

    /// Detects panel by specific name (e.g. "intel_backlight", "amdgpu_bl0").
    pub fn detect_by_name(name: &str) -> Option<Self> {
        let all = Self::detect_all();
        all.into_iter().find(|p| p.name == name)
    }

    /// Reads raw hardware brightness value.
    pub fn get_raw(&self) -> io::Result<i64> {
        let p = self.path.join("brightness");
        let s = fs::read_to_string(p)?;
        s.trim()
            .parse::<i64>()
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))
    }

    /// Reads brightness percentage (0..=100).
    pub fn get_percent(&self) -> io::Result<u8> {
        let raw = self.get_raw()?;
        if self.max_raw <= 0 {
            return Ok(0);
        }
        let pct = (raw * 100 + self.max_raw / 2) / self.max_raw;
        Ok(pct.clamp(0, 100) as u8)
    }

    /// Sets raw hardware brightness directly via sysfs.
    pub fn set_raw(&self, raw: i64) -> io::Result<()> {
        let clamped = raw.clamp(1, self.max_raw);
        let path = self.path.join("brightness");

        match fs::write(&path, clamped.to_string()) {
            Ok(_) => Ok(()),
            Err(e) if e.kind() == io::ErrorKind::PermissionDenied => {
                // Fallback to brightnessctl only if available
                if let Ok(true) = self.try_brightnessctl_set_raw(clamped) {
                    return Ok(());
                }
                eprintln!(
                    "Permission denied writing to '{}'.\nTip: Add your user to the 'video' group:\n  sudo usermod -aG video $USER\nand log out and back in.",
                    path.display()
                );
                Err(e)
            }
            Err(e) => Err(e),
        }
    }

    /// Sets brightness percentage (0..=100).
    pub fn set_percent(&self, pct: u8) -> io::Result<()> {
        let clamped_pct = pct.clamp(1, 100);
        let raw = (clamped_pct as i64 * self.max_raw + 50) / 100;
        self.set_raw(raw)
    }

    fn try_brightnessctl_set_raw(&self, raw: i64) -> io::Result<bool> {
        let status = Command::new("brightnessctl")
            .args(["-d", &self.name, "set", &raw.to_string(), "-q"])
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status()?;
        Ok(status.success())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mock_sysfs_backlight() {
        let tmp = std::env::temp_dir().join("lbright_test_sysfs/class/backlight/intel_backlight");
        let _ = fs::create_dir_all(&tmp);
        fs::write(tmp.join("max_brightness"), "96000\n").unwrap();
        fs::write(tmp.join("brightness"), "48000\n").unwrap();

        std::env::set_var(
            "LBRIGHT_SYSFS_ROOT",
            std::env::temp_dir().join("lbright_test_sysfs"),
        );

        let panel = InternalPanel::detect_by_name("intel_backlight").unwrap();
        assert_eq!(panel.max_raw, 96000);
        assert_eq!(panel.get_raw().unwrap(), 48000);
        assert_eq!(panel.get_percent().unwrap(), 50);

        panel.set_percent(25).unwrap();
        assert_eq!(panel.get_percent().unwrap(), 25);

        std::env::remove_var("LBRIGHT_SYSFS_ROOT");
    }
}
