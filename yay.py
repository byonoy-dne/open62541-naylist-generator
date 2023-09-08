import re
import xml.etree.ElementTree as ET

basedir = "/home/delf/workspace/byonoy/shimmer/nodesets-public/"

full = [
    "AbsorbanceReader.xml",
]
dependent = [
    "Opc.Ua.AMB.NodeSet2.xml",
    "Opc.Ua.Di.NodeSet2.xml",
    "Opc.Ua.LADS.NodeSet2.xml",
    "Opc.Ua.Machinery.NodeSet2.xml",
]
ns0 = "Opc.Ua.NodeSet2.xml"

yay = set()
pattern = re.compile(r'[^;](i=\d+)')

for filename in depends:
    print(f"Parsing {filename}")
    with open(basedir + '/' + filename) as f:
        for line in f:
            for match in pattern.findall(line):
                yay.add(match)

print(yay)

with open(basedir + '/' + ns0) as f:
    root = ET.fromstring(f.read())

    while True:
        new_yay = yay.copy()

        for nodeid in yay:
            for match in root.findall(f".//*[@NodeId='{nodeid}']"):
                contents = ET.tostring(match, encoding='unicode')
                for match in pattern.findall(contents):
                    new_yay.add(match)

        if len(new_yay) == len(yay):
            break

        print(f"Yay list length {len(new_yay)}")
        yay = new_yay

    # print(yay)

    nay = set()

    for match in root.findall(f".//*[@NodeId]"):
        nodeid = match.get("NodeId")
        if not nodeid in yay:
            nay.add(nodeid)

    print(f"Nay list length: {len(nay)}")
    print("\n".join(nay))



