#!/usr/bin/env python3

"""
ROS 2 driver node for the 3Dconnexion SpaceMouse Compact.

Reads raw axis/button state via pyspacemouse and publishes it as
sensor_msgs/Joy and/or geometry_msgs/TwistStamped, with axis source
selection and inversion driven entirely by ROS parameters (see
config/spacemouse.yaml).
"""

from geometry_msgs.msg import TwistStamped
import pyspacemouse
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy

AXIS_NAMES = ('x', 'y', 'z', 'roll', 'pitch', 'yaw')

# The device reports translation and rotation as separate HID packets, and
# each read() call drains only one packet from the kernel's HID queue. Under
# continuous motion, reading once per tick can't keep up with both packet
# streams, so the queue backs up and playback lags further behind the
# physical device the longer you move it. Draining the queue every tick
# (bounded here as a safety cap against a runaway/flooding device) keeps the
# published state current instead of trailing behind.
MAX_READS_PER_TICK = 32


class SpacemouseNode(Node):
    """Publishes SpaceMouse Compact input as Joy and/or TwistStamped messages."""

    def __init__(self):
        super().__init__(
            'spacemouse_node',
            automatically_declare_parameters_from_overrides=True
        )

        self._declare_parameters()

        self.device_name = self.get_parameter('device_name').get_parameter_value().string_value
        self.publish_rate = float(self.get_parameter('publish_rate').value)
        self.frame_id = self.get_parameter('frame_id').get_parameter_value().string_value
        self.publish_joy = bool(self.get_parameter('publish_joy').value)
        self.publish_twist = bool(self.get_parameter('publish_twist').value)
        self.deadzone = float(self.get_parameter('deadzone').value)
        self.linear_scale = float(self.get_parameter('linear_scale').value)
        self.angular_scale = float(self.get_parameter('angular_scale').value)

        self.axis_map = {}
        for axis in AXIS_NAMES:
            source_param = self.get_parameter(f'axis_map.{axis}.source')
            source = source_param.get_parameter_value().string_value
            invert = bool(self.get_parameter(f'axis_map.{axis}.invert').value)
            self.axis_map[axis] = (source, invert)

        self.joy_pub = None
        if self.publish_joy:
            self.joy_pub = self.create_publisher(Joy, 'joy', 10)

        self.twist_pub = None
        if self.publish_twist:
            self.twist_pub = self.create_publisher(TwistStamped, 'twist_stamped', 10)

        self.device = None
        self._connect()

        period = 1.0 / self.publish_rate if self.publish_rate > 0 else 0.01
        self.timer = self.create_timer(period, self._on_timer)
        self.reconnect_timer = self.create_timer(2.0, self._reconnect_if_needed)

        self.get_logger().info('SpaceMouse node initialized')
        self.get_logger().info(
            f'  publish_joy={self.publish_joy} publish_twist={self.publish_twist}'
        )
        self.get_logger().info(f'  axis_map={self.axis_map}')

    def _declare_parameters(self):
        """Declare parameters with default values."""
        defaults = {
            'device_name': '',
            'publish_rate': 100.0,
            'frame_id': 'spacemouse',
            'publish_joy': True,
            'publish_twist': True,
            'deadzone': 0.05,
            'linear_scale': 1.0,
            'angular_scale': 1.0,
        }
        for axis in AXIS_NAMES:
            defaults[f'axis_map.{axis}.source'] = axis
            defaults[f'axis_map.{axis}.invert'] = False

        for name, default in defaults.items():
            if not self.has_parameter(name):
                self.declare_parameter(name, default)

    def _connect(self):
        """Attempt to open the SpaceMouse HID device. Never raises."""
        try:
            if self.device_name:
                self.device = pyspacemouse.open(device=self.device_name)
            else:
                self.device = pyspacemouse.open()
            self.get_logger().info('SpaceMouse device connected')
        except Exception as e:
            self.get_logger().error(
                f'Failed to open SpaceMouse device: {e}', throttle_duration_sec=5.0
            )
            self.device = None

    def _reconnect_if_needed(self):
        if self.device is None:
            self.get_logger().warn(
                'SpaceMouse not connected, retrying...', throttle_duration_sec=5.0
            )
            self._connect()

    def _on_timer(self):
        if self.device is None:
            return

        try:
            state = self.device.read()
            last_t = state.t
            for _ in range(MAX_READS_PER_TICK - 1):
                state = self.device.read()
                if state.t == last_t:
                    break
                last_t = state.t
        except Exception as e:
            self.get_logger().error(
                f'Error reading SpaceMouse state: {e}', throttle_duration_sec=5.0
            )
            self.device = None
            return

        raw = {
            'x': state.x,
            'y': state.y,
            'z': state.z,
            'roll': state.roll,
            'pitch': state.pitch,
            'yaw': state.yaw,
        }

        out = {}
        for axis in AXIS_NAMES:
            source, invert = self.axis_map[axis]
            value = raw.get(source, 0.0)
            if invert:
                value = -value
            if abs(value) < self.deadzone:
                value = 0.0
            out[axis] = value

        buttons = [int(b) for b in state.buttons] if state.buttons else []
        stamp = self.get_clock().now().to_msg()

        if self.joy_pub is not None:
            joy_msg = Joy()
            joy_msg.header.stamp = stamp
            joy_msg.header.frame_id = self.frame_id
            joy_msg.axes = [float(out[a]) for a in AXIS_NAMES]
            joy_msg.buttons = buttons
            self.joy_pub.publish(joy_msg)

        if self.twist_pub is not None:
            twist_msg = TwistStamped()
            twist_msg.header.stamp = stamp
            twist_msg.header.frame_id = self.frame_id
            twist_msg.twist.linear.x = out['x'] * self.linear_scale
            twist_msg.twist.linear.y = out['y'] * self.linear_scale
            twist_msg.twist.linear.z = out['z'] * self.linear_scale
            twist_msg.twist.angular.x = out['roll'] * self.angular_scale
            twist_msg.twist.angular.y = out['pitch'] * self.angular_scale
            twist_msg.twist.angular.z = out['yaw'] * self.angular_scale
            self.twist_pub.publish(twist_msg)

    def destroy_node(self):
        if self.device is not None:
            try:
                self.device.close()
            except Exception:
                pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = SpacemouseNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
