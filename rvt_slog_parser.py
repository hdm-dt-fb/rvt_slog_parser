"""
Basic python helper to retrieve information from Revit sync log (slog).

Usage:
    rvt_slog_parser.py      <slog_path> <project_code> [options]

Arguments:
    slog_path               file path to the slog to parse
    project_code            unique project code consisting of 'projectnumber_projectModelPart'
                            like 456_11 , 416_T99 or 377_S

Options:
    -h, --help              Show this help screen.
    --db_store              stores parsed data in db
    --db_path=<db>          directory path to store the db

"""

from docopt import docopt
import re
import os.path as op
import colorful
from attr import attrs, attrib, Factory
from datetime import datetime
from collections import defaultdict
import rvt_slog_storage
import rvt_slog_bokeh

# TODO sync durations - get both load lines at once
# TODO get request matrix members


@attrs
class SlogUser(object):
    user_name = attrib()
    ses_cls = attrib(default=Factory(dict))


@attrs
class RvtSession(object):
    session_id = attrib()
    start = attrib(default=Factory(str))
    end = attrib(default=Factory(str))
    duration = attrib(default=Factory(str))
    build = attrib(default=Factory(str))
    hosts = attrib(default=Factory(str))
    central = attrib(default=Factory(str))
    syncs = attrib(default=Factory(list))
    links = attrib(default=Factory(list))


@attrs
class RvtSync(object):
    sync_id = attrib()
    sync_start = attrib(default=Factory(str))
    sync_end = attrib(default=Factory(str))
    sync_duration = attrib(default=Factory(str))


@attrs
class RvtLink(object):
    link_id = attrib()
    link_open_start = attrib(default=Factory(str))
    link_open_end = attrib(default=Factory(str))
    link_open_duration = attrib(default=Factory(str))
    link_path = attrib(default=Factory(str))


def serializer(users_classes):
    user_dict = defaultdict(list)
    for user_name in users_classes.keys():
        # user_dict[user_name].update([])
        for ses_id in users_classes[user_name].ses_cls:
            # use user class as base
            ses_dict = users_classes[user_name].ses_cls[ses_id].__dict__
            for ses_att_key, ses_att_val in users_classes[user_name].ses_cls[ses_id].__dict__.items():
                # serialize link objects
                if ses_att_key == "links":
                    ses_links = []
                    for link_obj in ses_att_val:
                        ses_links.append(dict(link_obj.__dict__.items()))
                    ses_dict["links"] = ses_links
                # serialize sync objects
                elif ses_att_key == "syncs":
                    ses_syncs = []
                    for link_obj in ses_att_val:
                        ses_syncs.append(dict(link_obj.__dict__.items()))
                    ses_dict["syncs"] = ses_syncs
            user_dict[user_name].append(ses_dict)
    return user_dict


