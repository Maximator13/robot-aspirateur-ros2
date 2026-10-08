"""Stratégie A — aléatoire (bump and turn).

Lance : Gazebo (turtlebot3_world) + map_server (carte de référence, vérité terrain pour la mesure)
+ TF statique map -> odom + random_walker + coverage_tracker + RViz.

Le robot n'utilise PAS la carte : elle sert uniquement au tracker pour calculer le % couvert.
Hypothèse : la carte a été construite depuis la position de spawn, donc l'origine de map = spawn ;
odom (Gazebo) est en coordonnées monde -> map -> odom = translation de -spawn
(dérive d'odométrie négligée en simulation — limite notée dans le journal).

Exemples :
  ros2 launch aspi_bot aspi_random.launch.py seed:=2                            # avec fenêtres
  ros2 launch aspi_bot aspi_random.launch.py seed:=2 headless:=true fast:=true  # protocole accéléré
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def gzserver(gazebo_ros_dir, world_file, condition, lockstep):
    """Serveur Gazebo (physique + capteurs) sur un monde donné."""
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_ros_dir, 'launch', 'gzserver.launch.py')),
        launch_arguments={'world': world_file, 'lockstep': lockstep}.items(),
        condition=condition)


def generate_launch_description():
    aspi_dir = get_package_share_directory('aspi_bot')
    tb3_gazebo_dir = get_package_share_directory('turtlebot3_gazebo')
    gazebo_ros_dir = get_package_share_directory('gazebo_ros')

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
        # Position de spawn dans le monde Gazebo (= origine de la carte de référence)
        DeclareLaunchArgument('spawn_x', default_value='-2.0'),
        DeclareLaunchArgument('spawn_y', default_value='-0.5'),
    ]

    # --- Gazebo ---
    # Monde d'origine (temps réel) ou copie accélérée (real_time_update_rate = 0).
    # En accéléré, lockstep : la physique attend la mise à jour des capteurs (pas de scan perdu).
    # Choix assumé : gzserver.launch.py déclare aussi un argument « seed », il reçoit donc
    # notre graine -> le générateur aléatoire de Gazebo est fixé lui aussi (reproductibilité).
    gzserver_normal = gzserver(
        gazebo_ros_dir, os.path.join(tb3_gazebo_dir, 'worlds', 'turtlebot3_world.world'),
        UnlessCondition(fast), 'false')
    gzserver_fast = gzserver(
        gazebo_ros_dir, os.path.join(aspi_dir, 'worlds', 'turtlebot3_world_fast.world'),
        IfCondition(fast), 'true')
    gzclient = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_ros_dir, 'launch', 'gzclient.launch.py')),
        condition=UnlessCondition(headless))

    robot_state_publisher = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(tb3_gazebo_dir, 'launch', 'robot_state_publisher.launch.py')),
        launch_arguments={'use_sim_time': 'true'}.items())

    # Spawn du robot : timeout porté à 120 s (sous WSL, Gazebo peut mettre plus de 30 s à démarrer)
    spawn = Node(
        package='gazebo_ros', executable='spawn_entity.py', output='screen',
        arguments=['-entity', 'burger',
                   '-file', os.path.join(tb3_gazebo_dir, 'models', 'turtlebot3_burger',
                                         'model.sdf'),
                   '-x', spawn_x, '-y', spawn_y, '-z', '0.01',
                   '-timeout', '120'])

    # --- Carte de référence : map_server (nœud lifecycle) activé par le lifecycle_manager ---
    map_server = Node(
        package='nav2_map_server', executable='map_server', name='map_server',
        output='screen', parameters=[sim, {'yaml_filename': map_yaml}])
    lifecycle_manager = Node(
        package='nav2_lifecycle_manager', executable='lifecycle_manager',
        name='lifecycle_manager_map', output='screen',
        parameters=[sim, {'autostart': True, 'node_names': ['map_server']}])

    # Pas de localisation en stratégie A : TF statique map -> odom.
    # Le plugin diff_drive de Gazebo publie odom dans le repère du MONDE (robot en
    # (-2.0, -0.5) au spawn), alors que la carte a son origine au spawn :
    # map -> odom est donc une translation de -spawn (et non l'identité).
    map_to_odom = Node(
        package='tf2_ros', executable='static_transform_publisher', name='map_to_odom',
        arguments=['--x', PythonExpression(['-(', spawn_x, ')']),
                   '--y', PythonExpression(['-(', spawn_y, ')']),
                   '--frame-id', 'map', '--child-frame-id', 'odom'],
        parameters=[sim])

    # --- Nœuds du projet ---
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
        parameters=[sim], condition=UnlessCondition(headless))

    return LaunchDescription(args + [
        gzserver_normal, gzserver_fast, gzclient, robot_state_publisher, spawn,
        map_server, lifecycle_manager, map_to_odom, walker, tracker, rviz])
