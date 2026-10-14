from glob import glob

from setuptools import setup

package_name = 'aspi_bot'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
        ('share/' + package_name + '/maps', glob('maps/*.yaml') + glob('maps/*.pgm')),
        ('share/' + package_name + '/rviz', glob('rviz/*.rviz')),
        ('share/' + package_name + '/worlds', glob('worlds/*.world')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='maxime',
    maintainer_email='contact@willsim.fr',
    description='Robot aspirateur TurtleBot3 : couverture aléatoire et boustrophédon',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'random_walker = aspi_bot.random_walker_node:main',
            'coverage_tracker = aspi_bot.coverage_tracker_node:main',
            'coverage_planner = aspi_bot.coverage_planner_node:main',
            'coverage_executor = aspi_bot.coverage_executor_node:main',
            'coverage_follower = aspi_bot.coverage_follower_node:main',
        ],
    },
)
