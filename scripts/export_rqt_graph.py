"""Exporte le graphe nœuds/topics du système qui tourne, avec le moteur de rqt_graph.

Même code que rqt_graph (paquet rqt_graph, mode « Nodes/Topics (active) »), sans la fenêtre :
le graphe est écrit en .dot puis rendu en PNG par Graphviz.
Usage (ROS sourcé, système lancé) : python3 export_rqt_graph.py <sortie.png> [secondes d'attente]
"""
import subprocess
import sys
import time

import rclpy
from qt_dotgraph.pydotfactory import PydotFactory
from rqt_graph.dotcode import NODE_TOPIC_GRAPH, RosGraphDotcodeGenerator
from rqt_graph.rosgraph2_impl import Graph


def main():
    out = sys.argv[1]
    attente = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
    rclpy.init()
    node = rclpy.create_node('export_rqt_graph')
    t_fin = time.time() + attente           # laisser la découverte DDS trouver tous les nœuds
    while time.time() < t_fin:
        rclpy.spin_once(node, timeout_sec=0.2)
    graph = Graph(node)
    graph.update()
    dot = RosGraphDotcodeGenerator(node).generate_dotcode(
        rosgraphinst=graph, ns_filter='/', topic_filter='/', graph_mode=NODE_TOPIC_GRAPH,
        dotcode_factory=PydotFactory(), orientation='LR',
        hide_single_connection_topics=False, hide_dead_end_topics=False,
        cluster_namespaces_level=0, accumulate_actions=True, quiet=True, unreachable=True,
        group_tf_nodes=True, hide_tf_nodes=False, hide_dynamic_reconfigure=True)
    dot_path = out.rsplit('.', 1)[0] + '.dot'
    with open(dot_path, 'w') as f:
        f.write(dot)
    subprocess.run(['dot', '-Tpng', '-Gdpi=130', dot_path, '-o', out], check=True)
    print('graphe écrit :', out)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
