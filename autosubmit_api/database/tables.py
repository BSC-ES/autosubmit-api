from typing import Type, Union
from sqlalchemy import Column, Integer, MetaData, Text, Table
from sqlalchemy.orm import DeclarativeBase
from autosubmit.database.tables import (
    metadata_obj,
    ExperimentTable,
    ExperimentStructureTable,
    ExperimentStatusTable,
    JobPackageTable,
    WrapperJobPackageTable,
    ExperimentRunTable,
    JobDataTable,
)


def table_change_schema(
    schema: str, source: Union[Type[DeclarativeBase], Table]
) -> Table:
    """
    Copy the source table and change the schema of that SQLAlchemy table into a new table instance
    """
    if isinstance(source, type) and issubclass(source, DeclarativeBase):
        _source_table: Table = source.__table__
    elif isinstance(source, Table):
        _source_table = source
    else:
        raise RuntimeError("Invalid source type on table schema change")

    metadata = MetaData(schema=schema)
    dest_table = Table(_source_table.name, metadata)

    for col in _source_table.columns:
        dest_table.append_column(col.copy())

    return dest_table


## API extended SQLAlchemy Core tables

DetailsTable = Table(
    "details",
    metadata_obj,
    Column("exp_id", Integer, primary_key=True),
    Column("user", Text, nullable=False),
    Column("created", Text, nullable=False),
    Column("model", Text, nullable=False),
    Column("branch", Text, nullable=False),
    Column("hpc", Text, nullable=False),
)
"""Stores extra information. It is populated by the API."""


GraphDataTable = Table(
    "experiment_graph_draw",
    metadata_obj,
    Column("id", Integer, primary_key=True),
    Column("job_name", Text, nullable=False),
    Column("x", Integer, nullable=False),
    Column("y", Integer, nullable=False),
)
"""Stores the coordinates and it is used exclusively 
to speed up the process of generating the graph layout"""

# Module exports
__all__ = [
    "table_change_schema",
    "ExperimentTable",
    "ExperimentStructureTable",
    "ExperimentStatusTable",
    "JobPackageTable",
    "WrapperJobPackageTable",
    "ExperimentRunTable",
    "JobDataTable",
    "DetailsTable",
    "GraphDataTable",
]
