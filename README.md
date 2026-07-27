# spacemouse_ros2

ROS 2 driver for the [3Dconnexion SpaceMouse Compact](https://3dconnexion.com/us/product/spacemouse-compact/). Reads the device via [pyspacemouse](https://github.com/JakubAndrysek/PySpaceMouse) (hidapi) and publishes `sensor_msgs/Joy`, `geometry_msgs/TwistStamped`, and/or `geometry_msgs/Twist`, with per-axis remap/invert driven entirely by a YAML config — no code changes needed to adapt to how the device is mounted or oriented.

ament_python package, ROS 2 Jazzy.

## Topics

Launched via `spacemouse_ros2.launch.py`, the node runs under the `spacemouse` namespace, so topics resolve to:

| Topic | Type | Notes |
|---|---|---|
| `/spacemouse/joy` | `sensor_msgs/Joy` | `axes = [x, y, z, roll, pitch, yaw]` (raw, ±1.0 range, after axis-map/invert/deadzone). `buttons` length depends on the connected device. |
| `/spacemouse/twiststamped` | `geometry_msgs/TwistStamped` | Same six axes scaled by `linear_scale` / `angular_scale`. |
| `/spacemouse/twist` | `geometry_msgs/Twist` | Same as `twiststamped` but unstamped, for consumers that expect a plain `Twist` (e.g. `cmd_vel`-style inputs). Off by default. |

All three topics can be independently enabled/disabled via `publish_joy` / `publish_twiststamped` / `publish_twist`. This matches the `/spacemouse/joy` remap target already used by `lekiwi_ros2` and `lerre_ros2`'s direct-servo launch files (`wheel_control_mode:=joy`).

To run multiple robots/namespaces on the same ROS graph, prepend a prefix with the `namespace_prefix` launch argument instead of the default `/spacemouse/...`:

```bash
ros2 launch spacemouse_ros2 spacemouse_ros2.launch.py namespace_prefix:=robot1
# -> /robot1/spacemouse/joy, /robot1/spacemouse/twiststamped
```

Leave it unset (the default) for the plain `/spacemouse/...` topics.

## Configuration

Edit `config/spacemouse.yaml` (or pass your own via the `config_file` launch argument):

```yaml
spacemouse_node:
  ros__parameters:
    device_name: ""        # empty = auto-detect first supported 3Dconnexion device
    publish_rate: 100.0
    frame_id: "spacemouse"
    publish_joy: true
    publish_twiststamped: true
    publish_twist: false
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

The SpaceMouse is a raw HID device. By default Linux creates `/dev/hidraw*` nodes as `root:root` mode `0600` — no exceptions for "safe" devices, since HID also covers keyboards — so the user running the node needs an explicit udev rule granting access; there's no way around installing one.

**If you're using this workspace's devcontainer** (`.devcontainer/devcontainer.json`), the container bind-mounts `/dev` straight from the host (`--mount=type=bind,source=/dev,target=/dev`) rather than presenting its own virtual `/dev`. That means:

- The udev rule must be installed on the **host OS**, not inside the container — a rule copied into the container's `/etc/udev/rules.d` has no effect, because the container has no running udev daemon to apply it.
- `udevadm` isn't installed inside the container at all; run the reload from a regular host terminal (outside VS Code's container shell).

From a host terminal:

```bash
sudo cp udev/70-spacemouse.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

Then unplug/replug the SpaceMouse (or reboot) so it's recreated under the new rule, and make sure your user is in the `plugdev` group (`sudo usermod -aG plugdev $USER`, then log out/in). Because `/dev` is bind-mounted live, the fixed permissions show up inside the container automatically — no container restart needed.

If the node logs "Failed to open SpaceMouse device" or keeps retrying, this is almost always a permissions issue — check `ls -l /dev/hidraw*` for the device's owning group. As a one-off, session-only workaround (does not survive replug/reboot): `sudo chown root:plugdev /dev/hidrawN && sudo chmod 660 /dev/hidrawN`.

## Dependencies

`pyspacemouse` is pip-only (not a rosdep key) — installed via the workspace's `pixi.toml` `[pypi-dependencies]`, not `package.xml`. It's pinned to `>=2.0` because this driver uses pyspacemouse 2.0's object-based device API (`pyspacemouse.open()` returns a `SpaceMouseDevice` with `.read()`/`.close()` methods); pre-2.0 releases used a different module-level API and are not compatible with this node.

`pyspacemouse` also needs the native `libhidapi` shared library at runtime (via its `easyhid` dependency, which loads it directly with `cffi`/`dlopen`). This workspace provides it as the conda-forge `libhidapi` package in `pixi.toml`'s `[dependencies]`. Note this is *not* the same as the PyPI `hidapi` wheel — that wheel bundles its own private copy of the library that `easyhid` can't see, so installing it does not satisfy this requirement.
