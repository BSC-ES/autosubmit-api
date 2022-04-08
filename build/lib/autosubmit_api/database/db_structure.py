import os
import textwrap
import traceback
import sqlite3

def get_structure(expid, structures_path):
    """
    Creates file of database and table of experiment structure if it does not exist. 
    Returns current structure as a Dictionary Job Name -> Children's Names

    :return: Map from job to children
    :rtype: Dictionary Key: String, Value: List(of String)
    """
    try:
        #pkl_path = os.path.join(exp_path, expid, "pkl")
        if os.path.exists(structures_path):
            db_structure_path = os.path.join(
                structures_path, "structure_" + expid + ".db")
            # Create file
            os.umask(0)
            if not os.path.exists(db_structure_path):
                os.open(db_structure_path, os.O_WRONLY | os.O_CREAT, 0o777)
                # open(db_structure_path, "w")
            # print(db_structure_path)
            conn = create_connection(db_structure_path)
            create_table_query = textwrap.dedent(
                '''CREATE TABLE
            IF NOT EXISTS experiment_structure (
            e_from text NOT NULL,
            e_to text NOT NULL,
            UNIQUE(e_from,e_to)
            );''')
            create_table(conn, create_table_query)
            current_table = _get_exp_structure(db_structure_path)
            # print("Current table: ")
            # print(current_table)
            current_table_structure = dict()
            for item in current_table:
                _from, _to = item
                current_table_structure.setdefault(_from, []).append(_to)
                current_table_structure.setdefault(_to, [])
                # if _from not in current_table_structure.keys():
                #     current_table_structure[_from] = list()
                # if _to not in current_table_structure.keys():
                #     current_table_structure[_to] = list()
                # current_table_structure[_from].append(_to)
            if (len(current_table_structure.keys()) > 0):
                # print("Return structure")
                return current_table_structure
            else:
                return None
        else:
            # pkl folder not found
            raise Exception("structures folder not found " +
                            str(structures_path))
    except Exception as exp:
        print(traceback.format_exc())


def create_connection(db_file):
    """ 
    Create a database connection to the SQLite database specified by db_file.  
    :param db_file: database file name  
    :return: Connection object or None
    """
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except:
        return None


def create_table(conn, create_table_sql):
    """ create a table from the create_table_sql statement
    :param conn: Connection object
    :param create_table_sql: a CREATE TABLE statement
    :return:
    """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Exception as e:
        print(e)


def _get_exp_structure(path):
    """
    Get all registers from experiment_status.\n
    :return: row content: exp_id, name, status, seconds_diff  
    :rtype: 4-tuple (int, str, str, int)
    """
    try:
        conn = create_connection(path)
        conn.text_factory = str
        cur = conn.cursor()
        cur.execute(
            "SELECT e_from, e_to FROM experiment_structure")
        rows = cur.fetchall()
        return rows
    except Exception as exp:
        print(traceback.format_exc())
        return dict()


def save_structure(graph, exp_id, structures_path):
    """
    Saves structure if path is valid
    """
    #pkl_path = os.path.join(exp_path, exp_id, "pkl")
    if os.path.exists(structures_path):
        db_structure_path = os.path.join(
            structures_path, "structure_" + exp_id + ".db")
        # with open(db_structure_path, "w"):
        conn = create_connection(db_structure_path)
        deleted = _delete_table_content(conn)
        if deleted == True:
            nodes_edges = {u for u, v in graph.edges()}
            nodes_edges.update({v for u, v in graph.edges()})
            independent_nodes = {
                u for u in graph.nodes() if u not in nodes_edges}
            data = {(u, v) for u, v in graph.edges()}
            data.update({(u, u) for u in independent_nodes})
            # save
            _create_edge(conn, data)
            #print("Created edge " + str(u) + str(v))
            conn.commit()
    else:
        # pkl folder not found
        raise Exception("pkl folder not found " + str(structures_path))


def _create_edge(conn, data):
    """
    Create edge
    """
    try:
        sql = ''' INSERT INTO experiment_structure(e_from, e_to) VALUES(?,?) '''
        cur = conn.cursor()
        cur.executemany(sql, data)
        # return cur.lastrowid
    except sqlite3.Error as e:
        print("Error on Insert : " + str(type(e).__name__))


def _delete_table_content(conn):
    """
    Deletes table content
    """
    try:
        sql = ''' DELETE FROM experiment_structure '''
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        return True
    except Exception as exp:
        # print(traceback.format_exc())
        print("Error on Delete _delete_table_content: {}".format(str(exp)))
        return False
