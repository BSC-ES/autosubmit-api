from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Engine, Table, create_engine
from sqlalchemy.schema import CreateTable

from autosubmit_api.common.utils import LOCAL_TZ
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database import tables
from autosubmit_api.database.common import create_as_api_db_engine, execute_upsert


class UserPreferencesModel(BaseModel):
    user_id: str
    preferred_username: str
    created: str
    modified: str


class UserPreferencesRepository(ABC):
    @abstractmethod
    def get_by_user_id(self, user_id: str) -> Optional[UserPreferencesModel]:
        """
        Get user preferences by user_id

        :param user_id: User ID
        :return: User preferences or None if not found
        """

    @abstractmethod
    def upsert_preferred_username(
        self, user_id: str, preferred_username: str
    ) -> UserPreferencesModel:
        """
        Create or update preferred username for a user

        :param user_id: User ID
        :param preferred_username: Preferred Linux username
        :return: Updated user preferences
        """


class UserPreferencesSQLRepository(UserPreferencesRepository):
    def __init__(self, engine: Engine, table: Table):
        self.engine = engine
        self.table = table

        with self.engine.connect() as conn:
            conn.execute(CreateTable(self.table, if_not_exists=True))
            conn.commit()

    def get_by_user_id(self, user_id: str):
        with self.engine.connect() as conn:
            statement = self.table.select().where(self.table.c.user_id == user_id)
            result = conn.execute(statement).first()
        if result is None:
            return None
        return UserPreferencesModel(
            user_id=result.user_id,
            preferred_username=result.preferred_username,
            created=result.created,
            modified=result.modified,
        )

    def upsert_preferred_username(self, user_id: str, preferred_username: str):
        timestamp = datetime.now(tz=LOCAL_TZ).isoformat(sep="-", timespec="seconds")
        with self.engine.connect() as conn:
            with conn.begin():
                try:
                    execute_upsert(
                        conn,
                        self.table,
                        {
                            "user_id": user_id,
                            "preferred_username": preferred_username,
                            "created": timestamp,
                            "modified": timestamp,
                        },
                        index_elements=["user_id"],
                        set_={
                            "preferred_username": preferred_username,
                            "modified": timestamp,
                        },
                    )

                    # Fetch and return the updated record (before transaction ends)
                    select_stmnt = self.table.select().where(
                        self.table.c.user_id == user_id
                    )
                    result = conn.execute(select_stmnt).first()
                    conn.commit()
                except Exception as exc:
                    conn.rollback()
                    raise exc

            # Transaction is committed here automatically by conn.begin() context manager
            return UserPreferencesModel(
                user_id=result.user_id,
                preferred_username=result.preferred_username,
                created=result.created,
                modified=result.modified,
            )


def create_user_preferences_repository() -> UserPreferencesRepository:
    if APIBasicConfig.DATABASE_BACKEND == "postgres":
        # PostgreSQL
        _engine = create_engine(APIBasicConfig.DATABASE_CONN_URL)
    else:
        _engine = create_as_api_db_engine()
    _table = tables.UserPreferencesTable
    return UserPreferencesSQLRepository(_engine, _table)
