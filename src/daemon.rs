use std::fs;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use crate::ambient::{AmbientSensor, AmbientTracker};
use crate::backlight::InternalPanel;
use crate::config::{get_config_path, load_config, save_config, DeviceId};
use crate::ddc::{start_ddc_worker, DdcCommand};
use crate::profile::{find_nearest_point, interpolate_linear};
use crate::state::{get_state_dir, read_pause_state, write_device_state};

/// Internal smooth fading state machine.
pub struct SmoothFader {
    pub current_raw: i64,
    pub target_raw: i64,
    pub max_raw: i64,
    pub step_raw: i64,
}

impl SmoothFader {
    pub fn new(current_raw: i64, max_raw: i64) -> Self {
        Self {
            current_raw,
            target_raw: current_raw,
            max_raw,
            step_raw: (max_raw / 100).max(1), // ~1% per step
        }
    }

    pub fn set_target_pct(&mut self, pct: u8) {
        let clamped = pct.clamp(1, 100);
        self.target_raw = (clamped as i64 * self.max_raw + 50) / 100;
        let diff = (self.target_raw - self.current_raw).abs();
        self.step_raw = (diff / 10).max(self.max_raw / 200).max(1);
    }

    /// Ticks the fader towards the target raw brightness. Returns true if value changed.
    pub fn tick(&mut self) -> (i64, bool) {
        if self.current_raw == self.target_raw {
            return (self.current_raw, false);
        }

        if self.current_raw < self.target_raw {
            self.current_raw = (self.current_raw + self.step_raw).min(self.target_raw);
        } else {
            self.current_raw = (self.current_raw - self.step_raw).max(self.target_raw);
        }

        (self.current_raw, true)
    }
}

/// Learning tracker for internal panel manual adjustments.
pub struct LearningTracker {
    pub last_manual_pct: u8,
    pub manual_detected_time: Option<Instant>,
}

impl LearningTracker {
    pub fn new() -> Self {
        Self {
            last_manual_pct: 0,
            manual_detected_time: None,
        }
    }
}

pub fn get_current_minute_of_day() -> u16 {
    // Current local time minutes from midnight
    let now = chrono_or_std_now_minutes();
    now
}

fn chrono_or_std_now_minutes() -> u16 {
    // Standard library calculation using /etc/localtime or local time offset via libc/time
    let now_secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();

    // Use libc localtime_r if available or standard calculation
    let mut tm = [0i32; 16];
    unsafe {
        let time_val = now_secs as LibcTimeT;
        localtime_r_compat(&time_val, tm.as_mut_ptr());
    }
    let hour = tm[2] as u16; // tm_hour
    let min = tm[1] as u16;  // tm_min
    hour * 60 + min
}

type LibcTimeT = i64;

unsafe fn localtime_r_compat(time_p: *const LibcTimeT, result: *mut i32) {
    #[cfg(target_os = "linux")]
    extern "C" {
        fn localtime_r(time_p: *const LibcTimeT, result: *mut i32) -> *mut i32;
    }
    #[cfg(target_os = "linux")]
    {
        localtime_r(time_p, result);
    }
}

