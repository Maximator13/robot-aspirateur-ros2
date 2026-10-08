"""Stratégie B sur le VRAI TurtleBot3 (pas de Gazebo).

Le robot exécute `turtlebot3_bringup robot.launch.py` (via SSH). Ce launch tourne sur le PC :
Nav2 (config/nav2_params_real.yaml : vitesse réduite, use_sim_time false, AMCL avec pose initiale
(0, 0, 0)) + coverage_planner + coverage_executor + coverage_tracker + RViz.

Zone interdite (option) : keepout:=true lance le serveur du masque (maps/keepout.yaml, généré par
scripts/make_keepout_mask.py) et costmap_filter_info_server ; allowed_area limite AUSSI le balayage
et la mesure au même rectangle (sinon des waypoints tomberaient dans la zone interdite).

Sécurité : 0.10 m/s. Arrêt : Ctrl+C (l'executor annule le but) puis scripts/stop_robot.sh.

Exemple :
  ros2 launch aspi_bot aspi_real_planned.launch.py map:=$HOME/ros2_ws/src/aspi_bot/maps/zone_reelle.yaml
Test en simulation (Gazebo lancé à part avec sim.launch.py) : ajouter use_sim_time:=true.
"""
import os

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from nav2_common.launch import RewrittenYaml


def as_bool(text):
    return text.strip().lower() in ('true', '1', 'yes')


def as_list(text):
    """'[-1.0, -1.0, 1.0, 1.0]' -> [-1.0, -1.0, 1.0, 1.0] ; '[]' -> []."""
    value = yaml.safe_load(text)
    return [float(v) for v in value] if value else []


def project_nodes(context):
    """Nœuds du projet : paramètres lus au lancement (zone autorisée optionnelle)."""
    cfg = {name: LaunchConfiguration(name).perform(context) for name in (
        'seed', 'run_duration', 'use_sim_time', 'allowed_area', 'near_collision_distance',
        'use_rviz', 'output_dir')}
    sim = {'use_sim_time': as_bool(cfg['use_sim_time'])}
    area = as_list(cfg['allowed_area'])
    area_param = {'allowed_area': area} if area else {}
    run_duration = float(cfg['run_duration'])

    aspi_dir = get_package_share_directory('aspi_bot')
    nodes = [
        # Départ = origine de la carte (carte construite depuis le point de départ marqué au sol)
        Node(package='aspi_bot', executable='coverage_planner', name='coverage_planner',
             output='screen', parameters=[sim, {'start_x': 0.0, 'start_y': 0.0}, area_param]),
        Node(package='aspi_bot', executable='coverage_executor', name='coverage_executor',
             output='screen',
             parameters=[sim, {'initial_x': 0.0, 'initial_y': 0.0, 'initial_yaw': 0.0,
                               'max_duration': run_duration + 10.0}]),
        Node(package='aspi_bot', executable='coverage_tracker', name='coverage_tracker',
             output='screen',
             parameters=[sim, {'strategy': 'BOUSTROPHEDON', 'seed': int(cfg['seed']),
                               'run_duration': run_duration,
                               'near_collision_distance': float(cfg['near_collision_distance']),
                      'output_dir': cfg['output_dir']},
                         area_param]),
    ]
    if as_bool(cfg['use_rviz']):
        nodes.append(Node(package='rviz2', executable='rviz2', name='rviz2', output='log',
                          arguments=['-d', os.path.join(aspi_dir, 'rviz', 'aspi.rviz')],
                          parameters=[sim]))
    return nodes


def generate_launch_description():
    aspi_dir = get_package_share_directory('aspi_bot')
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    map_yaml = LaunchConfiguration('map')
    nav2_params = LaunchConfiguration('nav2_params')
    use_sim_time = LaunchConfiguration('use_sim_time')
    keepout_mask = LaunchConfiguration('keepout_mask')

    args = [
        DeclareLaunchArgument('map', default_value=os.path.join(aspi_dir, 'maps', 'world.yaml'),
                              description='Carte de la zone (Nav2 et vérité terrain de la mesure)'),
        DeclareLaunchArgument('nav2_params',
                              default_value=os.path.join(aspi_dir, 'config', 'nav2_params_real.yaml')),
        DeclareLaunchArgument('seed', default_value='1', description='Numéro du run (nom du CSV)'),
        DeclareLaunchArgument('run_duration', default_value='300.0'),
        DeclareLaunchArgument('use_sim_time', default_value='false',
                              description='false sur le robot ; true pour un test avec Gazebo'),
        DeclareLaunchArgument('keepout', default_value='false',
                              description='true : zone interdite (keepout filter de Nav2)'),
        DeclareLaunchArgument('keepout_mask',
                              default_value=os.path.join(aspi_dir, 'maps', 'keepout.yaml')),
        DeclareLaunchArgument('allowed_area', default_value='[]',
                              description='Zone balayée et mesurée [xmin, ymin, xmax, ymax] (repère map)'),
        DeclareLaunchArgument('near_collision_distance', default_value='0.20',
                              description='0.20 : le LDS-02 ne voit rien sous ~0.16 m'),
        DeclareLaunchArgument('use_rviz', default_value='true'),
        # CSV du robot réel à part : ne jamais les mélanger avec le protocole de simulation
        DeclareLaunchArgument('output_dir', default_value=os.path.expanduser('~/ros2_ws/results/robot_reel')),
    ]

    # Le filtre keepout est déclaré dans nav2_params_real.yaml mais désactivé (enabled: False) :
    # on l'active dans les deux costmaps seulement si keepout:=true.
    keepout = LaunchConfiguration('keepout')
    nav2_params_final = RewrittenYaml(
        source_file=nav2_params, root_key='', convert_types=True,
        param_rewrites={
            'local_costmap.local_costmap.ros__parameters.keepout_filter.enabled': keepout,
            'global_costmap.global_costmap.ros__parameters.keepout_filter.enabled': keepout})

    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')),
        launch_arguments={'map': map_yaml, 'params_file': nav2_params_final,
                          'use_sim_time': use_sim_time, 'autostart': 'true'}.items())

    # Zone interdite : masque + informations du filtre, activés par leur propre lifecycle manager
    with_keepout = IfCondition(LaunchConfiguration('keepout'))
    sim = {'use_sim_time': ParameterValue(use_sim_time, value_type=bool)}
    mask_server = Node(
        package='nav2_map_server', executable='map_server', name='filter_mask_server',
        output='screen', condition=with_keepout,
        parameters=[sim, {'yaml_filename': keepout_mask, 'topic_name': '/keepout_filter_mask'}])
    filter_info = Node(
        package='nav2_map_server', executable='costmap_filter_info_server',
        name='costmap_filter_info_server', output='screen', condition=with_keepout,
        parameters=[sim, os.path.join(aspi_dir, 'config', 'keepout_info.yaml')])
    keepout_lifecycle = Node(
        package='nav2_lifecycle_manager', executable='lifecycle_manager',
        name='lifecycle_manager_keepout', output='screen', condition=with_keepout,
        parameters=[sim, {'autostart': True,
                          'node_names': ['filter_mask_server', 'costmap_filter_info_server']}])

    return LaunchDescription(args + [nav2, mask_server, filter_info, keepout_lifecycle,
                                     OpaqueFunction(function=project_nodes)])
