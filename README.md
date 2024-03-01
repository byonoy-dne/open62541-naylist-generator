Takes an application nodeset consisting of one or more nodeset files and their dependencies, and generates a text file listing all nodes from the dependent nodesets that were not referenced in the application nodeset. The resulting file can be used as input for the open62541 nodeset compiler's `--blacklist` parameter.

This tool should be considered _experimental_, at best. It was clobbered together at a hackathon and has not been used in a production environment.

Also, I think, the open62541 nodeset compiler has a bug when using a blacklist, but I have not had the time to raise an issue upstream. This repo contains a patch for reference.

```
usage: generate_naylist.py [-h] [-d DEPENDENCY] [-o OUTPUT] [--all-refs] [--all-data] [-v] full [full ...]

positional arguments:
  full                  Application nodeset files to be included completely

options:
  -h, --help            show this help message and exit
  -d DEPENDENCY, --dependency DEPENDENCY
                        Nodeset file containing dependencies required by other nodesets. Can be specified multiple times.
  -o OUTPUT, --output OUTPUT
                        Output file name. If none given, the output is printed to STDOUT.
  --all-refs            Don't naylist any reference types, even if they are not explcitly used in the application nodesets.
  --all-data            Don't naylist any data types, even if they are not explcitly used in the application nodesets.
  -v, --verbose
```

For example:

```
generate_nay_list.py \
    AbsorbanceReader.xml Opc.Ua.LADS.NodeSet2.xml \
    --dependency Opc.Ua.AMB.NodeSet2.xml \
    --dependency Opc.Ua.Di.NodeSet2.xml \
    --dependency Opc.Ua.Machinery.NodeSet2.xml \
    --dependency Opc.Ua.NodeSet2.xml \
    --all-refs --all-data \
    --output nay_list.txt \
    --verbose
```
