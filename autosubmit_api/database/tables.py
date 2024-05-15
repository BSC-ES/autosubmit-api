from sqlalchemy import Integer, Text, Table
from sqlalchemy.orm import mapped_column, Mapped
from autosubmit.database.tables import (
    BaseTable,
    ExperimentTable,
    ExperimentStatusTable,
    JobPackageTable,
    WrapperJobPackageTable,
)

## SQLAlchemy ORM tables
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


class GraphDataTable(BaseTable):
    """
    Stores the coordinates and it is used exclusively to speed up the process
    of generating the graph layout
    """

    __tablename__ = "experiment_graph_draw"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_name: Mapped[str] = mapped_column(Text, nullable=False)
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)


## SQLAlchemy Core tables

# MAIN_DB TABLES
experiment_table: Table = ExperimentTable.__table__
details_table: Table = DetailsTable.__table__

# AS_TIMES TABLES
experiment_status_table: Table = ExperimentStatusTable.__table__

# Graph Data TABLES
graph_data_table: Table = GraphDataTable.__table__

# Job package TABLES
job_package_table: Table = JobPackageTable.__table__
wrapper_job_package_table: Table = WrapperJobPackageTable.__table__
