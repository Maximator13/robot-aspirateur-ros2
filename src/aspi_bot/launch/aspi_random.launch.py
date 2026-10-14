import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    aspi_dir = get_package_share_directory('aspi_bot')

    seed = LaunchConfiguration('seed')
    map_yaml = LaunchConfiguration('map')
    run_duration = LaunchConfiguration('run_duration')
    headless = LaunchConfiguration('headless')
    fast = LaunchConfiguration('fast')
    spawn_x = LaunchConfiguration('spawn_x')
    spawn_y = LaunchConfiguration('spawn_y')
    sim = {'use_sim_time': True}

    args = [
        DeclareLaunchArgument('seed', default_value='1',
                              description='Graine du tirage aléatoire (reproductibilité)'),
        DeclareLaunchArgument('map', default_value=os.path.join(aspi_dir, 'maps', 'world.yaml'),
                              description='Carte de référence (vérité terrain)'),
        DeclareLaunchArgument('run_duration', default_value='600.0',
                              description='Durée du run en secondes simulées'),
        DeclareLaunchArgument('headless', default_value='false',
                              description='true : ni gzclient ni RViz (runs du protocole)'),
        DeclareLaunchArgument('fast', default_value='false',
                              description='true : monde sans limite de temps réel (accéléré)'),
        DeclareLaunchArgument('spawn_x', default_value='-2.0'),
        DeclareLaunchArgument('spawn_y', default_value='-0.5'),
    ]

    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(aspi_dir, 'launch', 'sim.launch.py')),
        launch_arguments={'headless': headless, 'fast': fast,
                          'spawn_x': spawn_x, 'spawn_y': spawn_y}.items())

    map_server = Node(
        package='nav2_map_server', executable='map_server', name='map_server',
        output='screen', parameters=[sim, {'yaml_filename': map_yaml}])
    lifecycle_manager = Node(
        package='nav2_lifecycle_manager', executable='lifecycle_manager',
        name='lifecycle_manager_map', output='screen',
        parameters=[sim, {'autostart': True, 'node_names': ['map_server']}])

    map_to_odom = Node(
        package='tf2_ros', executable='static_transform_publisher', name='map_to_odom',
        arguments=['--x', PythonExpression(['-(', spawn_x, ')']),
                   '--y', PythonExpression(['-(', spawn_y, ')']),
                   '--frame-id', 'map', '--child-frame-id', 'odom'],
        parameters=[sim])

    walker = Node(
        package='aspi_bot', executable='random_walker', name='random_walker',
        output='screen', parameters=[sim, {'seed': ParameterValue(seed, value_type=int)}])
    tracker = Node(
        package='aspi_bot', executable='coverage_tracker', name='coverage_tracker',
        output='screen',
        parameters=[sim, {
            'strategy': 'RANDOM',
            'seed': ParameterValue(seed, value_type=int),
            'run_duration': ParameterValue(run_duration, value_type=float)}])

    rviz = Node(
        package='rviz2', executable='rviz2', name='rviz2', output='log',
        arguments=['-d', os.path.join(aspi_dir, 'rviz', 'aspi.rviz')],
        parameters=[sim], condition=UnlessCondition(headless))

    return LaunchDescription(args + [
        simulation, map_server, lifecycle_manager, map_to_odom, walker, tracker, rviz])
