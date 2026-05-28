## Add MCAP sensor data logger for replay and analysis in Foxglove Studio

### Motivation

There is currently no built-in way to record and replay sensor data from RoSys robots. When debugging driving behavior, GNSS issues, or IMU drift, developers have to rely on log files and manual reconstruction. An MCAP-based recording system enables structured, timestamped data capture that can be visualized and analyzed in Foxglove Studio.

### Implementation

- New `rosys.recording` module with `McapLogger` class that writes MCAP files with JSON-encoded messages
- Supports automatic file rotation by size and disk budget enforcement (oldest files deleted when budget exceeded)
- Each hardware/driving module registers its own topics via `register_mcap_topics()`:
  - `/gnss` (foxglove.LocationFix) and `/gnss/detailed` (full measurement with std devs, quality, satellites)
  - `/imu` (roll/pitch/yaw + angular velocities + gyro calibration)
  - `/wheels/commanded` and `/wheels/measured` (linear/angular velocities)
  - `/odometry/pose` (x, y, yaw)
  - `/driver/state` (carrot pose, curvature, turn angle, spline progress)
- New `DriveState.spline_t` field and `DRIVE_STATE_UPDATED` event on `Driver`
- New `VELOCITY_COMMANDED` event on `Wheels`
- `DriveState` exported from `rosys.driving`
- BMS message parsing handles invalid messages gracefully instead of crashing
- Includes `developer_ui()` for monitoring recording status
- Adds `mcap`, `lz4`, and `zstandard` as new dependencies

### Progress

- [ ] I chose a meaningful title that completes the sentence: "If applied, this PR will..."
- [ ] I chose meaningful labels (if GitHub allows me to so).
- [ ] The implementation is complete.
- [ ] Pytests have been added (or are not necessary).
- [ ] Documentation has been added (or is not necessary).
