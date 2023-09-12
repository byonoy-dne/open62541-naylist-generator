import re
import xml.etree.ElementTree as ET
from typing import NamedTuple
from natsort import natsorted


basedir = "/home/delf/workspace/byonoy/shimmer/nodesets-public/"

full = [
    "AbsorbanceReader.xml",
]
dependencies = [
    "Opc.Ua.AMB.NodeSet2.xml",
    "Opc.Ua.Di.NodeSet2.xml",
    "Opc.Ua.LADS.NodeSet2.xml",
    "Opc.Ua.Machinery.NodeSet2.xml",
    "Opc.Ua.NodeSet2.xml",
]

out_filename = "/tmp/blacklist.txt"

id_pattern = re.compile(r'[>"](ns=(?P<ns>\d+);)?i=(?P<i>\d+)[<"]')


class NodeSetData(NamedTuple):
    contents: str
    tree: ET.Element
    ns_lookup: list[str]


class Node(NamedTuple):
    ns: str
    i: int

    def to_string(self, ns_lookup : list[str] = None):
        if ns_lookup:
            return f"i={self.i}" if len(self.ns) == 0 else f"ns={ns_lookup.index(self.ns)};i={self.i}"
        else:
            return f"i={self.i}" if len(self.ns) == 0 else f"ns={self.ns};i={self.i}"


def namespaces(tree : ET.Element) -> list[str]:
    result : list[str] = [""]
    ns = {'ua': 'http://opcfoundation.org/UA/2011/03/UANodeSet.xsd'}
    for uri in tree.findall('.//ua:NamespaceUris/ua:Uri', ns):
        result.append(uri.text)
    return result


def all_refs(data : NodeSetData) -> set[Node]:
    result : set[Node] = set()

    for match in id_pattern.finditer(data.contents):
        result.add(Node(data.ns_lookup[int(match.group('ns') or 0)], int(match.group('i'))))

    return result


def some_refs(data : NodeSetData, include : set[Node]):
    result : set[Node] = set()

    for node in filter(lambda n: n.ns in data.ns_lookup, include):
        for match in data.tree.findall(f".//*[@NodeId='{node.to_string(data.ns_lookup)}']"):
            result.update(all_refs(NodeSetData(ET.tostring(match, encoding='unicode'), match, data.ns_lookup)))

    return result


def load_node_set(filename : str):
    with open(filename) as f:
        data = f.read()
        tree = ET.fromstring(data)
        return NodeSetData(data, tree, namespaces(tree))


yay = set()
nay = set()
everything = set()

for filename in full:
    print(f"Parsing application nodeset file {filename}")
    nodeset = load_node_set(basedir + '/' + filename)
    yay.update(all_refs(nodeset))

everything.update(yay)

print(f"The application nodesets contain {len(yay)} nodes and direct references")

dep_data = {}
dep_added_nss = []
sorted_deps = []
for filename in dependencies:
    dep_data[filename] = load_node_set(basedir + '/' + filename)

while len(sorted_deps) < len(dep_data):
    for k, v in dep_data.items():
        unknown_nss = list(set(v.ns_lookup).difference(dep_added_nss))
        if len(unknown_nss) == 1:
            sorted_deps.append(v)
            dep_added_nss.append(unknown_nss[0])

dep_added_nss.reverse()
sorted_deps.reverse()

print("Adding dependencies")
for d in dep_added_nss:
    print(f"\t{d or 'Zero'}")

print("This might take a while, especially namespace zero...\n")

for i, nodeset in enumerate(sorted_deps):
    print(f"Parsing dependent nodeset {dep_added_nss[i] or 'Zero'}")
    everything.update(all_refs(nodeset))
    len_before = len(yay)
    while True:
        new_refs = some_refs(nodeset, yay)
        old_len = len(yay)
        yay.update(new_refs)
        if old_len == len(yay):
            break
        print(f"\tAdded another {len(yay) - old_len} transitive references...")

    print(f"\tFound {len(yay) - len_before} additional transitively referenced nodes\n")

print(f"Yay-listed {len(yay)} of {len(everything)} nodes")

nay = everything.difference(yay)

print(f"Nay-listed {len(nay)} of {len(everything)} nodes")

with open(out_filename, 'w') as f:
    for n in natsorted(map(lambda x: x.to_string(), nay)):
        print(n)
        f.write(n + "\n")
