from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'config_file',
            default_value=PathJoinSubstitution([
                FindPackageShare('spacemouse_ros2'),
                'config',
                'spacemouse.yaml',
            ]),
            description='ROS 2 parameter file defining axis remap/invert and topic config'
        ),

        # Namespaced under 'spacemouse' so relative topics resolve to
        # /spacemouse/joy and /spacemouse/twist_stamped, matching the
        # remap target already used by lekiwi_ros2/lerre_ros2's direct-servo
        # launch files in wheel_control_mode:=joy.
        Node(
            package='spacemouse_ros2',
            executable='spacemouse_node',
            name='spacemouse_node',
            namespace='spacemouse',
            parameters=[LaunchConfiguration('config_file')],
            output='screen'
        ),
    ])
