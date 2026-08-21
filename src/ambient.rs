use std::collections::VecDeque;
use std::fs;
use std::path::PathBuf;

/// Resolves sysfs IIO root path (default: /sys/bus/iio/devices).
pub fn get_iio_root() -> PathBuf {
    if let Ok(root) = std::env::var("LBRIGHT_SYSFS_ROOT") {
        return PathBuf::from(root).join("bus/iio/devices");
    }
    PathBuf::from("/sys/bus/iio/devices")
}

#[derive(Debug, Clone)]
pub struct AmbientSensor {
    pub path: PathBuf,
}

impl AmbientSensor {
    /// Detects available ambient light sensors in sysfs IIO devices.
    pub fn detect() -> Option<Self> {
        let base = get_iio_root();
        if let Ok(entries) = fs::read_dir(&base) {
            for entry in entries.flatten() {
                let dev_path = entry.path();
                for filename in &["in_illuminance_input", "in_illuminance_raw", "in_illuminance0_input", "in_illuminance0_raw"] {
                    let p = dev_path.join(filename);
                    if p.exists() {
                        return Some(Self { path: p });
                    }
                }
            }
        }
        None
    }

    /// Reads raw illuminance lux value directly from sysfs.
    pub fn read_lux(&self) -> Option<i64> {
        let content = fs::read_to_string(&self.path).ok()?;
        content.trim().parse::<i64>().ok()
    }
}

/// Calculates brightness offset percentage from lux.
pub fn calc_ambient_offset(lux: i64) -> i8 {
    if lux < 10 {
        -15
    } else if lux < 50 {
        -10
    } else if lux < 150 {
        -5
    } else if lux > 3000 {
        30
    } else if lux > 1000 {
        20
    } else if lux > 500 {
        10
    } else {
        0
    }
}

/// Moving average and hysteresis buffer for ambient light readings.
#[derive(Debug, Clone)]
pub struct AmbientTracker {
    buffer: VecDeque<i64>,
    capacity: usize,
    last_applied_offset: i8,
}

impl AmbientTracker {
    pub fn new(capacity: usize) -> Self {
        Self {
            buffer: VecDeque::with_capacity(capacity.max(1)),
            capacity: capacity.max(1),
            last_applied_offset: 0,
        }
    }

    pub fn set_capacity(&mut self, capacity: usize) {
        self.capacity = capacity.max(1);
        while self.buffer.len() > self.capacity {
            self.buffer.pop_front();
        }
    }

    pub fn push_sample(&mut self, lux: i64) -> i64 {
        if self.buffer.len() >= self.capacity {
            self.buffer.pop_front();
        }
        self.buffer.push_back(lux);
        self.average()
    }

    pub fn average(&self) -> i64 {
        if self.buffer.is_empty() {
            return 0;
        }
        let sum: i64 = self.buffer.iter().sum();
        sum / self.buffer.len() as i64
    }

    /// Evaluates whether the offset has changed enough to exceed the hysteresis threshold.
    pub fn evaluate_offset(&mut self, lux: i64, hysteresis_pct: u32) -> (i8, bool) {
        let avg_lux = self.push_sample(lux);
        let target_offset = calc_ambient_offset(avg_lux);
        let diff = (target_offset as i32 - self.last_applied_offset as i32).abs();

        if diff >= hysteresis_pct as i32 {
            self.last_applied_offset = target_offset;
            (target_offset, true)
        } else {
            (self.last_applied_offset, false)
        }
    }

    pub fn current_offset(&self) -> i8 {
        self.last_applied_offset
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ambient_offset() {
        assert_eq!(calc_ambient_offset(5), -15);
        assert_eq!(calc_ambient_offset(30), -10);
        assert_eq!(calc_ambient_offset(100), -5);
        assert_eq!(calc_ambient_offset(300), 0);
        assert_eq!(calc_ambient_offset(600), 10);
        assert_eq!(calc_ambient_offset(1500), 20);
        assert_eq!(calc_ambient_offset(5000), 30);
    }

    #[test]
    fn test_tracker_hysteresis() {
        let mut tracker = AmbientTracker::new(3);

        // Step into bright light (lux 600 -> offset +10)
        let (offset, changed) = tracker.evaluate_offset(600, 3);
        assert_eq!(offset, 10);
        assert!(changed);

        // Minor change (lux 700 -> offset still +10, diff 0 < 3)
        let (offset, changed) = tracker.evaluate_offset(700, 3);
        assert_eq!(offset, 10);
        assert!(!changed);
    }
}