/// Runs the background adaptive daemon.
pub fn run_daemon(foreground: bool) {
    if !foreground {
        eprintln!("Running lbright daemon in background loop...");
    } else {
        println!("Starting lbright daemon (foreground mode)...");
    }

    let config_path = get_config_path();
    let state_dir = get_state_dir();
    let _ = fs::create_dir_all(&state_dir);

    let (mut config, warnings) = load_config(&config_path);
    for w in warnings {
        eprintln!("[lbright] Config warning: {}", w);
    }

    let mut last_config_mtime = fs::metadata(&config_path).ok().and_then(|m| m.modified().ok());
    let panel = InternalPanel::detect_primary();
    let als_sensor = AmbientSensor::detect();
    let mut ambient_tracker = AmbientTracker::new(config.general.ambient_average as usize);

    let ddc_worker = start_ddc_worker(
        Duration::from_secs(config.general.ddc_set_timeout_sec),
        Duration::from_secs(config.general.ddc_detect_timeout_sec),
        Duration::from_secs(config.general.ddc_cooldown_sec as u64),
    );

    let mut fader = panel.as_ref().map(|p| {
        let cur = p.get_raw().unwrap_or(p.max_raw / 2);
        SmoothFader::new(cur, p.max_raw)
    });

    let mut learning = LearningTracker::new();

    let mut last_profile_calc = Instant::now() - Duration::from_secs(3600); // Trigger immediately
    let mut last_ambient_check = Instant::now();
    let mut last_config_check = Instant::now();
    let mut last_ddc_rescan = Instant::now();
    let mut last_tick_instant = Instant::now();

    let mut current_internal_target_pct: u8 = 50;

    loop {
        thread_sleep_tick(Duration::from_millis(100));

        // Detect system sleep/resume via monotonic clock gap (> 5s jump)
        let elapsed_since_last_tick = last_tick_instant.elapsed();
        if elapsed_since_last_tick > Duration::from_secs(5) {
            eprintln!(
                "[lbright] System resume detected (gap of {:.1}s). Triggering profile recalculation and DDC rescan...",
                elapsed_since_last_tick.as_secs_f32()
            );
            last_profile_calc = Instant::now() - Duration::from_secs(3600);
            let _ = ddc_worker.tx.send(DdcCommand::Rescan);
        }
        last_tick_instant = Instant::now();

        // 1. Advance internal smooth fade state machine
        if let (Some(f), Some(p)) = (fader.as_mut(), panel.as_ref()) {
            if config.general.fade_internal {
                let (raw, changed) = f.tick();
                if changed {
                    let _ = p.set_raw(raw);
                }
            } else if f.current_raw != f.target_raw {
                f.current_raw = f.target_raw;
                let _ = p.set_raw(f.target_raw);
            }
        }

        // 2. Check pause state
        let pause_state = read_pause_state(&state_dir);
        let is_paused = pause_state.is_paused();

        // 3. Config mtime check (every 1 second)
        if last_config_check.elapsed() >= Duration::from_secs(1) {
            last_config_check = Instant::now();
            let cur_mtime = fs::metadata(&config_path).ok().and_then(|m| m.modified().ok());
            if cur_mtime != last_config_mtime {
                last_config_mtime = cur_mtime;
                let (reloaded_config, warnings) = load_config(&config_path);
                for w in warnings {
                    eprintln!("[lbright] Config reload warning: {}", w);
                }
                config = reloaded_config;
                ambient_tracker.set_capacity(config.general.ambient_average as usize);
                eprintln!("[lbright] Configuration reloaded.");
                // Trigger immediate profile recalculation
                last_profile_calc = Instant::now() - Duration::from_secs(3600);
            }
        }

        // 4. Ambient light sensor check (every ambient_poll_sec)
        if config.general.ambient && !is_paused && last_ambient_check.elapsed() >= Duration::from_secs(config.general.ambient_poll_sec as u64) {
            last_ambient_check = Instant::now();
            if let Some(sensor) = &als_sensor {
                if let Some(lux) = sensor.read_lux() {
                    let (_offset, changed) = ambient_tracker.evaluate_offset(lux, config.general.ambient_hysteresis_pct);
                    if changed {
                        // Ambient condition changed significantly, update targets
                        last_profile_calc = Instant::now() - Duration::from_secs(3600);
                    }
                }
            }
        }

        // 5. Profile evaluation (every interval_min)
        let interval_duration = Duration::from_secs((config.general.interval_min as u64 * 60).max(1));
        if !is_paused && last_profile_calc.elapsed() >= interval_duration {
            last_profile_calc = Instant::now();

            let cur_minutes = get_current_minute_of_day();
            let ambient_offset = if config.general.ambient {
                ambient_tracker.current_offset()
            } else {
                0
            };

            // Evaluate internal panel target
            if let Some(internal_dev) = config.get_internal() {
                if internal_dev.enabled {
                    let base_target = interpolate_linear(
                        &internal_dev.points,
                        cur_minutes,
                        config.general.min_internal,
                        config.general.max_internal,
                    );
                    let final_target = ((base_target as i32 + ambient_offset as i32)
                        .clamp(config.general.min_internal as i32, config.general.max_internal as i32))
                        as u8;

                    current_internal_target_pct = final_target;

                    if let Some(f) = fader.as_mut() {
                        f.set_target_pct(final_target);
                    }
                    let _ = write_device_state(&state_dir, "internal", final_target);
                }
            }

            // Evaluate external DDC targets
            for dev in &config.devices {
                if let DeviceId::Ddc(ddc_id) = &dev.id {
                    if dev.enabled {
                        let base_target = interpolate_linear(
                            &dev.points,
                            cur_minutes,
                            config.general.min_external,
                            config.general.max_external,
                        );
                        let final_target = ((base_target as i32 + ambient_offset as i32)
                            .clamp(config.general.min_external as i32, config.general.max_external as i32))
                            as u8;

                        let _ = ddc_worker.tx.send(DdcCommand::Set {
                            id: ddc_id.clone(),
                            pct: final_target,
                        });
                        let _ = write_device_state(&state_dir, &format!("ddc_{}", ddc_id), final_target);
                    }
                }
            }
        }

        // 6. Periodic DDC display rescan (every ddc_rescan_min minutes)
        if last_ddc_rescan.elapsed() >= Duration::from_secs(config.general.ddc_rescan_min as u64 * 60) {
            last_ddc_rescan = Instant::now();
            let _ = ddc_worker.tx.send(DdcCommand::Rescan);
        }

        // 7. Internal panel manual learning heuristic
        if config.general.learn_internal && !is_paused {
            if let Some(p) = &panel {
                if let Ok(cur_pct) = p.get_percent() {
                    let diff = (cur_pct as i32 - current_internal_target_pct as i32).abs();
                    if diff >= 5 {
                        if learning.last_manual_pct == cur_pct {
                            if let Some(t0) = learning.manual_detected_time {
                                // Persisted for at least 10 seconds
                                if t0.elapsed() >= Duration::from_secs(10) {
                                    let cur_minutes = get_current_minute_of_day();
                                    if let Some(internal_dev) = config.get_device_mut(&DeviceId::Internal(None)) {
                                        if let Some(nearest) = find_nearest_point(&internal_dev.points, cur_minutes) {
                                            eprintln!(
                                                "[lbright] Learned new manual preference: {}% for point {:02}{:02}",
                                                cur_pct,
                                                nearest / 60,
                                                nearest % 60
                                            );
                                            internal_dev.points.insert(nearest, cur_pct);
                                            current_internal_target_pct = cur_pct;
                                            let _ = save_config(&config_path, &config);
                                        }
                                    }
                                    learning.manual_detected_time = None;
                                }
                            }
                        } else {
                            learning.last_manual_pct = cur_pct;
                            learning.manual_detected_time = Some(Instant::now());
                        }
                    } else {
                        learning.manual_detected_time = None;
                    }
                }
            }
        }
    }
}

fn thread_sleep_tick(d: Duration) {
    std::thread::sleep(d);
}
