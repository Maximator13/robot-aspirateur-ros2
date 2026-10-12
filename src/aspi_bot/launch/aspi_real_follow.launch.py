"""Stratégie B sur le VRAI TurtleBot3, SANS Nav2 (repli du 12/10).

Même trajet boustrophédon que aspi_real_planned (coverage_planner), mais exécuté par
coverage_follower (« tourner puis avancer », pose par TF) au lieu de Nav2 : sur le robot réel,
Nav2 faisait tourner le robot sur place sans jamais avancer (journal).
Localisation : carte + TF statique identité map -> odom (robot relancé sur la croix, comme
aspi_real_random localization:=static) : même conditions de mesure que le run A en static.

Exemple :
  ros2 launch aspi_bot aspi_real_follow.launch.py map:=$HOME/ros2_ws/src/aspi_bot/maps/zone_reelle.yaml
Test en simulation (Gazebo lancé à part avec sim.launch.py, carte world.yaml) :
  use_sim_time:=true odom_x:=2.0 odom_y:=0.5   (map -> odom = -spawn, voir aspi_random)
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():
    aspi_dir = get_package_share_directory('aspi_bot')
    cfg = {n: LaunchConfiguration(n) for n in (
        'map', 'seed', 'run_duration', 'use_sim_time', 'linear_speed', 'angular_speed',
        'near_collision_distance', 'use_rviz', 'output_dir', 'odom_x', 'odom_y')}
    sim = {'use_sim_time': PythonExpression(["'", cfg['use_sim_time'], "'.lower() == 'true'"])}
    duree = PythonExpression(['float(', cfg['run_duration'], ')'])

    args = [
        DeclareLaunchArgument('map', default_value=os.path.join(aspi_dir, 'maps', 'world.yaml')),
        DeclareLaunchArgument('seed', default_value='1', description='numéro du run (nom du CSV)'),
        DeclareLaunchArgument('run_duration', default_value='300.0'),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('linear_speed', default_value='0.10', description='m/s (sécurité)'),
        DeclareLaunchArgument('angular_speed', default_value='0.6', description='rad/s'),
        DeclareLaunchArgument('near_collision_distance', default_value='0.20'),
        DeclareLaunchArgument('use_rviz', default_value='true'),
        DeclareLaunchArgument('output_dir',
                              default_value=os.path.expanduser('~/ros2_ws/results/robot_reel')),
        # map -> odom : 0 sur le robot réel ; position de spawn en simulation
        DeclareLaunchArgument('odom_x', default_value='0.0'),
        DeclareLaunchArgument('odom_y', default_value='0.0'),
    ]
    nodes = [
        Node(package='nav2_map_server', executable='map_server', name='map_server', output='screen',
             parameters=[sim, {'yaml_filename': cfg['map']}]),
        Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
             name='lifecycle_manager_map', output='screen',
             parameters=[sim, {'autostart': True, 'node_names': ['map_server']}]),
        Node(package='tf2_ros', executable='static_transform_publisher', name='map_to_odom',
             arguments=['--x', cfg['odom_x'], '--y', cfg['odom_y'],
                        '--frame-id', 'map', '--child-frame-id', 'odom'],
             parameters=[sim]),
        Node(package='aspi_bot', executable='coverage_planner', name='coverage_planner',
             output='screen', parameters=[sim, {'start_x': 0.0, 'start_y': 0.0}]),
        # Le chrono du follower démarre au premier pas, celui du tracker au premier déplacement :
        # +5 s pour que le robot roule jusqu'à la fin de la mesure.
        Node(package='aspi_bot', executable='coverage_follower', name='coverage_follower',
             output='screen',
             parameters=[sim, {'linear_speed': PythonExpression(['float(', cfg['linear_speed'], ')']),
                               'angular_speed': PythonExpression(['float(', cfg['angular_speed'], ')']),
                               'run_duration': PythonExpression(['float(', cfg['run_duration'], ') + 5.0'])}]),
        Node(package='aspi_bot', executable='coverage_tracker', name='coverage_tracker',
             output='screen',
             parameters=[sim, {'strategy': 'BOUSTROPHEDON',
                               'seed': PythonExpression(['int(', cfg['seed'], ')']),
                               'run_duration': duree,
                               'near_collision_distance': PythonExpression(
                                   ['float(', cfg['near_collision_distance'], ')']),
                               'output_dir': cfg['output_dir']}]),
        Node(package='rviz2', executable='rviz2', name='rviz2', output='log',
             arguments=['-d', os.path.join(aspi_dir, 'rviz', 'aspi.rviz')], parameters=[sim],
             condition=IfCondition(cfg['use_rviz'])),
    ]
    return LaunchDescription(args + nodes)
