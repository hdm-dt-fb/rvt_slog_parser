import os.path as op
from tinydb import TinyDB, Query
import colorful


def write_db(project_code, db_dir, dict_data):
    if db_dir:
        db_path = db_dir
    else:
        db_path = op.join(op.dirname(__file__), "db")
    db_full_path = op.join(db_path, project_code + "_db_.json")

    db = TinyDB(db_full_path)
    query = Query()

    for user in dict_data:
        for session in dict_data[user]:
            if not db.table(user).search(query.session_id == session["session_id"]):
                db.table(user).insert(session)
                print(colorful.green(" {} with session {} stored in db".format(user, session["session_id"])))
            else:
                print(colorful.orange(" {} with session {} already in db".format(user, session["session_id"])))
    return db
