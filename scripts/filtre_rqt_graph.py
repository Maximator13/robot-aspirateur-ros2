"""Allège un graphe exporté par export_rqt_graph.py : ne garde que nos nœuds et leurs topics.

Les nœuds fournis par Gazebo, Nav2, map_server, robot_state_publisher, etc. sont retirés ;
les topics reliés à nos nœuds sont gardés, pour voir ce que chacun lit et publie.
Actions : les topics internes /<action>/_action/* sont regroupés en une seule boîte « action ».
Seule l'action réellement utilisée (follow_waypoints) est gardée : le client BasicNavigator
ouvre aussi des clients vers les autres actions de Nav2, qu'il n'appelle pas.
Usage : python3 filtre_rqt_graph.py <graphe.dot> <sortie.png>
"""
import subprocess
import sys

import pydot

NOS_NOEUDS = {'random_walker', 'coverage_planner', 'coverage_executor',
              'coverage_follower', 'coverage_tracker'}
ACTIONS_UTILISEES = {'follow_waypoints'}
COULEURS = {'random_walker': '#B04A06', 'coverage_planner': '#1F5F99',
            'coverage_executor': '#1F5F99', 'coverage_follower': '#1F5F99',
            'coverage_tracker': '#172236'}


def nom(node):
    return node.get_label().strip('"').lstrip('/') if node.get_label() else node.get_name()


def main():
    graph = pydot.graph_from_dot_file(sys.argv[1])[0]
    noeuds = {n.get_name(): n for n in graph.get_nodes() if n.get_name() not in ('node', 'graph', 'edge')}
    for sub in graph.get_subgraphs():                     # actions regroupées par rqt_graph
        for n in sub.get_nodes():
            noeuds[n.get_name()] = n
    aretes = list(graph.get_edges()) + [e for s in graph.get_subgraphs() for e in s.get_edges()]

    est_ros = lambda k: noeuds[k].get_shape() == 'ellipse'
    garde = {k for k in noeuds if est_ros(k) and nom(noeuds[k]) in NOS_NOEUDS}
    lien = [(e.get_source(), e.get_destination()) for e in aretes]
    topics = {s for s, d in lien if d in garde} | {d for s, d in lien if s in garde}
    garde |= {k for k in topics if k in noeuds and not est_ros(k)}

    # Actions : regrouper /<action>/_action/feedback|status en une boîte, ne garder que celles utilisées
    actions = {}
    for k in list(garde):
        if not est_ros(k) and '/_action/' in nom(noeuds[k]):
            action = nom(noeuds[k]).split('/_action/')[0]
            garde.discard(k)
            if action in ACTIONS_UTILISEES:
                actions[k] = 'action_' + action
    out = pydot.Dot(graph_type='digraph', rankdir='LR', ranksep='0.6', nodesep='0.35')
    for k in sorted(garde):
        n = noeuds[k]
        label = '/' + nom(n) if not nom(n).startswith('/') else nom(n)
        if est_ros(k):
            c = COULEURS[nom(n)]
            out.add_node(pydot.Node(k, label=nom(n), shape='box', style='"rounded,filled,bold"',
                                    fillcolor='#FFFFFF', color=c, fontcolor=c, fontname='Helvetica-Bold',
                                    fontsize='18', penwidth='2.5'))
        else:
            out.add_node(pydot.Node(k, label=label, shape='box', style='"rounded,filled"',
                                    fillcolor='#F3DCC6', color='#F3DCC6', fontname='Courier', fontsize='16'))
    for a in sorted(set(actions.values())):
        out.add_node(pydot.Node(a, label='action /' + a[len('action_'):], shape='box',
                                style='"rounded,filled,dashed"', fillcolor='#D3E1EE', color='#1F5F99',
                                fontname='Courier', fontsize='16'))
    vus = set()
    for s, d in sorted(set(lien)):
        if s in actions and d in garde:          # le nœud client appelle l'action
            s, d = d, actions[s]
            if (s, d) in vus:
                continue
            vus.add((s, d))
            out.add_edge(pydot.Edge(s, d, color='#1F5F99', penwidth='1.6', style='dashed'))
        elif s in garde and d in garde:
            out.add_edge(pydot.Edge(s, d, color='#172236', penwidth='1.6'))
    dot_path = sys.argv[2].rsplit('.', 1)[0] + '.dot'
    out.write_raw(dot_path)
    subprocess.run(['dot', '-Tpng', '-Gdpi=130', dot_path, '-o', sys.argv[2]], check=True)
    print('graphe allégé :', sys.argv[2], len(garde), 'éléments')


if __name__ == '__main__':
    main()
