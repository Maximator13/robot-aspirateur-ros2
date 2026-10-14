import os

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def as_bool(text):
    return text.strip().lower() in ('true', '1', 'yes')


def as_list(text):
    value = yaml.safe_load(text)
    return [float(v) for v in value] if value else []


def project_nodes(context):
    cfg = {name: LaunchConfiguration(name).perform(context) for name in (
        'seed', 'run_duration', 'use_sim_time', 'forward_speed', 'turn_speed', 'fence',
        'allowed_area', 'near_collision_distance', 'use_rviz', 'output_dir')}
    sim = {'use_sim_time': as_bool(cfg['use_sim_time'])}

    walker_params = {'seed': int(cfg['seed']),
                     'forward_speed': float(cfg['forward_speed']),
                     'turn_speed': float(cfg['turn_speed']),
                     'run_duration': float(cfg['run_duration']) + 5.0}
    fence = as_list(cfg['fence'])
    if fence:
        walker_params['fence'] = fence

    tracker_params = {'strategy': 'RANDOM', 'seed': int(cfg['seed']),
                      'run_duration': float(cfg['run_duration']),
                      'near_collision_distance': float(cfg['near_collision_distance']),
                      'output_dir': cfg['output_dir']}
    area = as_list(cfg['allowed_area'])
    if fence and not area:
        area = fence
    if area:
        tracker_params['allowed_area'] = area

    aspi_dir = get_package_share_directory('aspi_bot')
    nodes = [
        Node(package='aspi_bot', executable='random_walker', name='random_walker',
             output='screen', parameters=[sim, walker_params]),
        Node(package='aspi_bot', executable='coverage_tracker', name='coverage_tracker',
             output='screen', parameters=[sim, tracker_params]),
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
    use_sim_time = LaunchConfiguration('use_sim_time')
    localization = LaunchConfiguration('localization')

    args = [
        DeclareLaunchArgument('map', default_value=os.path.join(aspi_dir, 'maps', 'world.yaml'),
                              description='Carte de la zone (vérité terrain de la mesure)'),
        DeclareLaunchArgument('seed', default_value='1'),
        DeclareLaunchArgument('run_duration', default_value='300.0',
                              description='Durée de la mesure en secondes'),
        DeclareLaunchArgument('use_sim_time', default_value='false',
                              description='false sur le robot ; true pour un test avec Gazebo'),
        DeclareLaunchArgument('localization', default_value='amcl',
                              description='amcl ou static (TF identité map -> odom)'),
        DeclareLaunchArgument('forward_speed', default_value='0.10',
                              description='Vitesse d\'avance réduite (sécurité)'),
        DeclareLaunchArgument('turn_speed', default_value='0.6'),
        DeclareLaunchArgument('fence', default_value='[]',
                              description='Barrière virtuelle [xmin, ymin, xmax, ymax] en repère odom'),
        DeclareLaunchArgument('allowed_area', default_value='[]',
                              description='Zone mesurée [xmin, ymin, xmax, ymax] en repère map'),
        DeclareLaunchArgument('near_collision_distance', default_value='0.20',
                              description='0.20 : le LDS-02 ne voit rien sous ~0.16 m'),
        DeclareLaunchArgument('use_rviz', default_value='true'),
        DeclareLaunchArgument('output_dir', default_value=os.path.expanduser('~/ros2_ws/results/robot_reel')),
    ]

    amcl = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'localization_launch.py')),
        launch_arguments={'map': map_yaml, 'use_sim_time': use_sim_time,
                          'params_file': os.path.join(aspi_dir, 'config', 'amcl_real.yaml'),
                          'autostart': 'true', 'use_composition': 'False'}.items(),
        condition=IfCondition(PythonExpression(["'", localization, "' == 'amcl'"])))

    is_static = IfCondition(PythonExpression(["'", localization, "' == 'static'"]))
    map_server = Node(
        package='nav2_map_server', executable='map_server', name='map_server', output='screen',
        parameters=[{'use_sim_time': use_sim_time, 'yaml_filename': map_yaml}], condition=is_static)
    lifecycle = Node(
        package='nav2_lifecycle_manager', executable='lifecycle_manager',
        name='lifecycle_manager_map', output='screen', condition=is_static,
        parameters=[{'use_sim_time': use_sim_time, 'autostart': True,
                     'node_names': ['map_server']}])
    map_to_odom = Node(
        package='tf2_ros', executable='static_transform_publisher', name='map_to_odom',
        arguments=['--frame-id', 'map', '--child-frame-id', 'odom'],
        parameters=[{'use_sim_time': use_sim_time}], condition=is_static)

    return LaunchDescription(args + [amcl, map_server, lifecycle, map_to_odom,
                                     OpaqueFunction(function=project_nodes)])
