# Based on crane_x7_gazebo/launch/crane_x7_with_table.launch.py (Copyright 2022 RT Corporation, Apache-2.0)
import os
import xml.dom.minidom

import xacro
from ament_index_python.packages import get_package_share_directory

from launch import LaunchContext, LaunchDescription
from launch.actions import (DeclareLaunchArgument, OpaqueFunction, ExecuteProcess, RegisterEventHandler,
                            IncludeLaunchDescription, AppendEnvironmentVariable)
from launch.event_handlers import OnProcessExit, OnShutdown
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.conditions import IfCondition
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

CONTROLLERS_FILE = os.path.join('config', 'crane_x7', 'crane_x7_gazebo_controllers.yaml')
CONTROLLERS = ['joint_state_broadcaster', 'joint_velocity_controller', 'crane_x7_gripper_controller']
ARM_JOINTS = [
    'crane_x7_shoulder_fixed_part_pan_joint',
    'crane_x7_shoulder_revolute_part_tilt_joint',
    'crane_x7_upper_arm_revolute_part_twist_joint',
    'crane_x7_upper_arm_revolute_part_rotate_joint',
    'crane_x7_lower_arm_fixed_part_joint',
    'crane_x7_lower_arm_revolute_part_joint',
    'crane_x7_wrist_joint',
]


def get_robot_description():
    xacro_file = os.path.join(
        get_package_share_directory('crane_x7_description'), 'urdf', 'crane_x7.urdf.xacro')
    controllers_file = os.path.join(get_package_share_directory('ohrc_hw_config'), CONTROLLERS_FILE)
    if not os.path.isfile(controllers_file):
        raise RuntimeError(f'Controllers file {controllers_file} not found; rebuild ohrc_hw_config.')

    doc = xacro.process_file(
        xacro_file,
        mappings={
            'use_gazebo': 'true',
            'gz_control_config_package': 'ohrc_hw_config',
            'gz_control_config_file_path': CONTROLLERS_FILE,
        })
    if not isinstance(doc, xml.dom.minidom.Document):
        raise RuntimeError(f'The given xacro file {xacro_file} is not a valid xml format.')

    # position -> velocity command interface for the arm joints (the gripper stays in position).
    switched = set()
    for ros2_control in doc.getElementsByTagName('ros2_control'):
        for joint in ros2_control.getElementsByTagName('joint'):
            name = joint.getAttribute('name')
            if name not in ARM_JOINTS:
                continue
            for cmd in joint.getElementsByTagName('command_interface'):
                if cmd.getAttribute('name') != 'position':
                    continue
                cmd.setAttribute('name', 'velocity')
                for child in list(cmd.childNodes):
                    cmd.removeChild(child)
                switched.add(name)
    if switched != set(ARM_JOINTS):
        raise RuntimeError(
            f'Could not switch {sorted(set(ARM_JOINTS) - switched)} to velocity control in {xacro_file}; '
            'the crane_x7_description version is not supported by ohrc_hw_config.')

    return doc.toxml()


def launch_setup(context: LaunchContext):
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='both',
        parameters=[{'robot_description': get_robot_description()}],
    )
    return [robot_state_publisher]


def generate_launch_description():
    crane_x7_description_parent = os.path.dirname(get_package_share_directory('crane_x7_description'))
    crane_x7_gazebo_share = get_package_share_directory('crane_x7_gazebo')
    world_file = os.path.join(crane_x7_gazebo_share, 'worlds', 'table.sdf')
    gui_config = os.path.join(crane_x7_gazebo_share, 'gui', 'gui.config')

    declared_arguments = [
        DeclareLaunchArgument('rviz', default_value='false',
                              description='true/false for visualizing the robot in rviz'),
        DeclareLaunchArgument('gz_args', default_value=f'-r {world_file} --gui-config {gui_config}',
                              description='Extra args to be forwarded to gazebo'),
        DeclareLaunchArgument('z', default_value='1.015',
                              description='Spawn height of the robot (1.015 = on top of the table)'),
    ]

    # Gazebo Fortress (Humble) reads IGN_*, Gazebo Harmonic (Jazzy) reads GZ_*.
    resource_paths = [
        AppendEnvironmentVariable(var, crane_x7_description_parent)
        for var in ('GZ_SIM_RESOURCE_PATH', 'IGN_GAZEBO_RESOURCE_PATH')
    ]

    gazebo = IncludeLaunchDescription(
        PathJoinSubstitution([FindPackageShare('ros_gz_sim'), 'launch', 'gz_sim.launch.py']),
        launch_arguments={'gz_args': LaunchConfiguration('gz_args')}.items(),
    )

    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-topic', '/robot_description', '-name', 'crane_x7',
                   '-z', LaunchConfiguration('z'), '-allow_renaming', 'true'],
        output='screen',
    )

    spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=CONTROLLERS + ['--controller-manager-timeout', '30'],
        output='screen',
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['--display-config',
                   os.path.join(get_package_share_directory('crane_x7_description'),
                                'launch', 'display.rviz'),
                   '-f', 'world'],
        condition=IfCondition(LaunchConfiguration('rviz')),
    )

    return LaunchDescription(declared_arguments + resource_paths + [
        OpaqueFunction(function=launch_setup),
        gazebo,
        rviz,
        spawn,
        RegisterEventHandler(OnProcessExit(target_action=spawn, on_exit=[spawner])),
        RegisterEventHandler(OnShutdown(on_shutdown=[
            ExecuteProcess(cmd=['pkill', '-SIGINT', '-f', 'gz sim|ign gazebo'],
                           name='gz_sim_graceful_shutdown'),
        ])),
    ])
