from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

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
"""Table that holds the structure of the experiment jobs. Before autosubmit 4.1.16"""

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

UserMetricTable = Table(
    "user_metrics",
    metadata_obj,
    Column("user_metric_id", Integer, primary_key=True),
    Column("run_id", Integer, nullable=False),
    Column("job_name", Text, nullable=False),
    Column("metric_name", Text, nullable=False),
    Column("metric_value", Text, nullable=False),
    Column("modified", Text, nullable=False),
)

RunnerProcessesTable = Table(
    "runner_processes",
    metadata_obj,
    Column("id", Integer, primary_key=True),
    Column("expid", Text, nullable=False),
    Column("pid", Integer, nullable=False),
    Column("status", String(50), nullable=False),
    Column("runner", String(50), nullable=False),
    Column("module_loader", String(50), nullable=False),
    Column("modules", Text, nullable=False),
    Column("created", Text, nullable=False),
    Column("modified", Text, nullable=False),
)

JobsTable = Table(
    "jobs",
    metadata_obj,
    Column("name", String, nullable=False, primary_key=True),
    Column("id", Integer),
    Column("script_name", String),
    Column("priority", Integer),
    Column("status", String, nullable=False),  # Should be job_status_enum
    Column("frequency", String),  # TODO move to Section table ?
    Column("synchronize", Boolean),  # TODO move to Section table ?
    Column("section", String, ForeignKey("sections.name")),
    Column("chunk", Integer),
    Column("member", Text),
    Column("splits", Integer),
    Column("split", Integer),
    Column("date", String),
    Column("date_split", String),
    Column("max_checkpoint_step", Integer, nullable=False, default=0),
    Column("start_time", String),
    Column("start_time_timestamp", Float),
    Column("submit_time_timestamp", Float),
    Column("finish_time_timestamp", Float),
    Column("ready_date", String),
    Column("local_logs_out", String),  # tuple, to modify double value in two
    Column("local_logs_err", String),  # tuple, to modify double value in two
    Column("remote_logs_out", String),
    Column("remote_logs_err", String),
    Column("updated_log", Boolean),
    Column("packed", Boolean),
    Column("current_checkpoint_step", Integer, nullable=False, default=0),
    Column("platform_name", String),
)

ExperimentStructureDBTable = Table(
    "experiment_structure",
    MetaData(),
    Column(
        "e_from", String, ForeignKey("jobs.job_name"), nullable=False, primary_key=True
    ),
    Column(
        "e_to", String, ForeignKey("jobs.job_name"), nullable=False, primary_key=True
    ),
    Column("status", String),  # TODO To rename to target_status
    Column(
        "completed", String
    ),  # TODO to rename to edge_is_completed? (WAITING | RUNNING | COMPLETED)
    Column("from_step", Integer),
    Column("optional", Boolean),
    UniqueConstraint("e_from", "e_to", name="unique_e_from_and_e_to"),
)
"""Table that holds the structure of the experiment jobs. After autosubmit 4.1.16"""


def create_wrapper_tables(name, metadata_obj_):
    """Create a wrapper table for the given name."""
    table_package_info = Table(
        f"{name}_info",
        metadata_obj_,
        Column("name", String, nullable=False, primary_key=True),
        Column("id", Integer),
        Column("script_name", String),
        Column("status", String, nullable=False),  # Should be job_status_enum
        Column(
            "local_logs_out", String
        ),  # TODO: We should recover the log from the remote at some point
        Column(
            "local_logs_err", String
        ),  # TODO: We should recover the log from the remote at some point
        Column(
            "remote_logs_out", String
        ),  # TODO: We should recover the log from the remote at some point
        Column(
            "remote_logs_err", String
        ),  # TODO: We should recover the log from the remote at some point
        Column(
            "updated_log", Boolean
        ),  # TODO: We should recover the log from the remote at some point
        Column("platform_name", String),
        Column("wallclock", String),
        Column("num_processors", Integer),
        Column("type", Text),
        Column("sections", Text),
        Column("method", Text),
    )

    table_jobs_inside_wrapper = Table(
        f"{name}_jobs",
        metadata_obj_,
        Column(
            "package_id",
            Integer,
            ForeignKey("{name}_info.id"),
            nullable=False,
            primary_key=True,
        ),
        Column(
            "package_name",
            String,
            ForeignKey(f"{name}_info.name"),
            nullable=False,
            primary_key=True,
        ),
        Column(
            "job_name",
            String,
            ForeignKey("jobs.name"),
            nullable=False,
            primary_key=True,
        ),
        Column("timestamp", String, nullable=True),
    )
    return table_package_info, table_jobs_inside_wrapper


WrapperInfoTable, WrapperJobsTable = create_wrapper_tables("wrappers", metadata_obj)
PreviewWrapperInfoTable, PreviewWrapperJobsTable = create_wrapper_tables(
    "preview_wrappers", metadata_obj
)
