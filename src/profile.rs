use std::collections::BTreeMap;

/// Formats minutes from midnight into HHMM format (e.g. 540 -> "0900", 1439 -> "2359").
pub fn minutes_to_hhmm(minutes: u16) -> String {
    let m = minutes % 1440;
    format!("{:02}{:02}", m / 60, m % 60)
}

/// Parses "HHMM" or "HH:MM" format into minutes from midnight (0..=1439).
pub fn parse_time_str(s: &str) -> Option<u16> {
    let clean = s.trim();
    if clean.len() == 4 && clean.chars().all(|c| c.is_ascii_digit()) {
        let h: u16 = clean[..2].parse().ok()?;
        let m: u16 = clean[2..].parse().ok()?;
        if h < 24 && m < 60 {
            return Some(h * 60 + m);
        }
    } else if let Some((h_str, m_str)) = clean.split_once(':') {
        let h: u16 = h_str.trim().parse().ok()?;
        let m: u16 = m_str.trim().parse().ok()?;
        if h < 24 && m < 60 {
            return Some(h * 60 + m);
        }
    }
    None
}

/// Linearly interpolates the brightness target percentage for a given minute of the day (0..=1439),
/// wrapping smoothly across midnight. Clamps the result between min_pct and max_pct.
pub fn interpolate_linear(
    points: &BTreeMap<u16, u8>,
    now_minutes: u16,
    min_pct: u8,
    max_pct: u8,
) -> u8 {
    if points.is_empty() {
        return min_pct.max(50).min(max_pct);
    }
    if points.len() == 1 {
        let &val = points.values().next().unwrap();
        return val.max(min_pct).min(max_pct);
    }

    let cur = now_minutes % 1440;
    let keys: Vec<u16> = points.keys().copied().collect();

    let (l_min, l_val, u_min, u_val) = if cur < keys[0] {
        // Before the first point of the day: wrap from the last point of previous day
        let last_key = *keys.last().unwrap();
        (
            last_key as i32 - 1440,
            *points.get(&last_key).unwrap() as i32,
            keys[0] as i32,
            *points.get(&keys[0]).unwrap() as i32,
        )
    } else if cur > *keys.last().unwrap() {
        // After the last point of the day: wrap to the first point of the next day
        let last_key = *keys.last().unwrap();
        (
            last_key as i32,
            *points.get(&last_key).unwrap() as i32,
            keys[0] as i32 + 1440,
            *points.get(&keys[0]).unwrap() as i32,
        )
    } else {
        // Between two points within the day
        let mut lower = (0, 0);
        let mut upper = (0, 0);
        for i in 0..keys.len() - 1 {
            if keys[i] <= cur && cur <= keys[i + 1] {
                lower = (keys[i] as i32, *points.get(&keys[i]).unwrap() as i32);
                upper = (keys[i + 1] as i32, *points.get(&keys[i + 1]).unwrap() as i32);
                break;
            }
        }
        (lower.0, lower.1, upper.0, upper.1)
    };

    let denom = u_min - l_min;
    let raw_target = if denom == 0 {
        l_val
    } else {
        l_val + ((cur as i32 - l_min) * (u_val - l_val)) / denom
    };

    let target = raw_target.clamp(min_pct as i32, max_pct as i32) as u8;
    target
}

/// Finds the nearest configured time point (in minutes) to the current time, wrapping midnight.
pub fn find_nearest_point(points: &BTreeMap<u16, u8>, now_minutes: u16) -> Option<u16> {
    if points.is_empty() {
        return None;
    }
    let cur = now_minutes % 1440;
    let mut nearest = 0;
    let mut min_dist = u16::MAX;

    for &p in points.keys() {
        let d1 = if cur >= p { cur - p } else { p - cur };
        let d2 = 1440 - d1;
        let dist = d1.min(d2);
        if dist < min_dist {
            min_dist = dist;
            nearest = p;
        }
    }
    Some(nearest)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_time_parsing() {
        assert_eq!(parse_time_str("0000"), Some(0));
        assert_eq!(parse_time_str("0730"), Some(450));
        assert_eq!(parse_time_str("07:30"), Some(450));
        assert_eq!(parse_time_str("2359"), Some(1439));
        assert_eq!(parse_time_str("2400"), None);
        assert_eq!(parse_time_str("invalid"), None);
    }

    #[test]
    fn test_linear_interpolation() {
        let mut points = BTreeMap::new();
        points.insert(0, 20); // 00:00 -> 20%
        points.insert(360, 50); // 06:00 -> 50%
        points.insert(720, 80); // 12:00 -> 80%
        points.insert(1080, 50); // 18:00 -> 50%

        // Exact point hits
        assert_eq!(interpolate_linear(&points, 0, 5, 100), 20);
        assert_eq!(interpolate_linear(&points, 360, 5, 100), 50);
        assert_eq!(interpolate_linear(&points, 720, 5, 100), 80);

        // Halfway interpolation between 06:00 (50%) and 12:00 (80%) -> 09:00 (65%)
        assert_eq!(interpolate_linear(&points, 540, 5, 100), 65);

        // Wrap around midnight between 18:00 (50%) and 00:00 (20%) -> 21:00 (35%)
        assert_eq!(interpolate_linear(&points, 1260, 5, 100), 35);
    }

    #[test]
    fn test_clamp_limits() {
        let mut points = BTreeMap::new();
        points.insert(0, 10);
        points.insert(720, 95);

        assert_eq!(interpolate_linear(&points, 0, 20, 80), 20); // clamped at min 20
        assert_eq!(interpolate_linear(&points, 720, 20, 80), 80); // clamped at max 80
    }

    #[test]
    fn test_find_nearest_point() {
        let mut points = BTreeMap::new();
        points.insert(0, 20); // 00:00
        points.insert(360, 50); // 06:00
        points.insert(1200, 80); // 20:00

        assert_eq!(find_nearest_point(&points, 30), Some(0));
        assert_eq!(find_nearest_point(&points, 300), Some(360));
        assert_eq!(find_nearest_point(&points, 1400), Some(0)); // 23:20 is closer to 00:00 (40 mins) than 20:00 (200 mins)
    }
}
