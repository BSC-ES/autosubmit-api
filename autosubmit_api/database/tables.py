from sqlalchemy import Column, MetaData, Integer, String, Text, Table
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped


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
