from sqlite3 import Cursor
from typing import List, Any


def get_headers_sqlite(cursor: Cursor):
    """
    Get headers in position of a sqlite query cursor
    """
    return list(map(lambda attr: attr[0], cursor.description))


def map_row_result_to_dict_sqlite(row: List[Any], headers: List[str]):
    """
    Return a dict of the rows as values with keys as their respective header.
    """
    return {header: row[i] for i, header in enumerate(headers)}
