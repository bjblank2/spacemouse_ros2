# spacemouse_ros2

ROS 2 driver for the [3Dconnexion SpaceMouse Compact](https://3dconnexion.com/us/product/spacemouse-compact/). Reads the device via [pyspacemouse](https://github.com/JakubAndrysek/PySpaceMouse) (hidapi) and publishes `sensor_msgs/Joy` and/or `geometry_msgs/TwistStamped`, with per-axis remap/invert driven entirely by a YAML config — no code changes needed to adapt to how the device is mounted or oriented.

ament_python package, ROS 2 Jazzy.

## Topics

Launched via `spacemouse_ros2.launch.py`, the node runs under the `spacemouse` namespace, so topics resolve to:

| Topic | Type | Notes |
|---|---|---|
| `/spacemouse/joy` | `sensor_msgs/Joy` | `axes = [x, y, z, roll, pitch, yaw]` (raw, ±1.0 range, after axis-map/invert/deadzone). `buttons` length depends on the connected device. |
| `/spacemouse/twist_stamped` | `geometry_msgs/TwistStamped` | Same six axes scaled by `linear_scale` / `angular_scale`. |

Both topics can be independently enabled/disabled via `publish_joy` / `publish_twist`. This matches the `/spacemouse/joy` remap target already used by `lekiwi_ros2` and `lerre_ros2`'s direct-servo launch files (`wheel_control_mode:=joy`).

## Configuration

Edit `config/spacemouse.yaml` (or pass your own via the `config_file` launch argument):

```yaml
spacemouse_node:
  ros__parameters:
    device_name: ""        # empty = auto-detect first supported 3Dconnexion device
    publish_rate: 100.0
    frame_id: "spacemouse"
    publish_joy: true
    publish_twist: true
    deadzone: 0.05
    linear_scale: 1.0
    angular_scale: 1.0
    axis_map:
      x:     {source: "x",     invert: false}
      y:     {source: "y",     invert: false}
      z:     {source: "z",     invert: false}
      roll:  {source: "roll",  invert: false}
      pitch: {source: "pitch", invert: false}
      yaw:   {source: "yaw",   invert: false}
```

Each output axis (`x, y, z, roll, pitch, yaw`) can pull from any raw SpaceMouse axis via `source`, and flip sign via `invert: true`. For example, to swap X and Y and invert yaw:

```yaml
axis_map:
  x: {source: "y", invert: false}
  y: {source: "x", invert: false}
  yaw: {source: "yaw", invert: true}
```

## Usage

```bash
ros2 launch spacemouse_ros2 spacemouse_ros2.launch.py
ros2 topic echo /spacemouse/joy
```

## Device permissions

The SpaceMouse is a raw HID device, so the user running the node needs read/write access to it. Install the provided udev rule on the host (not just in the container, unless the container manages its own udev):

```bash
sudo cp udev/70-spacemouse.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

Then make sure your user is in the `plugdev` group (`sudo usermod -aG plugdev $USER`, then log out/in). If the node logs "Failed to open SpaceMouse device" or keeps retrying, this is almost always a permissions issue — check `ls -l /dev/hidraw*` for the device's owning group.

## Dependencies

`pyspacemouse` and `hidapi` are pip-only (not rosdep keys) — installed via the workspace's `pixi.toml` `[pypi-dependencies]`, not `package.xml`.
