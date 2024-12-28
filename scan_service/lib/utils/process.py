
def parse_pid_relation(old_pid_dict):
    """
    用于分析pid之前的父子进程关系（包括孙进程）
    :param pid_list:
        {
            "<PID>": {
                "ppid": ""
                "child_pids": []
            }
        }
    :return:
        {
            "<PID>":
                {
                    "ppid": ""
                    "child_pids": []
                    ...
                }
        }
    """
    pid_dict = old_pid_dict.copy()
    ret = {}
    pid_list = []

    for pid in pid_dict:
        pid_list.append(pid)

    # 分析这些pid的关系，如果多个pid没有关系，表明由该可执行文件启动了多个实例
    for pid in pid_dict:
        if pid_dict[pid]["ppid"] not in pid_list:
            ret[pid] = pid_dict[pid]
            ret[pid]["child_pids"] = []

    for pid in pid_dict:
        if not ret.get(pid):
            try:
                ret[pid_dict[pid]["ppid"]]["child_pids"].append(pid)
            except KeyError:
                for t_pid in ret:
                    if pid_dict[pid]["ppid"] in ret[t_pid]["child_pids"]:
                        ret[t_pid]["child_pids"].append(pid)

    return ret