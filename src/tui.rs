use std::io::{self, BufRead, Write};
use std::path::Path;

use crate::ambient::AmbientSensor;
use crate::backlight::InternalPanel;
use crate::config::{
    get_config_path, get_legacy_config_path, load_config, migrate_legacy_config, save_config,
    Config, DeviceConfig, DeviceId,
};
use crate::ddc::scan_ddc_displays;
use crate::profile::{interpolate_linear, minutes_to_hhmm, parse_time_str};
use crate::state::{get_state_dir, parse_pause_arg, read_pause_state, set_pause_state, PauseState};

fn read_line(prompt: &str) -> String {
    print!("{}", prompt);
    let _ = io::stdout().flush();
    let stdin = io::stdin();
    let mut line = String::new();
    let _ = stdin.lock().read_line(&mut line);
    line.trim().to_string()
}

pub fn run_tui() {
    let config_path = get_config_path();
    let state_dir = get_state_dir();

    println!("\n==========================================");
    println!("       LBrightness Control Menu");
    println!("==========================================");

    loop {
        let (config, warnings) = load_config(&config_path);
        for w in warnings {
            println!("Warning: {}", w);
        }

        let pause = read_pause_state(&state_dir);
        let pause_str = match &pause {
            PauseState::Active => "Active".to_string(),
            PauseState::PausedIndefinite => "Paused (Indefinite)".to_string(),
            PauseState::PausedUntil(_) => {
                if let Some(sec) = pause.remaining_seconds() {
                    format!("Paused ({}m remaining)", sec / 60)
                } else {
                    "Active".to_string()
                }
            }
        };

        println!("\n--- Main Menu --- [State: {}]", pause_str);
        println!("1) Live Status & Devices");
        println!("2) Edit Internal Brightness Curve");
        println!("3) Edit External Display Profiles");
        println!("4) Toggle Ambient Sensor (Currently: {})", if config.general.ambient { "Enabled" } else { "Disabled" });
        println!("5) Pause / Resume Adjustments");
        println!("6) Rescan Displays");
        println!("7) Migrate Old Config (profiles.conf)");
        println!("8) Reload Daemon");
        println!("9) Exit");

        let choice = read_line("\nSelect option [1-9]: ");
        match choice.as_str() {
            "1" => show_status(&config, &state_dir),
            "2" => edit_curve(&config_path, &config, DeviceId::Internal(None)),
            "3" => select_external_device(&config_path, &config),
            "4" => toggle_ambient(&config_path, &config),
            "5" => menu_pause(&state_dir),
            "6" => menu_rescan(),
            "7" => menu_migrate(&config_path),
            "8" => {
                println!("Triggering daemon reload...");
                let _ = save_config(&config_path, &config);
                println!("Done. Daemon will reload within 1 second.");
            }
            "9" | "q" | "exit" => {
                println!("Goodbye!");
                break;
            }
            _ => println!("Invalid option, please try again."),
        }
    }
}

pub fn show_status(config: &Config, state_dir: &Path) {
    println!("\n=== System Status ===");
    println!("Config path: {}", get_config_path().display());
    println!("State dir:   {}", state_dir.display());

    let pause = read_pause_state(state_dir);
    println!("Adaptive Mode: {}", if pause.is_paused() { "PAUSED" } else { "RUNNING" });
    if let Some(rem) = pause.remaining_seconds() {
        println!("Pause time remaining: {}m {}s", rem / 60, rem % 60);
    }

    println!("\n--- Internal Backlight ---");
    let panels = InternalPanel::detect_all();
    if panels.is_empty() {
        println!("No internal backlight panels detected in sysfs.");
    } else {
        for p in panels {
            let cur_pct = p.get_percent().map(|v| format!("{}%", v)).unwrap_or_else(|e| format!("Error: {}", e));
            println!("• [{}] Current: {}, Max Raw: {}", p.name, cur_pct, p.max_raw);
        }
    }

    println!("\n--- Ambient Light Sensor (ALS) ---");
    if let Some(als) = AmbientSensor::detect() {
        let lux = als.read_lux().map(|v| format!("{} lux", v)).unwrap_or_else(|| "Unavailable".to_string());
        println!("Sensor Path: {}", als.path.display());
        println!("Current Reading: {} (Ambient config: {})", lux, if config.general.ambient { "Enabled" } else { "Disabled" });
    } else {
        println!("No IIO ambient light sensors detected.");
    }

    println!("\n--- External Displays (DDC/CI) ---");
    let ddc_displays = scan_ddc_displays(std::time::Duration::from_secs(5));
    if ddc_displays.is_empty() {
        println!("No external DDC/CI displays detected (or ddcutil not installed).");
    } else {
        for d in ddc_displays {
            println!(
                "• Display {}: Model='{}', Serial='{}', Bus={:?}",
                d.display_index,
                d.model.as_deref().unwrap_or("Unknown"),
                d.serial.as_deref().unwrap_or("N/A"),
                d.bus.unwrap_or(0)
            );
        }
    }
}

