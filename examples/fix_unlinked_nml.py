import xml.etree.ElementTree as ET
import sys
import numpy as np
import scipy.sparse.csgraph
from argparse import ArgumentParser
from collections import defaultdict

import wknml


def flatten(l):
    return [x for y in l for x in y]


def find(pred, l):
    return next(x for x in l if pred(x))


parser = ArgumentParser(description="Splits trees in order to fix unlinked nodes.")
parser.add_argument("source", help="Source NML file")
parser.add_argument("target", help="Target NML file")
args = parser.parse_args()


file = wknml.parse_nml(ET.parse(args.source).getroot())

all_nodes = flatten([t.nodes for t in file.trees])
all_edges = flatten([t.edges for t in file.trees])

all_node_ids = [n.id for n in all_nodes]
max_node_id = max(all_node_ids) + 1
print(
    "trees={} nodes={} edges={} max_node={}".format(
        len(file.trees), len(all_nodes), len(all_edges), max_node_id
    )
)

mat = scipy.sparse.lil_matrix((max_node_id, max_node_id))
for edge in all_edges:
    mat[edge.source, edge.target] = 1

# mat_sparse = scipy.sparse.csgraph.csgraph_from_dense(mat)
n_components, labels = scipy.sparse.csgraph.connected_components(
    csgraph=mat, directed=False
)

old_new_mapping = defaultdict(list)
new_trees = []
for i in range(n_components):
    node_ids, = np.where(labels == i)
    node_ids = node_ids.tolist()
    if len(node_ids) == 1 and node_ids[0] not in all_node_ids:
        continue

    old_tree = find(lambda t: any(n.id in node_ids for n in t.nodes), file.trees)
    new_tree = wknml.Tree(
        id=i,
        color=old_tree.color,
        name=old_tree.name,
        groupId=old_tree.groupId,
        nodes=[n for n in all_nodes if n.id in node_ids],
        edges=[e for e in all_edges if e.source in node_ids or e.target in node_ids],
    )
    old_new_mapping[old_tree.id].append(i)
    new_trees.append(new_tree)

max_tree_id = max(t.id for t in new_trees)

new_trees2 = []
new_groups = []
for i, (old_id, new_ids) in enumerate(old_new_mapping.items()):
    group_id = i + max_tree_id + 1
    old_tree = find(lambda t: t.id == old_id, file.trees)
    new_groups.append(wknml.Group(id=group_id, name=old_tree.name))
    for new_id in new_ids:
        new_tree = find(lambda t: t.id == new_id, new_trees)
        new_trees2.append(new_tree._replace(groupId=group_id))

file = file._replace(trees=new_trees2, groups=new_groups)

with open(args.target, "wb") as f:
    f.write(ET.tostring(wknml.dump_nml(file)))
