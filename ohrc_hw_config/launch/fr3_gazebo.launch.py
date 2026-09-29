# Based on franka_gazebo_bringup/launch/gazebo_franka_arm_example_controller.launch.py
import os
import xacro
import xml.dom.minidom

from ament_index_python.packages import get_package_share_directory

from launch import LaunchContext, LaunchDescription
from launch.actions import (DeclareLaunchArgument, OpaqueFunction, ExecuteProcess, RegisterEventHandler,
                            IncludeLaunchDescription, AppendEnvironmentVariable)
from launch.event_handlers import OnProcessExit, OnShutdown
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.conditions import IfCondition
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

ROBOT_TYPE = 'fr3'
CONTROLLERS = ['joint_state_broadcaster', 'joint_velocity_controller']


def get_robot_description(load_gripper, franka_hand):
    franka_xacro_file = os.path.join(
        get_package_share_directory('franka_gazebo_bringup'), 'urdf', 'franka_arm.gazebo.xacro')
    controllers_file = os.path.join(
        get_package_share_directory('ohrc_hw_config'), 'config', 'fr3', 'fr3_gazebo_controllers.yaml')

    doc = xacro.process_file(
        franka_xacro_file,
        mappings={
            'robot_type': ROBOT_TYPE,
            'hand': load_gripper,
            'gazebo': 'true',
            'ee_id': franka_hand,
            'gazebo_effort': 'false',
        })
    if not isinstance(doc, xml.dom.minidom.Document):
        raise RuntimeError(f'The given xacro file {franka_xacro_file} is not a valid xml format.')

    replaced = 0
    for plugin in doc.getElementsByTagName('plugin'):
        if 'gz_ros2_control' not in plugin.getAttribute('filename'):
            continue
        for parameters in plugin.getElementsByTagName('parameters'):
            for child in list(parameters.childNodes):
                parameters.removeChild(child)
            parameters.appendChild(doc.createTextNode(controllers_file))
            replaced += 1
    if replaced == 0:
        raise RuntimeError(
            f'No gz_ros2_control <parameters> element found in {franka_xacro_file}; '
            'the franka_ros2 version is not supported by ohrc_hw_config.')

    return doc.toxml()


def launch_setup(context: LaunchContext):
    load_gripper = LaunchConfiguration('load_gripper').perform(context)
    franka_hand = LaunchConfiguration('franka_hand').perform(context)

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='both',
        parameters=[{'robot_description': get_robot_description(load_gripper, franka_hand)}],
    )
    return [robot_state_publisher]


def generate_launch_description():
    franka_description_parent = os.path.dirname(get_package_share_directory('franka_description'))
    franka_gazebo_bringup_share = get_package_share_directory('franka_gazebo_bringup')

    declared_arguments = [
        DeclareLaunchArgument('load_gripper', default_value='false',
                              description='true/false for mounting the Franka Hand'),
        DeclareLaunchArgument('franka_hand', default_value='franka_hand',
                              description='End-effector id used when load_gripper is true'),
        DeclareLaunchArgument('rviz', default_value='false',
                              description='true/false for visualizing the robot in rviz'),
        DeclareLaunchArgument('gz_args', default_value='empty.sdf -r',
                              description='Extra args to be forwarded to gazebo'),
    ]

    # Gazebo Fortress (Humble) reads IGN_*, Gazebo Harmonic (Jazzy) reads GZ_*.
    resource_paths = [
        AppendEnvironmentVariable(var, path)
        for var in ('GZ_SIM_RESOURCE_PATH', 'IGN_GAZEBO_RESOURCE_PATH')
        for path in (franka_description_parent, franka_gazebo_bringup_share)
    ]

    gazebo = IncludeLaunchDescription(
        PathJoinSubstitution([FindPackageShare('ros_gz_sim'), 'launch', 'gz_sim.launch.py']),
        launch_arguments={'gz_args': LaunchConfiguration('gz_args')}.items(),
    )

    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-topic', '/robot_description'],
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
                   os.path.join(get_package_share_directory('franka_description'),
                                'rviz', 'visualize_franka.rviz'),
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
