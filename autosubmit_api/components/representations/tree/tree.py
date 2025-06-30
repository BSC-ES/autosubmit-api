#!/usr/bin/env python
from autosubmit_api.builders.experiment_history_builder import ExperimentHistoryBuilder, ExperimentHistoryDirector
from autosubmit_api.components.jobs import utils as JUtils
from autosubmit_api.performance import utils as PUtils
from autosubmit_api.components.jobs.joblist_loader import JobListLoader
from autosubmit_api.components.jobs.job_factory import Job
from autosubmit_api.common.utils import Status, get_average_total_time, get_current_timestamp
from collections import deque, OrderedDict
from typing import List, Dict, Tuple, Set, Any
from operator import is_not
from functools import partial

DEFAULT_MEMBER = "DEFAULT"

class TreeRepresentation(object):
  def __init__(self, expid: str, job_list_loader: JobListLoader):
    self.expid: str = expid
    self.joblist_loader: JobListLoader = job_list_loader
    self._date_member_distribution: Dict[Tuple[str, str], List[Job]] = {}
    self._no_date_no_member_jobs: List[Job] = []
    self._normal_status: Set[Status] = {Status.COMPLETED, Status.WAITING, Status.READY, Status.SUSPENDED}
    self.result_tree: List = []
    self.result_header: Dict = {}
    self.average_post_time: float = 0.0
    self.nodes: List[Dict] = []
    self._distributed_dates: OrderedDict[str, None] = OrderedDict()
    self._distributed_members: OrderedDict[str, None] = OrderedDict()


  def perform_calculations(self):
    self._distribute_into_date_member_groups()
    self._generate_date_member_tree_folders()
    self._generate_no_date_no_member_tree_folder()
    self._generate_package_tree_folders()
    self._complement_result_header()
    self._calculate_average_post_time()
    self._generate_node_data()

  def get_tree_structure(self) -> Dict[str, Any]:
    return {
      "tree": self.result_tree,
      "jobs": self.nodes,
      "total": len(self.nodes),
      "reference": self.result_header,
      "error": False,
      "error_message": "",
      "pkl_timestamp": get_current_timestamp()
    }

  def _distribute_into_date_member_groups(self):
    for job in self.joblist_loader.jobs:
      if job.date is not None and job.member is not None:
        self._date_member_distribution.setdefault((job.date, job.member), []).append(job)
        self._distributed_dates[job.date] = None
        self._distributed_members[job.member] = None
      elif job.date is not None and job.member is None:
        # parents_members = {self.joblist_loader.job_dictionary[parent_name].member for parent_name in job.parents_names}
        # children_members = {self.joblist_loader.job_dictionary[children_name].member for children_name in job.children_names}
        # intersection_member_parent = self.joblist_loader.members & parents_members
        # intersection_member_children = self.joblist_loader.members & children_members
        self._date_member_distribution.setdefault((job.date, DEFAULT_MEMBER), []).append(job)
        self._distributed_dates[job.date] = None
        self._distributed_members[DEFAULT_MEMBER] = None
        # if len(intersection_member_parent) > 0 or len(intersection_member_children) > 0:
        #   member = intersection_member_parent.pop() if len(intersection_member_parent) > 0 else intersection_member_children.pop()
        #   self._date_member_distribution.setdefault((job.date, member), []).append(job)
        #   self._distributed_dates[job.date] = None
        #   self._distributed_members[member] = None
        # else:
        #   self._date_member_distribution.setdefault((job.date, DEFAULT_MEMBER), []).append(job)
        #   self._distributed_dates[job.date] = None
        #   self._distributed_members[DEFAULT_MEMBER] = None
      else:
        self._no_date_no_member_jobs.append(job)

  def _generate_date_member_tree_folders(self):
    for date in self._distributed_dates:
      folders_in_date = list()
      formatted_date = self.joblist_loader.dates_formatted_dict.get(date, None)
      all_suspended = True
      all_waiting = True
      all_completed = True
      total_jobs_startdate = 0
      for member in self._distributed_members:
        status_counters = {
          Status.COMPLETED: 0,
          Status.RUNNING: 0,
          Status.QUEUING: 0,
          Status.FAILED: 0,
          Status.HELD: 0 }
        jobs_in_date_member = self._date_member_distribution.get((date, member), [])
        sections = {job.section for job in jobs_in_date_member}
        section_to_dm_jobs_dict = {section: [job for job in jobs_in_date_member if job.section == section] for section in sections}
        sections_folder_open = set()
        jobs_in_section = OrderedDict()
        jobs_and_folders_in_member = deque()
        for job in jobs_in_date_member:
          all_suspended = all_suspended and job.status is Status.SUSPENDED
          all_waiting = all_waiting and job.status is Status.WAITING
          all_completed = all_completed and job.status is Status.COMPLETED
          if job.status in status_counters:
            status_counters[job.status] += 1
          if len(section_to_dm_jobs_dict[job.section]) > 1:
            if job.status in self._normal_status:
              jobs_in_section.setdefault(job.section, deque()).append(job.leaf)
            else:
              jobs_in_section.setdefault(job.section, deque()).appendleft(job.leaf)
              sections_folder_open.add(job.section)
          else:
            if job.status in self._normal_status:
              jobs_and_folders_in_member.append(job.leaf)
            else:
              jobs_and_folders_in_member.appendleft(job.leaf)
          job.tree_parent.append("{0}_{1}_{2}".format(self.expid, self.joblist_loader.dates_formatted_dict.get(date, None), member))

        for section in jobs_in_section:
          jobs_and_folders_in_member.append({
            'title': section,
            'folder': True,
            'refKey': "{0}_{1}_{2}_{3}".format(self.expid, formatted_date, str(member), str(section)),
            'data': 'Empty',
            'expanded': True if section in sections_folder_open else False,
            'children': list(jobs_in_section.get(section, []))
          })

        if len(jobs_in_date_member) > 0: # If there is something inside the date-member group, we create it.
          total_jobs_startdate += len(jobs_in_date_member)
          ref_key = "{0}_{1}_{2}".format(self.expid, formatted_date, member)
          folders_in_date.append({
            "title": JUtils.get_folder_date_member_title(self.expid,
                    formatted_date,
                    member,
                    len(jobs_in_date_member),
                    status_counters),
            "folder": True,
            "refKey": ref_key,
            "data": "Empty",
            "expanded": False,
            "children": list(jobs_and_folders_in_member)
          })
          self.result_header[ref_key] = ({
            "completed": status_counters[Status.COMPLETED],
            "running": status_counters[Status.RUNNING],
            "queuing": status_counters[Status.QUEUING],
            "failed": status_counters[Status.FAILED],
            "held": status_counters[Status.HELD],
            "total": len(jobs_in_date_member)
          })

      # for the folders representing those start dates whose members are all in STATE WAITING, COMPLETED or SUSPENDED, we display
      # these will be displayed collapsed, if there is any job with status fail, this will be displayed expanded
      # todo: add threshold variable

      if len(folders_in_date) > 0: # If there is something inside the date folder, we create it.
        if all_suspended or all_waiting or all_completed:
           date_tag = JUtils.get_date_folder_tag("WAITING", total_jobs_startdate) if all_waiting else JUtils.get_date_folder_tag("SUSPENDED", total_jobs_startdate)
           if all_completed:
             date_tag = JUtils.get_date_folder_tag("COMPLETED", total_jobs_startdate)
           date_folder_title = "{0}_{1} {2}".format(
             self.expid,
             formatted_date,
             date_tag
           )
        else:
           date_folder_title = "{0}_{1}".format(self.expid, formatted_date)

        self.result_tree.append({
          "title": date_folder_title,
          "folder": True,
          "refKey": date_folder_title,
          "data": "Empty",
          "expanded": False if len(self._distributed_dates) > 5 and (all_waiting or all_suspended or all_completed) else True,
          "children": list(folders_in_date)
        })

  def _generate_no_date_no_member_tree_folder(self):
    """ Generates folder for job with no date and no member """
    if len(self._no_date_no_member_jobs) > 0:
      self.result_tree.append({
        "title": "Keys",
        "folder": True,
        "refKey": "Keys",
        "data": "Empty",
        "expanded": True,
        "children": [job.leaf for job in self._no_date_no_member_jobs]
      })

  def _generate_package_tree_folders(self):
    """ Package folders (wrappers) as roots in the tree. """
    # sort the list before iterating
    result_exp_wrappers = []
    sorted_wrappers = sorted(self.joblist_loader.package_names)
    for package_name in sorted_wrappers:
      jobs_in_package = sorted( list(filter(partial(is_not, None), self.joblist_loader.get_all_jobs_in_package(package_name))), key=lambda x: x.chunk if x.chunk is not None else 0)
      simple_title = "Wrapper: {0}".format(package_name)
      total_count = len(jobs_in_package)
      status_counters = {
          Status.COMPLETED: 0,
          Status.RUNNING: 0,
          Status.QUEUING: 0,
          Status.FAILED: 0,
          Status.HELD: 0 }

      if total_count > 0:
        for job in jobs_in_package:
          if job.status in status_counters:
            status_counters[job.status] += 1
        result_exp_wrappers.append({
          "title": JUtils.get_folder_package_title(package_name, total_count, status_counters),
          "folder": True,
          "refKey": simple_title,
          "data": {'completed': status_counters[Status.COMPLETED],
                    'failed': status_counters[Status.FAILED],
                    'running': status_counters[Status.RUNNING],
                    'queuing': status_counters[Status.QUEUING],
                    'held': status_counters[Status.HELD],
                    'total': total_count },
          "expanded": False,
          "children": [job.leaf for job in jobs_in_package]
        })

        self.result_header[simple_title] = ({
          "completed" : status_counters[Status.COMPLETED],
          "running": status_counters[Status.RUNNING],
          "queuing": status_counters[Status.QUEUING],
          "failed": status_counters[Status.FAILED],
          "held": status_counters[Status.HELD],
          "total": total_count
        })

    # add root folder to enclose all the wrappers
    # If there is something inside the date-member group, we create it.
    if len(sorted_wrappers) > 0:
      self.result_tree.append({
        "title": "Wrappers",
        "folder": True,
        "refKey": "Wrappers_{0}".format(self.expid),
        "data": "Empty",
        "expanded": False,
        "children": list(result_exp_wrappers)
      })





  def _complement_result_header(self):
    self.result_header["completed_tag"] = JUtils.completed_tag_with_anchors
    self.result_header["running_tag"] = JUtils.running_tag_with_anchors
    self.result_header["queuing_tag"] = JUtils.queuing_tag_with_anchors
    self.result_header["failed_tag"] = JUtils.failed_tag_with_anchors
    self.result_header["held_tag"] = JUtils.held_tag_with_anchors
    self.result_header["checkmark"] = JUtils.checkmark_tag
    self.result_header["packages"] = [package_name for package_name in self.joblist_loader.package_names]
    self.result_header["chunk_unit"] = self.joblist_loader.chunk_unit
    self.result_header["chunk_size"] = self.joblist_loader.chunk_size

  def _calculate_average_post_time(self):
    post_jobs = [job for job in self.joblist_loader.jobs if job.section == "POST" and job.status in {Status.COMPLETED}]
    self.average_post_time = get_average_total_time(post_jobs)

  def _generate_node_data(self):
    # Get last run data for each job
    try:
      experiment_history = ExperimentHistoryDirector(ExperimentHistoryBuilder(self.expid)).build_reader_experiment_history()
      last_jobs_run = experiment_history.get_all_jobs_last_run_dict()
    except Exception:
      last_jobs_run = {}
    
    for job in self.joblist_loader.jobs:
      # Get chunk size and unit
      chunk_size = self.joblist_loader.chunk_size
      chunk_unit = self.joblist_loader.chunk_unit
      last_run = last_jobs_run.get(job.name)
      if last_run and last_run.chunk_unit and last_run.chunk_size:
        chunk_unit, chunk_size = last_run.chunk_unit, last_run.chunk_size

      # Calculate dates
      ini_date, end_date = job.get_date_ini_end(chunk_size, chunk_unit)

      # Calculate performance metrics
      SYPD = PUtils.calculate_SYPD_perjob(chunk_unit, chunk_size, job.chunk, job.run_time, job.status)
      ASYPD = PUtils.calculate_ASYPD_perjob(chunk_unit, chunk_size, job.chunk, job.total_time, self.average_post_time, job.status)

      self.nodes.append({
        "id": job.name,
        "internal_id": job.name,
        "label": job.name,
        "status": job.status_text,
        "status_code": job.status,
        "platform_name": job.platform,
        "chunk": job.chunk,
        "chunk_size": chunk_size,
        "chunk_unit": chunk_unit,
        "member": job.member,
        "title" : job.tree_title,
        "date": ini_date,
        "date_plus": end_date,
        "SYPD": SYPD,
        "ASYPD": ASYPD,
        "minutes_queue": job.queue_time,
        "minutes": job.run_time,
        "submit": job.submit_datetime,
        "start": job.start_datetime,
        "finish": job.finish_datetime,
        "section": job.section,
        "queue": job.qos,
        "processors": job.ncpus,
        "wallclock": job.wallclock,
        "wrapper": job.package,
        "wrapper_code": job.package_code,
        "children": len(job.children_names),
        "children_list": list(job.children_names),
        "parents": len(job.parents_names),
        "parent_list": list(job.parents_names),
        "out": job.out_file_path,
        "err": job.err_file_path,
        "tree_parents": job.tree_parent,
        "custom_directives": None,
        "rm_id": job.rm_id,
        "status_color": job.status_color,
        "workflow_commit": job.workflow_commit,
      })