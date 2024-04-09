from sqlalchemy import MetaData, Integer, String, Text, Table
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped


metadata_obj = MetaData()


class BaseTable(DeclarativeBase):
    metadata = metadata_obj


class ExperimentTable(BaseTable):
    __tablename__ = "experiment"

    id: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    autosubmit_version: Mapped[str] = mapped_column(String)


class DetailsTable(BaseTable):
    __tablename__ = "details"

    exp_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user: Mapped[str] = mapped_column(Text, nullable=False)
    created: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    branch: Mapped[str] = mapped_column(Text, nullable=False)
    hpc: Mapped[str] = mapped_column(Text, nullable=False)


class ExperimentStatusTable(BaseTable):
    __tablename__ = "experiment_status"

    exp_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    seconds_diff: Mapped[int] = mapped_column(Integer, nullable=False)
    modified: Mapped[str] = mapped_column(Text, nullable=False)


class GraphDataTable(BaseTable):
    __tablename__ = "experiment_graph_draw"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_name: Mapped[str] = mapped_column(Text, nullable=False)
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)


# MAIN_DB TABLES
experiment_table: Table = ExperimentTable.__table__
details_table: Table = DetailsTable.__table__

# AS_TIMES TABLES
experiment_status_table: Table = ExperimentStatusTable.__table__

# Graph Data TABLES
graph_data_table: Table = GraphDataTable.__table__
