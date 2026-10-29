# myCobot 280 (M5) simulation for OpenHRC using ros2_control mock hardware (no physics engine).
# The robot model is taken unmodified from mycobot_description; the ros2_control tag and
# usable joint velocity limits are added here when building robot_description.
import os
import xml.dom.minidom

import xacro
from ament_index_python.packages import get_package_share_directory

from launch import LaunchContext, LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, RegisterEventHandler
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessStart
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

CONTROLLERS_FILE = os.path.join('config', 'mycobot', 'mycobot_controllers.yaml')
CONTROLLERS = ['joint_state_broadcaster', 'arm_controller']
BASE_LINK = 'g_base'
ARM_JOINTS = [
    'joint2_to_joint1',
    'joint3_to_joint2',
    'joint4_to_joint3',
    'joint5_to_joint4',
    'joint6_to_joint5',
    'joint6output_to_joint6',
]


def get_robot_description(model, joint_velocity_limit, initial_positions):
    doc = xacro.process_file(model)
    if not isinstance(doc, xml.dom.minidom.Document):
        raise RuntimeError(f'The given model {model} is not a valid xml format.')
    robot = doc.documentElement

    # mycobot_description sets velocity="0" for every joint, which OpenHRC's IK treats as "cannot move".
    found = set()
    for joint in robot.getElementsByTagName('joint'):
        name = joint.getAttribute('name')
        if name not in ARM_JOINTS:
            continue
        found.add(name)
        for limit in joint.getElementsByTagName('limit'):
            if float(limit.getAttribute('velocity') or 0.0) <= 0.0:
                limit.setAttribute('velocity', str(joint_velocity_limit))
    if found != set(ARM_JOINTS):
        raise RuntimeError(f'Joints {sorted(set(ARM_JOINTS) - found)} not found in {model}.')

    ros2_control = doc.createElement('ros2_control')
    ros2_control.setAttribute('name', 'MycobotMockSystem')
    ros2_control.setAttribute('type', 'system')
    hardware = doc.createElement('hardware')
    plugin = doc.createElement('plugin')
    plugin.appendChild(doc.createTextNode('mock_components/GenericSystem'))
    hardware.appendChild(plugin)
    ros2_control.appendChild(hardware)

    for name, q0 in zip(ARM_JOINTS, initial_positions):
        joint = doc.createElement('joint')
        joint.setAttribute('name', name)
        cmd = doc.createElement('command_interface')
        cmd.setAttribute('name', 'position')
        joint.appendChild(cmd)
        pos = doc.createElement('state_interface')
        pos.setAttribute('name', 'position')
        param = doc.createElement('param')
        param.setAttribute('name', 'initial_value')
        param.appendChild(doc.createTextNode(str(q0)))
        pos.appendChild(param)
        joint.appendChild(pos)
        vel = doc.createElement('state_interface')
        vel.setAttribute('name', 'velocity')
        joint.appendChild(vel)
        ros2_control.appendChild(joint)
    robot.appendChild(ros2_control)

    return doc.toxml()


def launch_setup(context: LaunchContext):
    model = LaunchConfiguration('model').perform(context)
    joint_velocity_limit = float(LaunchConfiguration('joint_velocity_limit').perform(context))
    initial_positions = [float(q) for q in LaunchConfiguration('initial_positions').perform(context).split()]
    if len(initial_positions) != len(ARM_JOINTS):
        raise RuntimeError(f'initial_positions needs {len(ARM_JOINTS)} values, got {len(initial_positions)}.')

    robot_description = {'robot_description': get_robot_description(model, joint_velocity_limit, initial_positions)}
    controllers_file = os.path.join(get_package_share_directory('ohrc_hw_config'), CONTROLLERS_FILE)
    if not os.path.isfile(controllers_file):
        raise RuntimeError(f'Controllers file {controllers_file} not found; rebuild ohrc_hw_config.')

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='both',
        parameters=[robot_description],
    )

    control_node = Node(
        package='controller_manager',
        executable='ros2_control_node',
        parameters=[robot_description, controllers_file],
        output='both',
    )

    spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=CONTROLLERS + ['--controller-manager-timeout', '30'],
        output='screen',
    )

    return [
        robot_state_publisher,
        control_node,
        RegisterEventHandler(OnProcessStart(target_action=control_node, on_start=[spawner])),
    ]


def generate_launch_description():
    declared_arguments = [
        DeclareLaunchArgument('model', default_value=os.path.join(
            get_package_share_directory('mycobot_description'), 'urdf', 'mycobot_280_m5', 'mycobot_280_m5.urdf'),
            description='myCobot 280 URDF/xacro (its joint names must match ARM_JOINTS)'),
        DeclareLaunchArgument('joint_velocity_limit', default_value='2.0',
                              description='Joint velocity limit [rad/s] applied to joints whose URDF limit is 0'),
        DeclareLaunchArgument('initial_positions', default_value='0.0 -0.6 -1.0 0.03 0.0 0.0',
                              description='Initial joint positions [rad] of the mock hardware (space separated)'),
        DeclareLaunchArgument('rviz', default_value='false',
                              description='true/false for visualizing the robot in rviz'),
    ]

    world_to_base = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='world_to_mycobot_base',
        arguments=['--frame-id', 'world', '--child-frame-id', BASE_LINK],
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['--display-config',
                   os.path.join(get_package_share_directory('mycobot_280'), 'config', 'mycobot.rviz'),
                   '-f', 'world'],
        condition=IfCondition(LaunchConfiguration('rviz')),
    )

    return LaunchDescription(declared_arguments + [
        OpaqueFunction(function=launch_setup),
        world_to_base,
        rviz,
    ])
