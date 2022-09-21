# pdblib

pdblib is a library for reading Windows Program Database (.pdb) files created when compiling code.

There is [an existing python library](https://github.com/moyix/pdbparse) to parse PDB files however I found it was very slow to load large pdb files.
It is also quite abstract because it uses a generic parsing engine to do most of the work.

This library directly uses python's struct library to parse the data so there is no abstraction layer.
In my tests it is a few times faster than pdbparse to load a large pdb file.

This most likely will not get updated, but I put it here so that others can build upon it if they so wish.
