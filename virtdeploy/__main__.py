import argparse
import sys
import virtdeploy
import logging
import os.path


def createParser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--create', metavar="[file.toml]", help="Create cluster described in file")
    parser.add_argument('-d', '--delete', metavar="\"ClusterName\"", help="Delete cluster by name")
    parser.add_argument('-r', '--run', metavar="\"ClusterName\"", help="Run all cluster vm`s")
    parser.add_argument('-s', '--stop', metavar="\"ClusterName\"", help="Stop all cluster vm`s")
    parser.add_argument('-g', '--get-info', metavar="\"ClusterName\"", help="Get info about cluster")

    return parser


parser = createParser()
namespace = parser.parse_args(sys.argv[1:])

if namespace.create:
    if os.path.isfile(namespace.create):
        virtdeploy.initCluster(namespace.create)
    else:
        logging.fatal(f"{namespace.create} is not a file")
    sys.exit(0)

if namespace.delete:
    virtdeploy.destroyCluster(namespace.delete)
    sys.exit(0)
