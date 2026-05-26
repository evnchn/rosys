# MCAP Topics Reference

All data is stored in [MCAP](https://mcap.dev/) format with JSON encoding and zstd compression.
Every message carries a nanosecond timestamp. Files are written to `~/.rosys/mcap/` by default.

Open recordings in [Foxglove Studio](https://foxglove.dev/) for visualization and replay.

## Topics

### `/gnss` — GPS Position (Foxglove Map)

Schema: `foxglove.LocationFix` — automatically recognized by Foxglove's Map panel.

| Field       | Type   | Unit    | Description              |
|-------------|--------|---------|--------------------------|
| `latitude`  | number | degrees | WGS84 latitude           |
| `longitude` | number | degrees | WGS84 longitude          |
| `altitude`  | number | meters  | Altitude above sea level |

**Timestamp source:** `GnssMeasurement.time`

---

### `/gnss/detailed` — Full GNSS Debug Data

Schema: `GnssMeasurement`

| Field               | Type    | Unit    | Description                                      |
|---------------------|---------|---------|--------------------------------------------------|
| `latitude_deg`      | number  | degrees | WGS84 latitude                                   |
| `longitude_deg`     | number  | degrees | WGS84 longitude                                  |
| `heading_deg`       | number  | degrees | Heading from GNSS                                |
| `latitude_std_dev`  | number  | meters  | Latitude standard deviation                      |
| `longitude_std_dev` | number  | meters  | Longitude standard deviation                     |
| `heading_std_dev`   | number  | degrees | Heading standard deviation                       |
| `gps_quality`       | integer | —       | Quality indicator (0=invalid, 1=GPS, 4=RTK fixed)|
| `gps_quality_name`  | string  | —       | Human-readable quality name                      |
| `num_satellites`    | integer | —       | Number of visible satellites                     |
| `hdop`              | number  | —       | Horizontal dilution of precision                 |
| `altitude`          | number  | meters  | Altitude above sea level                         |

**Timestamp source:** `GnssMeasurement.time`

---

### `/imu` — IMU Orientation & Angular Velocity

Schema: `ImuMeasurement`

| Field                    | Type   | Unit  | Description           |
|--------------------------|--------|-------|-----------------------|
| `roll`                   | number | rad   | Roll angle            |
| `pitch`                  | number | rad   | Pitch angle           |
| `yaw`                    | number | rad   | Yaw angle             |
| `angular_velocity_roll`  | number | rad/s | Roll rate             |
| `angular_velocity_pitch` | number | rad/s | Pitch rate            |
| `angular_velocity_yaw`   | number | rad/s | Yaw rate              |
| `gyro_calibration`       | number | —     | Gyroscope calibration |

**Timestamp source:** `ImuMeasurement.time`

---

### `/wheels/measured` — Actual Wheel Velocity (Ist)

Schema: `WheelVelocityMeasured`

| Field     | Type   | Unit  | Description                    |
|-----------|--------|-------|--------------------------------|
| `linear`  | number | m/s   | Measured linear velocity       |
| `angular` | number | rad/s | Measured angular velocity      |

**Timestamp source:** `Velocity.time` (from hardware encoder readings)

---

### `/wheels/commanded` — Commanded Wheel Velocity (Soll)

Schema: `WheelVelocityCommanded`

| Field     | Type   | Unit  | Description                    |
|-----------|--------|-------|--------------------------------|
| `linear`  | number | m/s   | Commanded linear velocity      |
| `angular` | number | rad/s | Commanded angular velocity     |

**Timestamp source:** `Velocity.time` (from `wheels.drive()` call)

---

### `/odometry/pose` — Raw Wheel Odometry

Schema: `OdometryPose`

| Field | Type   | Unit   | Description                          |
|-------|--------|--------|--------------------------------------|
| `x`   | number | meters | Odometry X position (local frame)    |
| `y`   | number | meters | Odometry Y position (local frame)    |
| `yaw` | number | rad    | Odometry heading                     |

**Timestamp source:** `Pose.time` (from `POSE_UPDATED` event)

---

### `/driver/state` — Path Following State

Schema: `DriveState`

Emitted every control cycle (~10 Hz) while following a spline.

| Field        | Type    | Unit | Description                                      |
|--------------|---------|------|--------------------------------------------------|
| `carrot_x`   | number  | m    | Carrot (look-ahead target) X position             |
| `carrot_y`   | number  | m    | Carrot (look-ahead target) Y position             |
| `carrot_yaw` | number  | rad  | Carrot heading on spline                          |
| `curvature`  | number  | 1/m  | Steering curvature (positive = left turn)         |
| `turn_angle` | number  | rad  | Angle between robot heading and carrot direction  |
| `spline_t`   | number  | —    | Progress along spline (0 = start, 1 = end, >1 = overshoot) |
| `backward`   | boolean | —    | True if driving in reverse                        |

**Timestamp source:** `rosys.time()` (control loop timestamp)

---

## File Management

| Setting             | Default          | Description                              |
|---------------------|------------------|------------------------------------------|
| `output_dir`        | `~/.rosys/mcap/` | Directory for MCAP files                 |
| `max_file_size_mb`  | 100 MB           | Rotate to new file after this size       |
| `max_total_size_mb` | 1000 MB          | Delete oldest files when budget exceeded |
| `compression`       | `zstd`           | Compression (`zstd`, `lz4`, `none`)      |

Typical size: ~18 MB per hour (zstd compressed, all topics active).