fn edit_curve(config_path: &Path, config: &Config, dev_id: DeviceId) {
    let mut updated_config = config.clone();
    let dev = match updated_config.get_device_mut(&dev_id) {
        Some(d) => d,
        None => {
            updated_config.devices.push(DeviceConfig::with_default_curve(dev_id.clone()));
            updated_config.get_device_mut(&dev_id).unwrap()
        }
    };

    loop {
        println!("\n=== Editing Curve for [{}] ===", dev.id);
        println!("Points (Time -> Target %):");
        let keys: Vec<u16> = dev.points.keys().copied().collect();
        for (i, &m) in keys.iter().enumerate() {
            let pct = dev.points.get(&m).unwrap();
            println!("  {}) {} -> {}%", i + 1, minutes_to_hhmm(m), pct);
        }

        println!("\nOptions: (a)dd point, (e)dit point, (d)elete point, (t)est point, (s)ave, (b)ack");
        let opt = read_line("Select action: ");
        match opt.as_str() {
            "a" | "add" => {
                let time_str = read_line("Enter time (HHMM e.g. 0800): ");
                if let Some(mins) = parse_time_str(&time_str) {
                    let pct_str = read_line("Enter brightness (0-100%): ");
                    if let Ok(pct) = pct_str.parse::<u8>() {
                        dev.points.insert(mins, pct.clamp(0, 100));
                        println!("Point added.");
                    } else {
                        println!("Invalid brightness percentage.");
                    }
                } else {
                    println!("Invalid time format.");
                }
            }
            "e" | "edit" => {
                let num_str = read_line("Enter point number to edit: ");
                if let Ok(num) = num_str.parse::<usize>() {
                    if num >= 1 && num <= keys.len() {
                        let m = keys[num - 1];
                        let pct_str = read_line(&format!("Enter new brightness for {} (0-100%): ", minutes_to_hhmm(m)));
                        if let Ok(pct) = pct_str.parse::<u8>() {
                            dev.points.insert(m, pct.clamp(0, 100));
                            println!("Point updated.");
                        } else {
                            println!("Invalid brightness percentage.");
                        }
                    } else {
                        println!("Invalid point number.");
                    }
                }
            }
            "d" | "delete" => {
                let num_str = read_line("Enter point number to delete: ");
                if let Ok(num) = num_str.parse::<usize>() {
                    if num >= 1 && num <= keys.len() {
                        let m = keys[num - 1];
                        dev.points.remove(&m);
                        println!("Point deleted.");
                    } else {
                        println!("Invalid point number.");
                    }
                }
            }
            "t" | "test" => {
                let time_str = read_line("Enter test time (HHMM e.g. 1430): ");
                if let Some(mins) = parse_time_str(&time_str) {
                    let target = interpolate_linear(&dev.points, mins, 0, 100);
                    println!("Calculated target for {}: {}%", minutes_to_hhmm(mins), target);
                } else {
                    println!("Invalid time format.");
                }
            }
            "s" | "save" => {
                if let Err(e) = save_config(config_path, &updated_config) {
                    println!("Failed to save configuration: {}", e);
                } else {
                    println!("Configuration successfully saved!");
                }
                break;
            }
            "b" | "back" | "q" => break,
            _ => println!("Invalid option."),
        }
    }
}

