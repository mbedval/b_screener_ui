from contextlib import contextmanager
from psycopg import connect
from psycopg.rows import dict_row
@contextmanager
def get_connection(dsn: str):
    with connect(dsn, row_factory=dict_row) as connection:
        yield connection
