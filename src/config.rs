use std::collections::BTreeMap;
use std::fmt;
use std::fs::{self, File, OpenOptions};
use std::io;
use std::path::{Path, PathBuf};
use std::str::FromStr;

use crate::profile::{minutes_to_hhmm, parse_time_str};

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub enum DdcId {
    Default,
    Index(u8),
    Bus(u8),
    Serial(String),
    Edid(String),
    Model(String),
    Unmatched(String),
}

impl fmt::Display for DdcId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            DdcId::Default => write!(f, "default"),
            DdcId::Index(idx) => write!(f, "{}", idx),
            DdcId::Bus(bus) => write!(f, "bus={}", bus),
            DdcId::Serial(s) => write!(f, "serial={}", s),
            DdcId::Edid(e) => write!(f, "edid={}", e),
            DdcId::Model(m) => write!(f, "model={}", m),
            DdcId::Unmatched(u) => write!(f, "unmatched_{}", u),
        }
    }
}

impl FromStr for DdcId {
    type Err = ();

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let clean = s.trim();
        if clean.eq_ignore_ascii_case("default") {
            return Ok(DdcId::Default);
        }
        if let Ok(idx) = clean.parse::<u8>() {
            return Ok(DdcId::Index(idx));
        }
        if let Some((k, v)) = clean.split_once('=') {
            let k = k.trim().to_ascii_lowercase();
            let v = v.trim();
            match k.as_str() {
                "bus" => {
                    if let Ok(bus) = v.parse::<u8>() {
                        return Ok(DdcId::Bus(bus));
                    }
                }
                "serial" => return Ok(DdcId::Serial(v.to_string())),
                "edid" => return Ok(DdcId::Edid(v.to_string())),
                "model" => return Ok(DdcId::Model(v.to_string())),
                _ => {}
            }
        }
        if let Some(rest) = clean.strip_prefix("unmatched_") {
            return Ok(DdcId::Unmatched(rest.to_string()));
        }
        Ok(DdcId::Unmatched(clean.to_string()))
    }
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub enum DeviceId {
    Internal(Option<String>),
    Ddc(DdcId),
}

impl fmt::Display for DeviceId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            DeviceId::Internal(None) => write!(f, "internal"),
            DeviceId::Internal(Some(name)) => write!(f, "internal:{}", name),
            DeviceId::Ddc(ddc_id) => write!(f, "ddc:{}", ddc_id),
        }
    }
}

impl FromStr for DeviceId {
    type Err = ();

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let clean = s.trim();
        if clean.eq_ignore_ascii_case("internal") {
            return Ok(DeviceId::Internal(None));
        }
        if let Some(rest) = clean.strip_prefix("internal:") {
            return Ok(DeviceId::Internal(Some(rest.trim().to_string())));
        }
        if let Some(rest) = clean.strip_prefix("ddc:") {
            let ddc_id = DdcId::from_str(rest)?;
            return Ok(DeviceId::Ddc(ddc_id));
        }
        Err(())
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DeviceConfig {
    pub id: DeviceId,
    pub enabled: bool,
    pub points: BTreeMap<u16, u8>, // Minute of day (0..=1439) -> percent (0..=100)
}

impl DeviceConfig {
    pub fn new(id: DeviceId, enabled: bool) -> Self {
        Self {
            id,
            enabled,
            points: BTreeMap::new(),
        }
    }

