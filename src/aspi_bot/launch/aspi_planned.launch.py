"""Stratégie B — balayage boustrophédon planifié sur la carte, exécuté par Nav2.

Lance : simulation commune (sim.launch.py) + Nav2 (map_server + AMCL + navigation, config de
aspi_bot/config/nav2_params.yaml) + coverage_planner + coverage_executor + coverage_tracker + RViz.

Différence avec la stratégie A : ici le robot UTILISE la carte (localisation AMCL, map -> odom
estimé) ; la même carte sert de vérité terrain au tracker (même masque atteignable que le planner).

Exemples :
  ros2 launch aspi_bot aspi_planned.launch.py                                # avec fenêtres
  ros2 launch aspi_bot aspi_planned.launch.py headless:=true                 # sans fenêtres
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    aspi_dir = get_package_share_directory('aspi_bot')
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    seed = LaunchConfiguration('seed')
    map_yaml = LaunchConfiguration('map')
    nav2_params = LaunchConfiguration('nav2_params')
    run_duration = LaunchConfiguration('run_duration')
    headless = LaunchConfiguration('headless')
    fast = LaunchConfiguration('fast')
    spawn_x = LaunchConfiguration('spawn_x')
    spawn_y = LaunchConfiguration('spawn_y')
    sim = {'use_sim_time': True}

    args = [
        # Le balayage est déterministe : seed sert seulement à nommer le CSV (et fixe Gazebo)
        DeclareLaunchArgument('seed', default_value='1',
                              description='Numéro du run (nom du CSV)'),
        DeclareLaunchArgument('map', default_value=os.path.join(aspi_dir, 'maps', 'world.yaml'),
                              description='Carte utilisée par Nav2 ET vérité terrain du tracker'),
        # Nommé nav2_params (et non params_file) : les arguments de launch ne sont pas cloisonnés
        # en Humble, et gzserver.launch.py déclare aussi un « params_file » qu'il recevrait.
        DeclareLaunchArgument('nav2_params',
                              default_value=os.path.join(aspi_dir, 'config', 'nav2_params.yaml'),
                              description='Paramètres Nav2 (copie adaptée du burger.yaml Humble)'),
        DeclareLaunchArgument('run_duration', default_value='600.0',
                              description='Durée du run en secondes simulées'),
        DeclareLaunchArgument('headless', default_value='false',
                              description='true : ni gzclient ni RViz'),
        DeclareLaunchArgument('fast', default_value='false',
                              description='true : simulation accélérée (à valider pour Nav2)'),
        DeclareLaunchArgument('spawn_x', default_value='-2.0'),
        DeclareLaunchArgument('spawn_y', default_value='-0.5'),
    ]

    # Monde + robot, communs aux deux stratégies
    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(aspi_dir, 'launch', 'sim.launch.py')),
        launch_arguments={'headless': headless, 'fast': fast,
                          'spawn_x': spawn_x, 'spawn_y': spawn_y}.items())

    # Nav2 complet : map_server + AMCL (localisation) + planner/controller/bt_navigator/
    # waypoint_follower. La pose initiale est fixée par coverage_executor (par code).
    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')),
        launch_arguments={'map': map_yaml, 'params_file': nav2_params,
                          'use_sim_time': 'true', 'autostart': 'true'}.items())

    # --- Nœuds du projet ---
    # Départ = origine de la carte (carte construite depuis le spawn)
    planner = Node(
        package='aspi_bot', executable='coverage_planner', name='coverage_planner',
        output='screen', parameters=[sim, {'start_x': 0.0, 'start_y': 0.0}])
    executor = Node(
        package='aspi_bot', executable='coverage_executor', name='coverage_executor',
        output='screen',
        parameters=[sim, {'initial_x': 0.0, 'initial_y': 0.0, 'initial_yaw': 0.0}])
    tracker = Node(
        package='aspi_bot', executable='coverage_tracker', name='coverage_tracker',
        output='screen',
        parameters=[sim, {
            'strategy': 'BOUSTROPHEDON',
            'seed': ParameterValue(seed, value_type=int),
            'run_duration': ParameterValue(run_duration, value_type=float)}])

    rviz = Node(
        package='rviz2', executable='rviz2', name='rviz2', output='log',
        arguments=['-d', os.path.join(aspi_dir, 'rviz', 'aspi.rviz')],
        parameters=[sim], condition=UnlessCondition(headless))

    return LaunchDescription(args + [simulation, nav2, planner, executor, tracker, rviz])
