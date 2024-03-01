#!/usr/bin/env python3

import re
import xml.etree.ElementTree as ET
from typing import NamedTuple
from natsort import natsorted
import argparse


parser = argparse.ArgumentParser()
parser.add_argument(
    "full",
    help="Application nodeset files to be included completely",
    nargs="+",
)
parser.add_argument(
    "-d",
    "--dependency",
    help="Nodeset file containing dependencies required by other nodesets. Can be specified multiple times.",
    action="append",
)
parser.add_argument(
    "-o",
    "--output",
    help="Output file name. If none given, the output is printed to STDOUT.",
)
parser.add_argument(
    "--all-refs",
    help="Don't naylist any reference types, even if they are not explcitly used in the application nodesets.",
    action="store_true",
)
parser.add_argument(
    "--all-data",
    help="Don't naylist any data types, even if they are not explcitly used in the application nodesets.",
    action="store_true",
)
parser.add_argument("-v", "--verbose", action="store_true")
args = parser.parse_args()

print_fn = print if args.verbose else lambda _: None
id_pattern = re.compile(r"(ns=(?P<ns>\d+);)?i=(?P<i>\d+)")
embedded_id_pattern = re.compile(r'[>"](ns=(?P<ns>\d+);)?i=(?P<i>\d+)[<"]')


class NodeSetData(NamedTuple):
    contents: str
    tree: ET.Element
    ns_lookup: list[str]


class Node(NamedTuple):
    ns: str
    i: int

    def to_string(self, ns_lookup: list[str] = None):
        if ns_lookup:
            return (
                f"i={self.i}"
                if len(self.ns) == 0
                else f"ns={ns_lookup.index(self.ns)};i={self.i}"
            )
        else:
            return f"i={self.i}" if len(self.ns) == 0 else f"ns={self.ns};i={self.i}"


def namespaces(tree: ET.Element) -> list[str]:
    result: list[str] = [""]
    ns = {"ua": "http://opcfoundation.org/UA/2011/03/UANodeSet.xsd"}
    for uri in tree.findall("./ua:NamespaceUris/ua:Uri", ns):
        result.append(uri.text)
    return result


def all_refs(data: NodeSetData) -> set[Node]:
    result: set[Node] = set()

    for match in embedded_id_pattern.finditer(data.contents):
        result.add(
            Node(data.ns_lookup[int(match.group("ns") or 0)], int(match.group("i")))
        )

    return result


def some_refs(data: NodeSetData, include: set[Node]) -> None:
    result: set[Node] = set()

    for node in filter(lambda n: n.ns in data.ns_lookup, include):
        for match in data.tree.findall(
            f".//*[@NodeId='{node.to_string(data.ns_lookup)}']"
        ):
            result.update(
                all_refs(
                    NodeSetData(
                        ET.tostring(match, encoding="unicode"), match, data.ns_lookup
                    )
                )
            )

    return result


def ref_refs(data: NodeSetData) -> set[Node]:
    result: set[Node] = set()

    for ref in data.tree.findall(".//*[@ReferenceType]"):
        match = id_pattern.match(ref.get("ReferenceType"))
        result.add(
            Node(data.ns_lookup[int(match.group("ns") or 0)], int(match.group("i")))
        )

    return result


def data_types(data: NodeSetData) -> set[Node]:
    result: set[Node] = set()

    ns = {"ua": "http://opcfoundation.org/UA/2011/03/UANodeSet.xsd"}
    for match in data.tree.findall(".//ua:UADataType", ns):
        result.update(
            all_refs(
                NodeSetData(
                    ET.tostring(match, encoding="unicode"), match, data.ns_lookup
                )
            )
        )

    return result


def resolve_aliases(data: str) -> str:
    tree = ET.fromstring(data)
    ns = {"ua": "http://opcfoundation.org/UA/2011/03/UANodeSet.xsd"}
    for alias in tree.findall("./ua:Aliases/ua:Alias", ns):
        pattern = re.compile(f'(?P<open>[>"]){alias.get("Alias")}(?P<close>[<"])')
        data = pattern.sub(f"\\g<open>{alias.text}\\g<close>", data)

    return data


def load_node_set(filename: str) -> NodeSetData:
    with open(filename) as f:
        data = resolve_aliases(f.read())
        tree = ET.fromstring(data)
        return NodeSetData(data, tree, namespaces(tree))


yay: set[Node] = set()
nay: set[Node] = set()
everything: set[Node] = set()

for filename in args.full:
    print_fn(f"Parsing application nodeset {filename}")
    nodeset = load_node_set(filename)
    yay.update(all_refs(nodeset))

everything.update(yay)

print_fn(f"The application nodesets contain {len(yay)} nodes and direct references")

if args.all_refs:
    print_fn("Reference types will not be naylisted")
if args.all_data:
    print_fn("Data types will not be naylisted")

dep_data = {}
dep_added_nss = []
sorted_deps = []
for filename in args.dependency:
    dep_data[filename] = load_node_set(filename)

while len(sorted_deps) < len(dep_data):
    for k, v in dep_data.items():
        unknown_nss = list(set(v.ns_lookup).difference(dep_added_nss))
        if len(unknown_nss) == 1:
            sorted_deps.append(v)
            dep_added_nss.append(unknown_nss[0])

dep_added_nss.reverse()
sorted_deps.reverse()

print_fn("Adding dependencies")
for d in dep_added_nss:
    print_fn(f"\t{d or 'http://opcfoundation.org/UA/'}")

print_fn("\nThis might take a while, especially namespace zero...\n")

for i, nodeset in enumerate(sorted_deps):
    print_fn(f"Parsing dependency {dep_added_nss[i] or 'http://opcfoundation.org/UA/'}")
    everything.update(all_refs(nodeset))

    if args.all_refs:
        refs = ref_refs(nodeset)
        yay.update(refs)
        print_fn(f"\tAdded {len(refs)} reference types...")

    if args.all_data:
        types = data_types(nodeset)
        yay.update(types)
        print_fn(f"\tAdded {len(types)} data types...")

    len_before = len(yay)
    while True:
        new_refs = some_refs(nodeset, yay)
        old_len = len(yay)
        yay.update(new_refs)
        if old_len == len(yay):
            break
        print_fn(f"\tAdded another {len(yay) - old_len} transitive references...")

    print_fn(
        f"\tFound {len(yay) - len_before} additional transitively referenced nodes\n"
    )

print_fn(f"Yay-listed {len(yay)} of {len(everything)} nodes")

nay = everything.difference(yay)
sorted_nay = natsorted(map(lambda x: x.to_string(), nay))

print_fn(f"Nay-listed {len(nay)} of {len(everything)} nodes")

if args.output:
    with open(args.output, "w") as f:
        for n in sorted_nay:
            f.write(n + "\n")
else:
    for n in sorted_nay:
        print(n)