    pub fn with_default_curve(id: DeviceId) -> Self {
        let mut dev = Self::new(id, true);
        dev.points.insert(0, 18); // 00:00 -> 18%
        dev.points.insert(420, 45); // 07:00 -> 45%
        dev.points.insert(720, 65); // 12:00 -> 65%
        dev.points.insert(1140, 55); // 19:00 -> 55%
        dev.points.insert(1380, 25); // 23:00 -> 25%
        dev
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GeneralConfig {
    pub interval_min: u32,
    pub ambient: bool,
    pub ambient_poll_sec: u32,
    pub ambient_average: u32,
    pub ambient_hysteresis_pct: u32,
    pub fade_internal: bool,
    pub fade_external: bool,
    pub learn_internal: bool,
    pub learn_external: bool,
    pub min_internal: u8,
    pub max_internal: u8,
    pub min_external: u8,
    pub max_external: u8,
    pub ddc_rescan_min: u32,
    pub ddc_cooldown_sec: u32,
    pub ddc_set_timeout_sec: u64,
    pub ddc_detect_timeout_sec: u64,
}

impl Default for GeneralConfig {
    fn default() -> Self {
        Self {
            interval_min: 15,
            ambient: false,
            ambient_poll_sec: 5,
            ambient_average: 3,
            ambient_hysteresis_pct: 3,
            fade_internal: true,
            fade_external: false,
            learn_internal: true,
            learn_external: false,
            min_internal: 5,
            max_internal: 100,
            min_external: 0,
            max_external: 100,
            ddc_rescan_min: 5,
            ddc_cooldown_sec: 10,
            ddc_set_timeout_sec: 5,
            ddc_detect_timeout_sec: 10,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Config {
    pub version: u32,
    pub general: GeneralConfig,
    pub devices: Vec<DeviceConfig>,
}

impl Default for Config {
    fn default() -> Self {
        let general = GeneralConfig::default();
        let internal = DeviceConfig::with_default_curve(DeviceId::Internal(None));
        let ddc_default = DeviceConfig::with_default_curve(DeviceId::Ddc(DdcId::Default));

        Self {
            version: 2,
            general,
            devices: vec![internal, ddc_default],
        }
    }
}

impl Config {
    pub fn get_device_mut(&mut self, id: &DeviceId) -> Option<&mut DeviceConfig> {
        self.devices.iter_mut().find(|d| &d.id == id)
    }

    #[allow(dead_code)]
    pub fn get_device(&self, id: &DeviceId) -> Option<&DeviceConfig> {
        self.devices.iter().find(|d| &d.id == id)
    }

    pub fn get_internal(&self) -> Option<&DeviceConfig> {
        self.devices
            .iter()
            .find(|d| matches!(d.id, DeviceId::Internal(_)) && d.enabled)
            .or_else(|| {
                self.devices
                    .iter()
                    .find(|d| matches!(d.id, DeviceId::Internal(_)))
            })
    }

    /// Serializes configuration into clean INI format.
    pub fn to_ini_string(&self) -> String {
        let mut out = String::new();
        out.push_str("# LBrightness Configuration\n");
        out.push_str(&format!("version = {}\n\n", self.version));

        out.push_str("[general]\n");
        out.push_str(&format!("interval_min = {}\n", self.general.interval_min));
        out.push_str(&format!("ambient = {}\n", self.general.ambient));
        out.push_str(&format!(
            "ambient_poll_sec = {}\n",
            self.general.ambient_poll_sec
        ));
        out.push_str(&format!(
            "ambient_average = {}\n",
            self.general.ambient_average
        ));
        out.push_str(&format!(
            "ambient_hysteresis_pct = {}\n",
            self.general.ambient_hysteresis_pct
        ));
        out.push_str(&format!(
            "fade_internal = {}\n",
            self.general.fade_internal
        ));
        out.push_str(&format!(
            "fade_external = {}\n",
            self.general.fade_external
        ));
        out.push_str(&format!(
            "learn_internal = {}\n",
            self.general.learn_internal
        ));
        out.push_str(&format!(
            "learn_external = {}\n",
            self.general.learn_external
        ));
        out.push_str(&format!("min_internal = {}\n", self.general.min_internal));
        out.push_str(&format!("max_internal = {}\n", self.general.max_internal));
        out.push_str(&format!("min_external = {}\n", self.general.min_external));
        out.push_str(&format!("max_external = {}\n", self.general.max_external));
        out.push_str(&format!(
            "ddc_rescan_min = {}\n",
            self.general.ddc_rescan_min
        ));
        out.push_str(&format!(
            "ddc_cooldown_sec = {}\n",
            self.general.ddc_cooldown_sec
        ));
        out.push_str(&format!(
            "ddc_set_timeout_sec = {}\n",
            self.general.ddc_set_timeout_sec
        ));
        out.push_str(&format!(
            "ddc_detect_timeout_sec = {}\n",
            self.general.ddc_detect_timeout_sec
        ));
        out.push('\n');

        for dev in &self.devices {
            out.push_str(&format!("[{}]\n", dev.id));
            out.push_str(&format!("enabled = {}\n", dev.enabled));
            for (&minutes, &pct) in &dev.points {
                out.push_str(&format!("point = {}:{}\n", minutes_to_hhmm(minutes), pct));
            }
            out.push('\n');
        }

        out
    }

    /// Parses configuration from INI string.
    pub fn from_ini_string(content: &str) -> (Self, Vec<String>) {
        let mut warnings = Vec::new();
        let mut config = Config::default();
        config.devices.clear();

        let mut current_section: Option<String> = None;
        let mut current_device: Option<DeviceConfig> = None;

        for (line_no, raw_line) in content.lines().enumerate() {
            let line = raw_line.trim();
            if line.is_empty() || line.starts_with('#') || line.starts_with(';') {
                continue;
            }

            if line.starts_with('[') && line.ends_with(']') {
                // Finish previous section
                if let Some(dev) = current_device.take() {
                    config.devices.push(dev);
                }

                let sec_name = line[1..line.len() - 1].trim().to_string();
                if sec_name.eq_ignore_ascii_case("general") {
                    current_section = Some("general".to_string());
                } else if let Ok(dev_id) = DeviceId::from_str(&sec_name) {
                    current_section = Some(sec_name);
                    current_device = Some(DeviceConfig::new(dev_id, true));
                } else {
                    warnings.push(format!(
                        "Line {}: Unrecognized section [{}]",
                        line_no + 1,
                        sec_name
                    ));
                    current_section = None;
                }
                continue;
            }

            if let Some((key_raw, val_raw)) = line.split_once('=') {
                let k = key_raw.trim().to_ascii_lowercase();
                let v = val_raw.trim();

                match current_section.as_deref() {
                    None => {
                        if k == "version" {
                            if let Ok(ver) = v.parse::<u32>() {
                                config.version = ver;
                            }
                        }
                    }
                    Some("general") => match k.as_str() {
                        "interval_min" => {
                            if let Ok(n) = v.parse() {
                                config.general.interval_min = n;
                            }
                        }
                        "ambient" => {
                            if let Ok(b) = v.parse() {
                                config.general.ambient = b;
                            }
                        }
                        "ambient_poll_sec" => {
                            if let Ok(n) = v.parse() {
                                config.general.ambient_poll_sec = n;
                            }
                        }
                        "ambient_average" => {
                            if let Ok(n) = v.parse() {
                                config.general.ambient_average = n;
                            }
                        }
                        "ambient_hysteresis_pct" => {
                            if let Ok(n) = v.parse() {
                                config.general.ambient_hysteresis_pct = n;
                            }
                        }
                        "fade_internal" => {
                            if let Ok(b) = v.parse() {
                                config.general.fade_internal = b;
                            }
                        }
                        "fade_external" => {
                            if let Ok(b) = v.parse() {
                                config.general.fade_external = b;
                            }
                        }
                        "learn_internal" => {
                            if let Ok(b) = v.parse() {
                                config.general.learn_internal = b;
                            }
                        }
                        "learn_external" => {
                            if let Ok(b) = v.parse() {
                                config.general.learn_external = b;
                            }
                        }
                        "min_internal" => {
                            if let Ok(n) = v.parse() {
                                config.general.min_internal = n;
                            }
                        }
                        "max_internal" => {
                            if let Ok(n) = v.parse() {
                                config.general.max_internal = n;
                            }
                        }
                        "min_external" => {
                            if let Ok(n) = v.parse() {
                                config.general.min_external = n;
                            }
                        }
                        "max_external" => {
                            if let Ok(n) = v.parse() {
                                config.general.max_external = n;
                            }
                        }
                        "ddc_rescan_min" => {
                            if let Ok(n) = v.parse() {
                                config.general.ddc_rescan_min = n;
                            }
                        }
                        "ddc_cooldown_sec" => {
                            if let Ok(n) = v.parse() {
                                config.general.ddc_cooldown_sec = n;
                            }
                        }
                        "ddc_set_timeout_sec" => {
                            if let Ok(n) = v.parse() {
                                config.general.ddc_set_timeout_sec = n;
                            }
                        }
                        "ddc_detect_timeout_sec" => {
                            if let Ok(n) = v.parse() {
                                config.general.ddc_detect_timeout_sec = n;
                            }
                        }
                        _ => warnings.push(format!(
                            "Line {}: Unknown general key '{}'",
                            line_no + 1,
                            k
                        )),
                    },
                    Some(_) => {
                        if let Some(dev) = current_device.as_mut() {
                            if k == "enabled" {
                                if let Ok(b) = v.parse() {
                                    dev.enabled = b;
                                }
                            } else if k == "point" {
                                if let Some((time_s, pct_s)) = v.split_once(':') {
                                    if let (Some(mins), Ok(pct)) =
                                        (parse_time_str(time_s), pct_s.trim().parse::<u8>())
                                    {
                                        dev.points.insert(mins, pct.min(100));
                                    } else {
                                        warnings.push(format!(
                                            "Line {}: Invalid point format '{}'",
                                            line_no + 1,
                                            v
                                        ));
                                    }
                                } else {
                                    warnings.push(format!(
                                        "Line {}: Point missing colon separator '{}'",
                                        line_no + 1,
                                        v
                                    ));
                                }
                            } else {
                                warnings.push(format!(
                                    "Line {}: Unknown device key '{}'",
                                    line_no + 1,
                                    k
                                ));
                            }
                        }
                    }
                }
            }
        }

        if let Some(dev) = current_device {
            config.devices.push(dev);
        }

        // Ensure internal exists
        if !config
            .devices
            .iter()
            .any(|d| matches!(d.id, DeviceId::Internal(_)))
        {
            config
                .devices
                .insert(0, DeviceConfig::with_default_curve(DeviceId::Internal(None)));
        }

        (config, warnings)
    }
}

/// Advisory lock file to synchronize config modifications across processes.
pub struct LockFile {
    path: PathBuf,
    _file: File,
}

impl LockFile {
    pub fn acquire(config_path: &Path) -> Option<Self> {
        let lock_path = config_path.with_extension("lock");
        if let Some(parent) = lock_path.parent() {
            let _ = fs::create_dir_all(parent);
        }

        // Try open with create_new (atomic lock)
        for _ in 0..10 {
            if let Ok(file) = OpenOptions::new()
                .create_new(true)
                .write(true)
                .open(&lock_path)
            {
                return Some(Self {
                    path: lock_path,
                    _file: file,
                });
            }
            std::thread::sleep(std::time::Duration::from_millis(50));
        }
        None
    }
}

impl Drop for LockFile {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.path);
    }
}

/// Resolves standard config path, checking LBRIGHT_CONFIG_PATH override if present.
pub fn get_config_path() -> PathBuf {
    if let Ok(p) = std::env::var("LBRIGHT_CONFIG_PATH") {
        return PathBuf::from(p);
    }
    let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
    PathBuf::from(home).join(".config/lbrightness/config.ini")
}

/// Resolves legacy profiles.conf path.
pub fn get_legacy_config_path() -> PathBuf {
    if let Ok(p) = std::env::var("LBRIGHT_LEGACY_CONFIG_PATH") {
        return PathBuf::from(p);
    }
    let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
    PathBuf::from(home).join(".config/auto-brightness/profiles.conf")
}

/// Atomically saves content to the target path via a temporary file.
pub fn save_atomic(path: &Path, content: &str) -> io::Result<()> {
    let tmp = path.with_extension("tmp");
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(&tmp, content)?;
    fs::rename(&tmp, path)?;
    Ok(())
}

/// Saves Config object atomically under an advisory lock.
pub fn save_config(path: &Path, config: &Config) -> io::Result<()> {
    let _lock = LockFile::acquire(path)
        .ok_or_else(|| io::Error::new(io::ErrorKind::WouldBlock, "Could not acquire config lock"))?;
    let content = config.to_ini_string();
    save_atomic(path, &content)
}

/// Loads Config from path, returning default if not found.
pub fn load_config(path: &Path) -> (Config, Vec<String>) {
    if !path.exists() {
        return (Config::default(), Vec::new());
    }
    match fs::read_to_string(path) {
        Ok(content) => Config::from_ini_string(&content),
        Err(e) => (
            Config::default(),
            vec![format!("Failed to read config: {}", e)],
        ),
    }
}

/// Migration result metadata.
#[derive(Debug)]
pub struct MigrationResult {
    pub config: Config,
    pub warnings: Vec<String>,
    pub points_migrated: usize,
    #[allow(dead_code)]
    pub legacy_path: PathBuf,
}

/// Imports legacy ~/.config/auto-brightness/profiles.conf without modifying it.
pub fn migrate_legacy_config(legacy_path: &Path) -> io::Result<MigrationResult> {
    if !legacy_path.exists() {
        return Err(io::Error::new(
            io::ErrorKind::NotFound,
            format!("Legacy config not found at {}", legacy_path.display()),
        ));
    }

    let content = fs::read_to_string(legacy_path)?;
    let mut warnings = Vec::new();
    let mut config = Config::default();
    config.devices.clear();

    let mut internal_points = BTreeMap::new();
    let mut device_points: BTreeMap<String, BTreeMap<u16, u8>> = BTreeMap::new();
    let mut disabled_list: Vec<String> = Vec::new();
    let mut points_migrated = 0;

    for (line_no, line) in content.lines().enumerate() {
        let trimmed = line.trim();
        if trimmed.is_empty() || trimmed.starts_with('#') || trimmed.starts_with(';') {
            continue;
        }
        if let Some((k_raw, v_raw)) = trimmed.split_once('=') {
            let k = k_raw.trim();
            let v = v_raw.trim();

            if k == "ambient_sensor" {
                config.general.ambient = v == "1" || v.eq_ignore_ascii_case("true");
            } else if k == "disabled_displays" {
                disabled_list = v.split(',').map(|s| s.trim().to_string()).filter(|s| !s.is_empty()).collect();
            } else if let Ok(pct) = v.parse::<u8>() {
                if let Some((dev_prefix, hhmm)) = k.split_once('_') {
                    if let Some(mins) = parse_time_str(hhmm) {
                        device_points.entry(dev_prefix.to_string()).or_default().insert(mins, pct.min(100));
                        points_migrated += 1;
                    } else {
                        warnings.push(format!("Line {}: Unknown time format in key '{}'", line_no + 1, k));
                    }
                } else if let Some(mins) = parse_time_str(k) {
                    internal_points.insert(mins, pct.min(100));
                    points_migrated += 1;
                } else {
                    warnings.push(format!("Line {}: Unrecognized key '{}'", line_no + 1, k));
                }
            } else {
                warnings.push(format!("Line {}: Invalid value for key '{}'", line_no + 1, k));
            }
        }
    }

    // Add internal device
    let mut internal_dev = DeviceConfig::new(DeviceId::Internal(None), true);
    if !internal_points.is_empty() {
        internal_dev.points = internal_points;
    } else {
        internal_dev = DeviceConfig::with_default_curve(DeviceId::Internal(None));
    }
    if disabled_list.iter().any(|d| d == "default" || d == "internal" || d == "eDP-1") {
        internal_dev.enabled = false;
    }
    config.devices.push(internal_dev);

    // Add other device sections from legacy
    for (dev_name, points) in device_points {
        let is_disabled = disabled_list.contains(&dev_name);
        if dev_name.starts_with("eDP") || dev_name.starts_with("intel") {
            let mut dev = DeviceConfig::new(DeviceId::Internal(Some(dev_name.clone())), !is_disabled);
            dev.points = points;
            config.devices.push(dev);
        } else {
            // External DRM connector name (e.g. HDMI-1) -> map conservatively to unmatched section
            warnings.push(format!(
                "Legacy device '{}' is a DRM connector name; mapped to [ddc:unmatched_{}]. Use 'lbright scan' to associate with a stable DDC ID.",
                dev_name, dev_name
            ));
            let mut dev = DeviceConfig::new(DeviceId::Ddc(DdcId::Unmatched(dev_name.clone())), !is_disabled);
            dev.points = points;
            config.devices.push(dev);
        }
    }

    // If no DDC default exists, add default
    if !config.devices.iter().any(|d| matches!(d.id, DeviceId::Ddc(DdcId::Default))) {
        config.devices.push(DeviceConfig::with_default_curve(DeviceId::Ddc(DdcId::Default)));
    }

    Ok(MigrationResult {
        config,
        warnings,
        points_migrated,
        legacy_path: legacy_path.to_path_buf(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ini_roundtrip() {
        let mut config = Config::default();
        config.general.interval_min = 10;
        config.general.ambient = true;

        let ini_str = config.to_ini_string();
        let (parsed, warnings) = Config::from_ini_string(&ini_str);
        assert!(warnings.is_empty(), "Warnings: {:?}", warnings);
        assert_eq!(parsed.general.interval_min, 10);
        assert_eq!(parsed.general.ambient, true);
        assert_eq!(parsed.devices.len(), config.devices.len());
    }

    #[test]
    fn test_lock_file() {
        let tmp_dir = std::env::temp_dir().join("lbright_test_lock");
        let _ = fs::create_dir_all(&tmp_dir);
        let config_path = tmp_dir.join("config.ini");

        let lock1 = LockFile::acquire(&config_path);
        assert!(lock1.is_some());

        // Second acquire should fail while lock1 is held
        let lock2 = LockFile::acquire(&config_path);
        assert!(lock2.is_none());

        drop(lock1);

        // After dropping lock1, acquire should succeed
        let lock3 = LockFile::acquire(&config_path);
        assert!(lock3.is_some());
    }

    #[test]
    fn test_legacy_migration() {
        let tmp_dir = std::env::temp_dir().join("lbright_test_mig");
        let _ = fs::create_dir_all(&tmp_dir);
        let legacy_file = tmp_dir.join("profiles.conf");

        let sample_legacy = r#"
# Sample legacy conf
ambient_sensor=1
disabled_displays=HDMI-A-1
0000=41
0700=28
1200=33
HDMI-A-1_0000=19
HDMI-A-1_0700=36
"#;
        fs::write(&legacy_file, sample_legacy).unwrap();

        let result = migrate_legacy_config(&legacy_file).unwrap();
        assert!(result.config.general.ambient);
        assert_eq!(result.points_migrated, 5);

        let internal = result.config.get_internal().unwrap();
        assert_eq!(internal.points.get(&0), Some(&41));
        assert_eq!(internal.points.get(&420), Some(&28));
        assert_eq!(internal.points.get(&720), Some(&33));
    }
}
