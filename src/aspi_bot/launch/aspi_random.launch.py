"""Stratégie A — aléatoire (bump and turn).

Lance : Gazebo (turtlebot3_world) + map_server (carte de référence, vérité terrain pour la mesure)
+ TF statique identité map -> odom + random_walker + coverage_tracker + RViz.

Le robot n'utilise PAS la carte : elle sert uniquement au tracker pour calculer le % couvert.
Hypothèse : la carte a été construite depuis la position de spawn, donc map == odom au départ
(dérive d'odométrie négligée en simulation — limite notée dans le journal).

Exemple : ros2 launch aspi_bot aspi_random.launch.py seed:=2
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    aspi_dir = get_package_share_directory('aspi_bot')
    tb3_gazebo_dir = get_package_share_directory('turtlebot3_gazebo')

    seed = LaunchConfiguration('seed')
    map_yaml = LaunchConfiguration('map')
    run_duration = LaunchConfiguration('run_duration')
    use_rviz = LaunchConfiguration('use_rviz')
    sim = {'use_sim_time': True}

    args = [
        DeclareLaunchArgument('seed', default_value='1',
                              description='Graine du tirage aléatoire (reproductibilité)'),
        DeclareLaunchArgument('map', default_value=os.path.join(aspi_dir, 'maps', 'world.yaml'),
                              description='Carte de référence (vérité terrain)'),
        DeclareLaunchArgument('run_duration', default_value='600.0',
                              description='Durée du run en secondes simulées'),
        DeclareLaunchArgument('use_rviz', default_value='true'),
    ]

    # Monde + robot (le launch TurtleBot3 inclut robot_state_publisher en sim time)
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(tb3_gazebo_dir, 'launch', 'turtlebot3_world.launch.py')))

    # Carte de référence : map_server est un nœud lifecycle, activé par le lifecycle_manager
    map_server = Node(
        package='nav2_map_server', executable='map_server', name='map_server',
        output='screen', parameters=[sim, {'yaml_filename': map_yaml}])
    lifecycle_manager = Node(
        package='nav2_lifecycle_manager', executable='lifecycle_manager',
        name='lifecycle_manager_map', output='screen',
        parameters=[sim, {'autostart': True, 'node_names': ['map_server']}])

    # Pas de localisation en stratégie A : on pose map == odom
    map_to_odom = Node(
        package='tf2_ros', executable='static_transform_publisher', name='map_to_odom',
        arguments=['--frame-id', 'map', '--child-frame-id', 'odom'],
        parameters=[sim])

    walker = Node(
        package='aspi_bot', executable='random_walker', name='random_walker',
        output='screen', parameters=[sim, {'seed': ParameterValue(seed, value_type=int)}])
    tracker = Node(
        package='aspi_bot', executable='coverage_tracker', name='coverage_tracker',
        output='screen',
        parameters=[sim, {
            'strategy': 'RANDOM',
            # Typage explicite : sinon run_duration:=600 serait lu comme un entier et refusé
            'seed': ParameterValue(seed, value_type=int),
            'run_duration': ParameterValue(run_duration, value_type=float)}])

    rviz = Node(
        package='rviz2', executable='rviz2', name='rviz2', output='log',
        arguments=['-d', os.path.join(aspi_dir, 'rviz', 'aspi.rviz')],
        parameters=[sim], condition=IfCondition(use_rviz))

    return LaunchDescription(args + [
        gazebo, map_server, lifecycle_manager, map_to_odom, walker, tracker, rviz])
