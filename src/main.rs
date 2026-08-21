mod ambient;
mod backlight;
mod config;
mod ddc;
mod daemon;
mod profile;
mod state;
mod tui;

use std::env;
use std::process::exit;

use backlight::InternalPanel;
use config::{
    get_config_path, get_legacy_config_path, load_config, migrate_legacy_config, save_config,
    DeviceId, DdcId,
};
use ddc::{ddc_set_vcp, scan_ddc_displays};
use state::{get_state_dir, parse_pause_arg, read_pause_state, set_pause_state, PauseState};

fn print_version() {
    println!("lbright {}", env!("CARGO_PKG_VERSION"));
}

fn print_help() {
    println!(
        r#"lbright {} - High-efficiency Adaptive Brightness System for Linux

USAGE:
    lbright <SUBCOMMAND> [OPTIONS]

SUBCOMMANDS:
    daemon [--foreground]              Run the background adaptive brightness daemon
    tui                                Launch interactive terminal menu
    status                             Show current devices, brightness, sensor, and pause state
    scan                               Scan and list internal panels and external DDC displays
    set <device> <0-100>               Manually set device brightness (e.g. 'internal', 'ddc:1')
    pause <duration|off|indefinite>    Pause or resume automatic brightness adjustments
    migrate [--dry-run]                Import legacy profiles.conf into config.ini
    version                            Print version information
    help                               Print this help message

DEVICE SYNTAX (for 'set'):
    internal                           Primary internal backlight
    internal:<name>                    Specific backlight (e.g. 'internal:intel_backlight')
    ddc:default                        Default external monitor
    ddc:<index>                        Specific display number (e.g. 'ddc:1')
    ddc:bus=<bus>                      Specific I2C bus (e.g. 'ddc:bus=7')
    ddc:serial=<sn>                    Specific monitor serial (e.g. 'ddc:serial=ABC123')

EXAMPLES:
    lbright status
    lbright set internal 60
    lbright set ddc:1 50
    lbright pause 30m
    lbright pause off
    lbright migrate --dry-run
"#,
        env!("CARGO_PKG_VERSION")
    );
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        print_help();
        exit(0);
    }

    let subcommand = args[1].to_ascii_lowercase();
    match subcommand.as_str() {
        "--version" | "-v" | "-V" | "version" => {
            print_version();
        }
        "daemon" => {
            let foreground = args.iter().any(|a| a == "--foreground" || a == "-f");
            daemon::run_daemon(foreground);
        }
        "tui" => {
            tui::run_tui();
        }
        "status" => {
            let config_path = get_config_path();
            let state_dir = get_state_dir();
            let (config, warnings) = load_config(&config_path);
            for w in warnings {
                eprintln!("Warning: {}", w);
            }
            tui::show_status(&config, &state_dir);
        }
        "scan" => {
            println!("=== Scanning Displays ===");
            let panels = InternalPanel::detect_all();
            println!("Internal Panels ({}):", panels.len());
            for p in panels {
                let cur = p
                    .get_percent()
                    .map(|v| format!("{}%", v))
                    .unwrap_or_else(|_| "Unknown".to_string());
                println!("  • {} (Current: {}, Max: {})", p.name, cur, p.max_raw);
            }

            println!("\nExternal DDC Displays:");
            let ddc = scan_ddc_displays(std::time::Duration::from_secs(10));
            if ddc.is_empty() {
                println!("  None found (make sure 'ddcutil' is installed and monitors support DDC/CI).");
            } else {
                for d in ddc {
                    println!(
                        "  • Display {}: Model='{}', Serial='{}', Bus={:?}",
                        d.display_index,
                        d.model.as_deref().unwrap_or("Unknown"),
                        d.serial.as_deref().unwrap_or("N/A"),
                        d.bus.unwrap_or(0)
                    );
                }
            }
        }
        "set" => {
            if args.len() < 4 {
                eprintln!("Error: 'set' requires <device> and <percent (0-100)>.");
                eprintln!("Example: lbright set internal 50");
                exit(1);
            }
            let dev_str = &args[2];
            let pct_str = &args[3];
            let pct: u8 = match pct_str.parse() {
                Ok(v) if v <= 100 => v,
                _ => {
                    eprintln!("Error: Brightness percentage must be between 0 and 100.");
                    exit(1);
                }
            };

            if let Ok(dev_id) = dev_str.parse::<DeviceId>() {
                match dev_id {
                    DeviceId::Internal(specific) => {
                        let panel = match specific {
                            Some(name) => InternalPanel::detect_by_name(&name),
                            None => InternalPanel::detect_primary(),
                        };
                        if let Some(p) = panel {
                            if let Err(e) = p.set_percent(pct) {
                                eprintln!("Failed to set internal backlight: {}", e);
                                exit(1);
                            } else {
                                println!("Set internal backlight [{}] to {}%", p.name, pct);
                            }
                        } else {
                            eprintln!("Error: No matching internal backlight panel found.");
                            exit(1);
                        }
                    }
                    DeviceId::Ddc(ddc_id) => {
                        let displays = scan_ddc_displays(std::time::Duration::from_secs(5));
                        let target_idx = displays
                            .iter()
                            .find(|d| d.matches(&ddc_id))
                            .map(|d| d.display_index)
                            .or_else(|| {
                                if let DdcId::Index(idx) = ddc_id {
                                    Some(idx)
                                } else if ddc_id == DdcId::Default && !displays.is_empty() {
                                    Some(displays[0].display_index)
                                } else {
                                    None
                                }
                            });

                        if let Some(idx) = target_idx {
                            if ddc_set_vcp(idx, pct, std::time::Duration::from_secs(5)) {
                                println!("Set DDC display {} to {}%", idx, pct);
                            } else {
                                eprintln!("Failed to set DDC brightness on display {}.", idx);
                                exit(1);
                            }
                        } else {
                            eprintln!("Error: Could not resolve external display matching '{}'.", dev_str);
                            exit(1);
                        }
                    }
                }
            } else {
                eprintln!("Error: Invalid device syntax '{}'. Use 'internal' or 'ddc:<id>'.", dev_str);
                exit(1);
            }
        }
        "pause" => {
            let state_dir = get_state_dir();
            if args.len() < 3 || args[2] == "status" {
                let p = read_pause_state(&state_dir);
                match p {
                    PauseState::Active => println!("Adaptive adjustments: ACTIVE"),
                    PauseState::PausedIndefinite => println!("Adaptive adjustments: PAUSED (Indefinitely)"),
                    PauseState::PausedUntil(_) => {
                        if let Some(sec) = p.remaining_seconds() {
                            println!("Adaptive adjustments: PAUSED ({}m {}s remaining)", sec / 60, sec % 60);
                        } else {
                            println!("Adaptive adjustments: ACTIVE");
                        }
                    }
                }
                return;
            }

            let dur_arg = &args[2];
            match parse_pause_arg(dur_arg) {
                Ok(new_state) => {
                    if let Err(e) = set_pause_state(&state_dir, &new_state) {
                        eprintln!("Failed to update pause state: {}", e);
                        exit(1);
                    } else {
                        match new_state {
                            PauseState::Active => println!("Adaptive brightness adjustments RESUMED."),
                            PauseState::PausedIndefinite => println!("Adaptive brightness adjustments PAUSED INDEFINITELY."),
                            PauseState::PausedUntil(ts) => {
                                let now = std::time::SystemTime::now()
                                    .duration_since(std::time::UNIX_EPOCH)
                                    .unwrap_or_default()
                                    .as_secs();
                                let diff = ts.saturating_sub(now);
                                println!("Adaptive brightness adjustments PAUSED for {} minutes.", diff / 60);
                            }
                        }
                    }
                }
                Err(err) => {
                    eprintln!("Error: {}", err);
                    exit(1);
                }
            }
        }
        "migrate" => {
            let dry_run = args.iter().any(|a| a == "--dry-run");
            let legacy_path = get_legacy_config_path();
            let config_path = get_config_path();

            println!("=== LBrightness Migration Tool ===");
            println!("Reading legacy configuration from: {}", legacy_path.display());

            match migrate_legacy_config(&legacy_path) {
                Ok(result) => {
                    println!("Successfully parsed {} points from legacy config!", result.points_migrated);
                    for w in &result.warnings {
                        println!("Notice: {}", w);
                    }
                    if dry_run {
                        println!("\n--- Dry Run Preview of {} ---", config_path.display());
                        println!("{}", result.config.to_ini_string());
                        println!("Dry run complete. No files were written.");
                    } else {
                        if let Err(e) = save_config(&config_path, &result.config) {
                            eprintln!("Failed to write new config file: {}", e);
                            exit(1);
                        } else {
                            println!("\nNew configuration written successfully to: {}", config_path.display());
                            println!("Original legacy file was left untouched: {}", legacy_path.display());
                        }
                    }
                }
                Err(e) => {
                    eprintln!("Migration failed: {}", e);
                    exit(1);
                }
            }
        }
        "help" | "-h" | "--help" => {
            print_help();
        }
        _ => {
            eprintln!("Unknown command: '{}'. Run 'lbright help' for usage.", subcommand);
            exit(1);
        }
    }
}