def get_user_sessions(slog_str):
    users = {}
    all_users = set()
    session_users = {}
    re_session_id = re.compile(r' >Session.+\n')
    re_user = re.compile(r' user=.+')
    re_build = re.compile(r' build=.+')
    re_host = re.compile(r' host=.+')
    re_central = re.compile(r' central=.+')
    re_time_stamp = re.compile(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')
    re_session_end = re.compile(r'\$.+\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{3} <Session')
    re_stc_start = re.compile(r'\$.+\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{3} >STC\n')
    re_stc_end = re.compile(r'\$.+\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{3} <STC\n')
    re_stc_block = re.compile(r'(\$.{8}) ([\d\:\-\s]+?)\..+ >STC\s+.+? ([\d\:\-\s]+?)\..{3} <STC\n')
    re_link_load = re.compile(r'(\$.{8}) ([\d\:\-\.\s]+?) \>OpenLink\s+\"([^\"]+?)\".+? ([\d\:\-\.\s]+?) <OpenLink',
                              re.DOTALL)
    re_header = re.compile(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{3} >Session.+\n'
                           r' user=".+"\n'
                           r' build=".+"\n'
                           r' journal=".+"\n'
                           r' host=.+ ".+"\n'
                           r' server=.+ ".+"\n'
                           r' central=".+"\n'
                           )

    headers = re_header.findall(slog_str)

    for header in headers:
        start = re_time_stamp.findall(header)[0]
        session_id = re_session_id.findall(header)[0].split(" ")[-1].strip("\n")
        user_name = re_user.findall(header)[0].split('"')[1]
        host = re_host.findall(header)[0].split('"')[1].split(".")[0]
        build = re_build.findall(header)[0].split('"')[1]
        central = re_central.findall(header)[0].split('"')[1]
        session_users[session_id] = user_name
        # print(user_name, session_id, len(header))

        if user_name not in all_users:
            users[user_name] = SlogUser(user_name)

        users[user_name].ses_cls[session_id] = RvtSession(session_id)
        users[user_name].ses_cls[session_id].start = start
        users[user_name].ses_cls[session_id].hosts = host
        users[user_name].ses_cls[session_id].build = build
        users[user_name].ses_cls[session_id].central = central
        all_users.add(user_name)

    # print(all_users)
    # print(session_users)

    session_ends = re_session_end.findall(slog_str)
    for session_end in session_ends:
        # print(session_end)
        session_id = session_end.split(" ")[0]
        user_name = session_users[session_id]
        start = users[user_name].ses_cls[session_id].start
        end = re_time_stamp.findall(session_end)[0]
        start_time = datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
        end_time = datetime.strptime(end, "%Y-%m-%d %H:%M:%S")
        duration = end_time - start_time
        if not duration:
            duration = ""
        else:
            duration = duration.__str__()
        users[user_name].ses_cls[session_id].end = end
        users[user_name].ses_cls[session_id].duration = duration

    sync_starts = re_stc_start.findall(slog_str)
    for i, sync_start in enumerate(sync_starts):
        session_id = sync_start.split(" ")[0]
        user_name = session_users[session_id]
        start = re_time_stamp.findall(sync_start)[0]
        sync = RvtSync(str(i).zfill(2) + session_id)
        sync.sync_start = start
        users[user_name].ses_cls[session_id].syncs.append(sync)
        # print("{} sync_start: {}".format(session_id, start))
    # print(i)

    sync_ends = re_stc_end.findall(slog_str)
    for i, sync_end in enumerate(sync_ends):
        session_id = sync_end.split(" ")[0]
        user_name = session_users[session_id]
        end = re_time_stamp.findall(sync_end)[0]
        # users[user_name].ses_cls[session_id].syncs[i].sync_end = end
        # print("{} sync_end: {}".format(session_id, end))
    # print(i)

    # print(session_users)

    link_loads = re_link_load.findall(slog_str)
    # print(link_loads)
    for i, link_load in enumerate(link_loads):
        # print(link_load)
        session_id = link_load[0]
        user_name = session_users[session_id]
        start = link_load[1][:-4]
        end = link_load[3][:-4]
        start_time = datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
        end_time = datetime.strptime(end, "%Y-%m-%d %H:%M:%S")
        duration = end_time - start_time
        link_path = link_load[2]
        link = RvtLink(str(i).zfill(4) + session_id)
        link.link_open_start = start
        link.link_open_end = end
        link.link_open_duration = duration.__str__()
        link.link_path = link_path
        users[user_name].ses_cls[session_id].links.append(link)

    return users


args = docopt(__doc__)
slog_path = args["<slog_path>"]
project_code = args["<project_code>"]
db_store = args["--db_store"]
db_path = args["--db_path"]
slog_users = None
df_dict = {"user": [], "start": [], "end": []}

print(colorful.bold_cyan("+parsing: {}".format(op.basename(slog_path))))
print(" at path: {}".format(op.abspath(slog_path)))

if not op.exists(slog_path):
    print(colorful.bold_red("+slog not found at specified path!"))
else:
    with open(slog_path, 'r', encoding="utf-16le") as slog:
        slog_txt = slog.read()

    slog_users = get_user_sessions(slog_txt)

    print(colorful.bold_orange("-found {} users:".format(len(slog_users))))
    for user in slog_users:
        print(colorful.bold_green("-{}:".format(user)))
        for session in slog_users[user].ses_cls:
            ses_id = colorful.bold_orange(session)
            start = slog_users[user].ses_cls[session].start
            end = slog_users[user].ses_cls[session].end
            host = slog_users[user].ses_cls[session].hosts
            build = slog_users[user].ses_cls[session].build
            duration = slog_users[user].ses_cls[session].duration
            df_dict["user"].append(user)
            df_dict["start"].append(start)
            df_dict["end"].append(end)
            print("     session {}\n"
                  "     on {} {} | start {} | duration {}".format(ses_id, host, build, start, duration))

            for link in slog_users[user].ses_cls[session].links:
                print("          link open start {} | duration {}".format(link.link_open_start,
                                                                          link.link_open_duration))
                print("             {}".format(link.link_path))

            for sync in slog_users[user].ses_cls[session].syncs:
                print(colorful.brown("          sync start {}".format(sync.sync_start)))

    if slog_users and db_store:
        print(colorful.bold_cyan("-db access."))
        user_dict = serializer(slog_users)
        db = rvt_slog_storage.write_db(project_code, db_path, user_dict)
        bokeh_graph = rvt_slog_bokeh.build_graph_html(rvt_slog_bokeh.dict_to_df(df_dict), project_code)

    print(colorful.bold_cyan("+finished parsing {}".format(slog_path)))
