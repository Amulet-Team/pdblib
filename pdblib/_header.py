import os

from undname import undname, UndnameFailure

from ._pdb import PDB7
from ._stream.module import PublicSymbol, LocalProcedure, LocalProcedureReference


def create_headers(pdb: PDB7, path: str):
    """Generate header files from a program database"""
    os.makedirs(path, exist_ok=True)

    groups: dict[str, list[str]] = {}
    for symbol in pdb.SymRecordStream:
        record = symbol.RecordData
        if isinstance(record, (PublicSymbol, LocalProcedure, LocalProcedureReference)):
            record_descriptor_raw = record.name.decode()
            try:
                record_name: str = undname(record_descriptor_raw, name_only=True)
            except UndnameFailure:
                groups.setdefault("uncategorised", []).append(f"// {record_descriptor_raw}\n\n")
            else:
                group_name, *other = record_name.split("::", 1)
                if other and group_name.isalnum():
                    group = groups.setdefault(group_name, [])
                    group.append(f"// {record_descriptor_raw}\n")
                    try:
                        record_descriptor = undname(record_descriptor_raw)
                    except UndnameFailure:
                        pass
                    else:
                        group.append(f"{record_descriptor}\n")
                    group.append("\n")
                else:
                    groups.setdefault("uncategorised", []).append(f"// {record_descriptor_raw}\n\n")
        else:
            raise NotImplementedError

    for group_name, group in groups.items():
        with open(os.path.join(path, f"{group_name}.hpp"), "w") as f:
            f.write("".join(group))
