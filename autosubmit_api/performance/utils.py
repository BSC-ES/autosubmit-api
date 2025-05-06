#!/usr/bin/env pytthon
from collections import deque
from typing import Dict, List
from autosubmit_api.common.utils import JobSection, Status, datechunk_to_year

def calculate_SYPD_perjob(chunk_unit: str, chunk_size: int, job_chunk: int, run_time: int, status: int) -> float:
    """
    Generalization of SYPD at job level.
    """
    if status == Status.COMPLETED and job_chunk and job_chunk > 0:
        years_per_sim = datechunk_to_year(chunk_unit, chunk_size)
        if run_time > 0:
            return round((years_per_sim * 86400) / run_time, 2)
    return None


def calculate_PSYPD_perjob(chunk_unit: str, chunk_size: int, job_chunk: int, queue_run_time: int, average_post: float, status: int) -> float:
    """
    Generalization of PSYPD at job level
    """
    if status == Status.COMPLETED and job_chunk and job_chunk > 0:
        years_per_sim = datechunk_to_year(chunk_unit, chunk_size)
        # print("YPS in PSYPD calculation: {}".format(years_per_sim))
        divisor = queue_run_time + average_post
        if divisor > 0.0:
            return round((years_per_sim * 86400) / divisor, 2)
    return None

def find_critical_path(jobs_dict: Dict[str, dict]) -> List[dict]:
    """
    Generalized algorithm that receives a dictionary where each key is the job name
    and the value contains 'run_time', 'queue_time', 'children_names', and 'section'.
    Returns a list of dictionaries representing the jobs of the ideal critical path.
    """
    longest_path = {}
    predecessor = {}
    in_degree = {job_name: 0 for job_name in jobs_dict}
    
    for job_name, info in jobs_dict.items():
        base_time = max(info['run_time'], 0.001)
        longest_path[job_name] = base_time
        predecessor[job_name] = None
    
    for job_name, info in jobs_dict.items():
        for child_name in info['children_names']:
            if child_name in jobs_dict:
                in_degree[child_name] += 1
    
    queue = deque([name for name, deg in in_degree.items() if deg == 0])
    
    while queue:
        current_name = queue.popleft()
        current_info = jobs_dict[current_name]
        for child_name in current_info['children_names']:
            if child_name in jobs_dict:
                child_info = jobs_dict[child_name]
                child_run = max(child_info['run_time'], 0.001)
                new_path_length = longest_path[current_name] + child_run
                if new_path_length > longest_path[child_name]:
                    longest_path[child_name] = new_path_length
                    predecessor[child_name] = current_name
                in_degree[child_name] -= 1
                if in_degree[child_name] == 0:
                    queue.append(child_name)
    
    if not longest_path:
        return []
    end_job_name = max(longest_path, key=longest_path.get)
    path_names = []
    curr = end_job_name
    while curr:
        path_names.append(curr)
        curr = predecessor[curr]
    path_names.reverse()
    
    critical_path = [
        {
            "name": name,
            "run_time": jobs_dict[name]['run_time'],
            "queue_time": jobs_dict[name]['queue_time'],
            "section": jobs_dict[name]['section'],
        }
        for name in path_names
    ]
    return critical_path

def calculate_critical_path_phases(critical_path: List[dict]) -> Dict[str, float]:
    """
    Calculates the total run times for three phases in the critical path based on a list of dictionaries:
    1. Pre-SIM: Jobs executed before the first SIM job.
    2. SIM: All SIM jobs in the critical path.
    3. Post-SIM: Jobs executed after the last SIM job.

    Each dictionary has keys: 'name', 'run_time', 'queue_time', and 'section'.
    Returns a dictionary with the total run time and total run+queue time.
    """

    if not critical_path or critical_path == []:
        return {
            "pre_sim_run_time": 0.0,
            "sim_run_time": 0.0,
            "post_sim_run_time": 0.0,
            "total_run_time": 0.0,
            "total_run_queue_time": 0.0,
        }

    first_sim_index = -1
    last_sim_index = -1

    for i, job in enumerate(critical_path):
        if job.get("section") == JobSection.SIM:
            if first_sim_index == -1:
                first_sim_index = i
            last_sim_index = i

    pre_sim_run_time = 0.0
    sim_run_time = 0.0
    post_sim_run_time = 0.0
    total_run_queue_time = 0.0

    for i, job in enumerate(critical_path):
        run_time = job.get("run_time", 0)
        queue_time = job.get("queue_time", 0)
        total_run_queue_time += run_time + queue_time
        
        if first_sim_index == -1:
            post_sim_run_time += run_time
        elif i < first_sim_index:
            pre_sim_run_time += run_time
        elif i <= last_sim_index:
            sim_run_time += run_time
        else:
            post_sim_run_time += run_time

    total_run_time = pre_sim_run_time + sim_run_time + post_sim_run_time

    return {
        "pre_sim_run_time": pre_sim_run_time,
        "sim_run_time": sim_run_time,
        "post_sim_run_time": post_sim_run_time,
        "total_run_time": total_run_time,
        "total_run_queue_time": total_run_queue_time,
    }