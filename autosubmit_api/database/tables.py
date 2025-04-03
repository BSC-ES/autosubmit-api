from sqlalchemy import (
    Column,
    Float,
    MetaData,
    Integer,
    String,
    Text,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped

## Table utils


def table_copy(table: Table) -> Table:
    """
    Copy a table schema
    """
    return Table(
        table.name,
        MetaData(),
        *[col.copy() for col in table.columns],
    )


metadata_obj = MetaData()


## SQLAlchemy ORM tables
class BaseTable(DeclarativeBase):
    metadata = metadata_obj


class ExperimentTable(BaseTable):
    """
    Is the main table, populated by Autosubmit. Should be read-only by the API.
    """

    __tablename__ = "experiment"

    id: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    autosubmit_version: Mapped[str] = mapped_column(String)


class DetailsTable(BaseTable):
    """
    Stores extra information. It is populated by the API.
    """

    __tablename__ = "details"

    exp_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user: Mapped[str] = mapped_column(Text, nullable=False)
    created: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    branch: Mapped[str] = mapped_column(Text, nullable=False)
    hpc: Mapped[str] = mapped_column(Text, nullable=False)


class ExperimentStatusTable(BaseTable):
    """
    Stores the status of the experiments
    """

    __tablename__ = "experiment_status"

    exp_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    seconds_diff: Mapped[int] = mapped_column(Integer, nullable=False)
    modified: Mapped[str] = mapped_column(Text, nullable=False)


ExperimentStructureTable = Table(
    "experiment_structure",
    metadata_obj,
    Column("e_from", Text, nullable=False, primary_key=True),
    Column("e_to", Text, nullable=False, primary_key=True),
)
"""Table that holds the structure of the experiment jobs."""

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


class JobPackageTable(BaseTable):
    """
    Stores a mapping between the wrapper name and the actual job in slurm
    """

    __tablename__ = "job_package"

    exp_id: Mapped[str] = mapped_column(Text)
    package_name: Mapped[str] = mapped_column(Text, primary_key=True)
    job_name: Mapped[str] = mapped_column(Text, primary_key=True)


class WrapperJobPackageTable(BaseTable):
    """
    It is a replication. It is only created/used when using inspectand create or monitor
    with flag -cw in Autosubmit.\n
    This replication is used to not interfere with the current autosubmit run of that experiment
    since wrapper_job_package will contain a preview, not the real wrapper packages
    """

    __tablename__ = "wrapper_job_package"

    exp_id: Mapped[str] = mapped_column(Text)
    package_name: Mapped[str] = mapped_column(Text, primary_key=True)
    job_name: Mapped[str] = mapped_column(Text, primary_key=True)


## SQLAlchemy Core tables

# MAIN_DB TABLES
experiment_table: Table = ExperimentTable.__table__
details_table: Table = DetailsTable.__table__

# AS_TIMES TABLES
experiment_status_table: Table = ExperimentStatusTable.__table__

# Graph Data TABLES
graph_data_table: Table = GraphDataTable

# Job package TABLES
job_package_table: Table = JobPackageTable.__table__
wrapper_job_package_table: Table = WrapperJobPackageTable.__table__

ExperimentRunTable = Table(
    "experiment_run",
    metadata_obj,
    Column("run_id", Integer, primary_key=True),
    Column("created", Text, nullable=False),
    Column("modified", Text, nullable=True),
    Column("start", Integer, nullable=False),
    Column("finish", Integer),
    Column("chunk_unit", Text, nullable=False),
    Column("chunk_size", Integer, nullable=False),
    Column("completed", Integer, nullable=False),
    Column("total", Integer, nullable=False),
    Column("failed", Integer, nullable=False),
    Column("queuing", Integer, nullable=False),
    Column("running", Integer, nullable=False),
    Column("submitted", Integer, nullable=False),
    Column("suspended", Integer, nullable=False, default=0),
    Column("metadata", Text),
)

JobDataTable = Table(
    "job_data",
    metadata_obj,
    Column("id", Integer, nullable=False, primary_key=True),
    Column("counter", Integer, nullable=False),
    Column("job_name", Text, nullable=False, index=True),
    Column("created", Text, nullable=False),
    Column("modified", Text, nullable=False),
    Column("submit", Integer, nullable=False),
    Column("start", Integer, nullable=False),
    Column("finish", Integer, nullable=False),
    Column("status", Text, nullable=False),
    Column("rowtype", Integer, nullable=False),
    Column("ncpus", Integer, nullable=False),
    Column("wallclock", Text, nullable=False),
    Column("qos", Text, nullable=False),
    Column("energy", Integer, nullable=False),
    Column("date", Text, nullable=False),
    Column("section", Text, nullable=False),
    Column("member", Text, nullable=False),
    Column("chunk", Integer, nullable=False),
    Column("last", Integer, nullable=False),
    Column("platform", Text, nullable=False),
    Column("job_id", Integer, nullable=False),
    Column("extra_data", Text, nullable=False),
    Column("nnodes", Integer, nullable=False, default=0),
    Column("run_id", Integer),
    Column("MaxRSS", Float, nullable=False, default=0.0),
    Column("AveRSS", Float, nullable=False, default=0.0),
    Column("out", Text, nullable=False),
    Column("err", Text, nullable=False),
    Column("rowstatus", Integer, nullable=False, default=0),
    Column("children", Text, nullable=True),
    Column("platform_output", Text, nullable=True),
    UniqueConstraint("counter", "job_name", name="unique_counter_and_job_name"),
)

# Copy JobDataTable to an alternative version which has an additional column
JobDataTableV18 = table_copy(JobDataTable)
JobDataTableV18.append_column(Column("workflow_commit", Text, nullable=True))
