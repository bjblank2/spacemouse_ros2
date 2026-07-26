from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'namespace_prefix',
            default_value='',
            description=(
                'Optional prefix prepended to the node namespace '
                '(e.g. "robot1" -> /robot1/spacemouse/joy). Leave empty '
                'for the default /spacemouse/... topics.'
            )
        ),
        DeclareLaunchArgument(
            'config_file',
            default_value=PathJoinSubstitution([
                FindPackageShare('spacemouse_ros2'),
                'config',
                'spacemouse.yaml',
            ]),
            description='ROS 2 parameter file defining axis remap/invert and topic config'
        ),

        # Namespaced under '[namespace_prefix/]spacemouse' so relative topics
        # resolve to /spacemouse/joy and /spacemouse/twist_stamped by default
        # (matching the remap target already used by lekiwi_ros2/lerre_ros2's
        # direct-servo launch files in wheel_control_mode:=joy), or
        # /<namespace_prefix>/spacemouse/... when a prefix is supplied.
        Node(
            package='spacemouse_ros2',
            executable='spacemouse_node',
            name='spacemouse_node',
            namespace=PathJoinSubstitution([
                LaunchConfiguration('namespace_prefix'),
                'spacemouse',
            ]),
            parameters=[LaunchConfiguration('config_file')],
            output='screen'
        ),
    ])
