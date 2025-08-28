from typing import List, Optional, Type, Union

from sqlalchemy import (
    Boolean,
    Column,
    Engine,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    inspect,
)
from sqlalchemy.orm import DeclarativeBase

from autosubmit_api.logger import logger

## Table utils


def table_copy(table: Table, metadata: Optional[MetaData] = None) -> Table:
    """
    Copy a table schema
    """
    if not isinstance(metadata, MetaData):
        metadata = MetaData()
    return Table(
        table.name,
        metadata,
        *[col.copy() for col in table.columns],
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
    return table_copy(_source_table, metadata)


def check_table_schema(engine: Engine, valid_tables: List[Table]) -> Union[Table, None]:
    """
    Check if one of the valid table schemas matches the current table schema.
    Returns the first matching table schema or None if no match is found.
    ORDER MATTERS!!! Table with more columns (more restrictive) should be first
    """
    for valid_table in valid_tables:
        try:
            # Get the current columns of the table
            current_columns = inspect(engine).get_columns(
                valid_table.name, valid_table.schema
            )
            column_names = [column["name"] for column in current_columns]

            # Get the columns of the valid table
            valid_columns = valid_table.columns.keys()
            # Check if all the valid table columns are present in the current table
            if all(column in column_names for column in valid_columns):
                return valid_table
        except Exception as exc:
            logger.error(f"Error inspecting table {valid_table.name}: {exc}")
            continue
    return None


metadata_obj = MetaData()


## SQLAlchemy tables


ExperimentTable = Table(
    "experiment",
    metadata_obj,
    Column("id", Integer, nullable=False, primary_key=True),
    Column("name", String, nullable=False),
    Column("description", String, nullable=False),
    Column("autosubmit_version", String),
)
"""The main table, populated by Autosubmit. Should be read-only by the API."""


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

ExperimentStatusTable = Table(
    "experiment_status",
    metadata_obj,
    Column("exp_id", Integer, primary_key=True),
    Column("name", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("seconds_diff", Integer, nullable=False),
    Column("modified", Text, nullable=False),
)
"""Stores the status of the experiments."""

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


JobPackageTable = Table(
    "job_package",
    metadata_obj,
    Column("exp_id", Text),
    Column("package_name", Text),
    Column("job_name", Text),
)
"""Stores a mapping between the wrapper name and the actual job in SLURM."""

WrapperJobPackageTable = Table(
    "wrapper_job_package",
    metadata_obj,
    Column("exp_id", Text),
    Column("package_name", Text),
    Column("job_name", Text),
)
"""It is a replication.
It is only created/used when using inspect and create or monitor
with flag -cw in Autosubmit.
This replication is used to not interfere with the current
autosubmit run of that experiment since wrapper_job_package
will contain a preview, not the real wrapper packages."""

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
    Column("runner_extra_params", Text, nullable=True),
)

JobPklTable = Table(
    "job_pkl",
    metadata_obj,
    Column("expid", String, primary_key=True),
    Column("pkl", LargeBinary),
    Column("modified", String),
)

UserPreferencesTable = Table(
    "user_preferences",
    metadata_obj,
    Column("user_id", Text, primary_key=True),
    Column("preferred_username", Text, nullable=False),
    Column("created", Text, nullable=False),
    Column("modified", Text, nullable=False),
)
"""Table that holds user preferences, including preferred Linux username."""

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
    Column("min_trigger_status", String),
    Column("completion_status", String),
    Column("from_step", Integer),
    Column("fail_ok", Boolean),
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
