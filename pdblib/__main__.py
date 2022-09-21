from typing import Optional, Sequence
import argparse
import pathlib

import pdblib
from pdblib._header import create_headers


def arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read and generate data from a Windows PDB file.")

    subparsers = parser.add_subparsers(
        dest="operation", required=True, help="The operation to run."
    )
    path_parser = subparsers.add_parser("header")
    path_parser.add_argument(
        "pdb_path",
        type=pathlib.Path,
        help="The path of the pdb file to load. Must exist.",
    )
    path_parser.add_argument(
        "header_directory", type=pathlib.Path, help="The path of the directory to save header files in."
    )
    return parser


def main(args: Optional[Sequence[str]] = None):
    parsed_args = arg_parser().parse_args(args)
    if parsed_args.operation == "header":
        pdb = pdblib.parse(parsed_args.pdb_path)
        create_headers(pdb, parsed_args.header_directory)


if __name__ == "__main__":
    main()
