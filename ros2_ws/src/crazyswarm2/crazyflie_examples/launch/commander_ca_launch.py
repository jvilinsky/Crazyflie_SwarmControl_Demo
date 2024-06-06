import os
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node
from launch.conditions import LaunchConfigurationEquals
from launch.conditions import LaunchConfigurationNotEquals
from launch.substitutions import LaunchConfiguration, PythonExpression


def generate_launch_description():
    # load crazyflies
    crazyflies_yaml = os.path.join(
        get_package_share_directory('crazyflie'),
        'config',
        'crazyflies.yaml')

    with open(crazyflies_yaml, 'r') as ymlfile:
        crazyflies = yaml.safe_load(ymlfile)

    # server params
    server_yaml = os.path.join(
        get_package_share_directory('crazyflie'),
        'config',
        'server.yaml')

    with open(server_yaml, 'r') as ymlfile:
        server_yaml_contents = yaml.safe_load(ymlfile)

    server_params = [crazyflies] + [server_yaml_contents["/crazyflie_server"]["ros__parameters"]]

    # construct motion_capture_configuration
    motion_capture_yaml = os.path.join(
        get_package_share_directory('crazyflie'),
        'config',
        'motion_capture.yaml')

    with open(motion_capture_yaml, 'r') as ymlfile:
        motion_capture = yaml.safe_load(ymlfile)

    motion_capture_params = motion_capture["/motion_capture_tracking"]["ros__parameters"]
    motion_capture_params["rigid_bodies"] = dict()
    for key, value in crazyflies["robots"].items():
        type = crazyflies["robot_types"][value["type"]]
        if value["enabled"] and type["motion_capture"]["enabled"]:
            enabled_cf = key # works for only one cf
            motion_capture_params["rigid_bodies"][key] =  {
                    "initial_position": value["initial_position"],
                    "marker": type["motion_capture"]["marker"],
                    "dynamics": type["motion_capture"]["dynamics"],
                }
            
    # copy relevent settings to server params
    server_params[1]["poses_qos_deadline"] = motion_capture_params["topics"]["poses"]["qos"]["deadline"]

    return LaunchDescription([
        DeclareLaunchArgument('backend', default_value='cflib'),
        DeclareLaunchArgument('debug', default_value='False'),
        Node(
            package='motion_capture_tracking',
            executable='motion_capture_tracking_node',
            condition=LaunchConfigurationNotEquals('backend','sim'),
            name='motion_capture_tracking',
            output='screen',
            parameters=[motion_capture_params]
        ),
        Node(
            package='crazyflie_examples',
            executable='goal_commander.py',
            name='goal_commander',
            output='screen',
            parameters=[{"hover_height": 0.5},
                        {"ca_on": True},
                        {"incoming_twist_topic": "/cmd_vel"},
                        {"robot_prefix": enabled_cf}]
        ),
        Node(
            package='crazyflie_examples',
            executable='detect_avoid.py',
            name='detect_avoid',
            output='screen',
            parameters=[{"ca_threshold1": 0.2},
                        {"ca_threshold2": 0.4},
                        {"avoidance_vel": 0.2},
                        {"robot_prefix": enabled_cf}]
        ),
        Node(
            package='crazyflie_examples',
            executable='waypoint_gen.py',
            name='waypoint_gen',
            output='screen',
            parameters=[{"robot_prefix": enabled_cf}]
        ),
        Node(
            package='crazyflie',
            executable='crazyflie_server.py',
            condition=LaunchConfigurationEquals('backend','cflib'),
            name='crazyflie_server',
            output='screen',
            parameters=server_params
        ),
        Node(
            package='crazyflie',
            executable='crazyflie_server',
            condition=LaunchConfigurationEquals('backend','cpp'),
            name='crazyflie_server',
            output='screen',
            parameters=server_params,
            prefix=PythonExpression(['"xterm -e gdb -ex run --args" if ', LaunchConfiguration('debug'), ' else ""']),
        ),
        Node(
            package='crazyflie_sim',
            executable='crazyflie_server',
            condition=LaunchConfigurationEquals('backend','sim'),
            name='crazyflie_server',
            output='screen',
            emulate_tty=True,
            parameters=server_params
        ),
        # Node(
        #     package='rviz2',
        #     namespace='',
        #     executable='rviz2',
        #     name='rviz2',
        #     arguments=['-d' + os.path.join(get_package_share_directory('crazyflie'), 'config', 'config.rviz')],
        #     parameters=[{
        #         "use_sim_time": True,
        #     }]
        # ),
    ])

if __name__ == '__main__':
    generate_launch_description()