fn select_external_device(config_path: &Path, config: &Config) {
    println!("\n=== External Display Profiles ===");
    let ddc_devices: Vec<&DeviceConfig> = config
        .devices
        .iter()
        .filter(|d| matches!(d.id, DeviceId::Ddc(_)))
        .collect();

    for (i, dev) in ddc_devices.iter().enumerate() {
        println!("  {}) [{}] (Enabled: {})", i + 1, dev.id, dev.enabled);
    }
    println!("  n) Add new device section");
    println!("  b) Back");

    let choice = read_line("Select device to edit: ");
    if choice == "b" || choice == "back" {
        return;
    }
    if choice == "n" || choice == "new" {
        let name = read_line("Enter DDC identifier (e.g. default, serial=ABC123, bus=7): ");
        if let Ok(dev_id) = format!("ddc:{}", name).parse::<DeviceId>() {
            edit_curve(config_path, config, dev_id);
        } else {
            println!("Invalid device identifier.");
        }
        return;
    }

    if let Ok(num) = choice.parse::<usize>() {
        if num >= 1 && num <= ddc_devices.len() {
            let id = ddc_devices[num - 1].id.clone();
            edit_curve(config_path, config, id);
        } else {
            println!("Invalid selection.");
        }
    }
}

fn toggle_ambient(config_path: &Path, config: &Config) {
    let mut updated = config.clone();
    updated.general.ambient = !updated.general.ambient;
    if let Err(e) = save_config(config_path, &updated) {
        println!("Failed to save configuration: {}", e);
    } else {
        println!(
            "Ambient sensor is now {}.",
            if updated.general.ambient { "ENABLED" } else { "DISABLED" }
        );
    }
}

fn menu_pause(state_dir: &Path) {
    println!("\n=== Pause / Resume Adaptive Control ===");
    println!("1) Resume adjustments (Off)");
    println!("2) Pause for 15 minutes");
    println!("3) Pause for 30 minutes");
    println!("4) Pause for 1 hour");
    println!("5) Pause for 3 hours");
    println!("6) Pause for 8 hours");
    println!("7) Pause indefinitely");
    println!("b) Back");

    let choice = read_line("Select option: ");
    let pause_state = match choice.as_str() {
        "1" => parse_pause_arg("off"),
        "2" => parse_pause_arg("15m"),
        "3" => parse_pause_arg("30m"),
        "4" => parse_pause_arg("1h"),
        "5" => parse_pause_arg("3h"),
        "6" => parse_pause_arg("8h"),
        "7" => parse_pause_arg("indefinite"),
        "b" => return,
        _ => {
            println!("Invalid choice.");
            return;
        }
    };

    if let Ok(state) = pause_state {
        if let Err(e) = set_pause_state(state_dir, &state) {
            println!("Failed to set pause state: {}", e);
        } else {
            println!("Pause state updated successfully.");
        }
    }
}

fn menu_rescan() {
    println!("\nScanning display hardware...");
    let panels = InternalPanel::detect_all();
    println!("Internal panels found: {}", panels.len());
    for p in panels {
        println!("  • /sys/class/backlight/{}", p.name);
    }

    let ddc = scan_ddc_displays(std::time::Duration::from_secs(10));
    println!("External DDC displays found: {}", ddc.len());
    for d in ddc {
        println!(
            "  • Display {}: Model='{}', Serial='{}'",
            d.display_index,
            d.model.as_deref().unwrap_or("Unknown"),
            d.serial.as_deref().unwrap_or("N/A")
        );
    }
    println!("Scan completed.");
}

fn menu_migrate(config_path: &Path) {
    let legacy_path = get_legacy_config_path();
    println!("\n=== Migrate Legacy Configuration ===");
    println!("Legacy path: {}", legacy_path.display());
    println!("Target path: {}", config_path.display());

    let confirm = read_line("Run migration now? (y/N): ");
    if confirm.eq_ignore_ascii_case("y") {
        match migrate_legacy_config(&legacy_path) {
            Ok(res) => {
                println!("Successfully parsed legacy configuration!");
                println!("Points migrated: {}", res.points_migrated);
                for w in res.warnings {
                    println!("Notice: {}", w);
                }
                if let Err(e) = save_config(config_path, &res.config) {
                    println!("Failed to write new config file: {}", e);
                } else {
                    println!("New configuration saved to {}", config_path.display());
                }
            }
            Err(e) => println!("Migration error: {}", e),
        }
    }
}
