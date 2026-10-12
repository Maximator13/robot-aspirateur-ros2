"""Simulation commune aux stratégies A et B : Gazebo (turtlebot3_world) + robot burger.

Inclus par aspi_random.launch.py et aspi_planned.launch.py, pour que les deux stratégies
tournent exactement dans le même monde, avec le même robot et la même position de départ.

Arguments :
  headless : true -> pas de gzclient (fenêtre Gazebo)
  fast     : true -> monde accéléré (real_time_update_rate = 0) + lockstep
  spawn_x, spawn_y : position de départ dans le monde (= origine de la carte de référence) ;
                     défaut (-2.0, -0.5) = turtlebot3_world
  world_file : autre monde .world (ex. jumeau de la zone réelle : worlds/zone_reelle.world, à lancer
               avec spawn_x:=0.0 spawn_y:=0.0) ; vide = monde du protocole. Si renseigné, fast est
               ignoré (monde en temps réel, lockstep false).
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


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

    headless = LaunchConfiguration('headless')
    fast = LaunchConfiguration('fast')
    spawn_x = LaunchConfiguration('spawn_x')
    spawn_y = LaunchConfiguration('spawn_y')
    world_file = LaunchConfiguration('world_file')

    args = [
        DeclareLaunchArgument('headless', default_value='false',
                              description='true : pas de fenêtre Gazebo'),
        DeclareLaunchArgument('fast', default_value='false',
                              description='true : monde sans limite de temps réel (accéléré)'),
        DeclareLaunchArgument('spawn_x', default_value='-2.0'),
        DeclareLaunchArgument('spawn_y', default_value='-0.5'),
        # Autre monde (ex. jumeau de la zone réelle, worlds/zone_reelle.world) ; vide = turtlebot3_world
        DeclareLaunchArgument('world_file', default_value='',
                              description='Chemin d\'un monde .world (temps réel) ; vide = monde du protocole'),
    ]
    sans_monde = ["'", world_file, "' == ''"]

    # Monde d'origine (temps réel) ou copie accélérée (real_time_update_rate = 0).
    # En accéléré, lockstep : la physique attend la mise à jour des capteurs (pas de scan perdu).
    # Choix assumé : gzserver.launch.py déclare aussi un argument « seed » ; s'il est défini par
    # le launch parent, le générateur aléatoire de Gazebo est fixé lui aussi (reproductibilité).
    gzserver_normal = gzserver(
        gazebo_ros_dir, os.path.join(tb3_gazebo_dir, 'worlds', 'turtlebot3_world.world'),
        IfCondition(PythonExpression(sans_monde + [" and '", fast, "'.lower() not in ('true', '1')"])), 'false')
    gzserver_fast = gzserver(
        gazebo_ros_dir, os.path.join(aspi_dir, 'worlds', 'turtlebot3_world_fast.world'),
        IfCondition(PythonExpression(sans_monde + [" and '", fast, "'.lower() in ('true', '1')"])), 'true')
    gzserver_monde = gzserver(
        gazebo_ros_dir, world_file,
        IfCondition(PythonExpression(["'", world_file, "' != ''"])), 'false')
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

    return LaunchDescription(args + [
        gzserver_normal, gzserver_fast, gzserver_monde, gzclient, robot_state_publisher, spawn])
