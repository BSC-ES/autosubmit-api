from typing import List, Optional, Tuple
import portalocker
import os
import traceback
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database.repositories.graph_draw import ExpGraphDrawDBRepository
from autosubmit_api.logger import logger
from autosubmit_api.monitor.monitor import Monitor


class ExperimentGraphDrawing:
    def __init__(self, expid):
        """
        Sets and validates graph drawing.
        :param expid: Name of experiment
        :type expid: str
        """
        APIBasicConfig.read()
        self.expid = expid
        self.folder_path = APIBasicConfig.LOCAL_ROOT_DIR
        self.graph_data_db = ExpGraphDrawDBRepository(expid)
        self.graph_data_db.create_table()
        self.lock_name = "calculation_in_progress.lock"
        self.current_position_dictionary = None
        self.current_jobs_set = set()
        self.coordinates = list()
        self.set_current_position()
        self.should_update = False
        self.locked = False
        self.test_locked()

    def test_locked(self):
        self.locked = True
        try:
            with portalocker.Lock(
                os.path.join(self.folder_path, self.lock_name), timeout=1
            ) as fh:
                self.locked = False
                fh.flush()
                os.fsync(fh.fileno())
        except portalocker.AlreadyLocked:
            logger.error("It is locked")
            self.locked = True
        except Exception:
            self.locked = True

    def get_validated_data(self, allJobs):
        """
        Validates if should update current graph drawing.
        :return: None if graph drawing should be updated, otherwise, it returns the position data.
        :rype: None or dict()
        """
        job_names = {job.name for job in allJobs}
        # Validating content
        difference = job_names - self.current_jobs_set
        if difference and len(difference) > 0:
            # Intersection found. Graph Drawing database needs to be updated
            self.should_update = True
            # Clear database
            return None
        return self.current_position_dictionary
        # return None if self.should_update == True else self.current_position_dictionary

    def calculate_drawing(
        self, allJobs, independent=False, num_chunks=48, job_dictionary=None
    ):
        """
        Called in a thread.
        :param allJobs: list of jobs (usually from job_list object)
        :type allJobs: list()
        :return: Last row Id
        :rtype: int
        """
        lock_name = (
            "calculation_{}_in_progress.lock".format(self.expid)
            if independent is True
            else self.lock_name
        )
        lock_path_file = os.path.join(self.folder_path, lock_name)
        try:
            with portalocker.Lock(lock_path_file, timeout=1) as fh:
                monitor = Monitor()
                graph = monitor.create_tree_list(
                    self.expid, allJobs, None, dict(), False, job_dictionary
                )
                if len(allJobs) > 1000:
                    # Logic: Start with 48 as acceptable number of chunks for Gmaxiter = 100
                    # Minimum Gmaxiter will be 10
                    maxiter = max(10, 148 - num_chunks)
                    # print("Experiment {} num_chunk {} maxiter {}".format(
                    #     self.expid, num_chunks, maxiter))
                    result = graph.create(
                        [
                            "dot",
                            "-Gnslimit=2",
                            "-Gnslimit1=2",
                            "-Gmaxiter={}".format(maxiter),
                            "-Gsplines=none",
                            "-v",
                        ],
                        format="plain",
                    )
                else:
                    result = graph.create("dot", format="plain")
                for u in result.split(b"\n"):
                    splitList = u.split(b" ")
                    if len(splitList) > 1 and splitList[0].decode() == "node":
                        self.coordinates.append(
                            (
                                splitList[1].decode(),
                                int(float(splitList[2].decode()) * 90),
                                int(float(splitList[3].decode()) * -90),
                            )
                        )
                        # self.coordinates[splitList[1]] = (
                        #     int(float(splitList[2]) * 90), int(float(splitList[3]) * -90))
                self.insert_coordinates()
                fh.flush()
                os.fsync(fh.fileno())
            os.remove(lock_path_file)
            return self.get_validated_data(allJobs)
        except portalocker.AlreadyLocked:
            message = "Already calculating graph drawing."
            print(message)
            return None
        except Exception as exc:
            logger.error((traceback.format_exc()))
            os.remove(lock_path_file)
            logger.error(
                ("Exception while calculating coordinates {}".format(str(exc)))
            )
            return None

    def insert_coordinates(self) -> Optional[int]:
        """
        Prepares and inserts new coordinates.
        """
        try:
            # Start by clearing database
            self._clear_graph_database()
            result = None
            if self.coordinates and len(self.coordinates) > 0:
                result = self._insert_many_graph_coordinates(self.coordinates)
                return result
            return None
        except Exception as exc:
            logger.error((str(exc)))
            return None

    def set_current_position(self) -> None:
        """
        Sets all registers in the proper variables.
        current_position_dictionary: JobName -> (x, y)
        current_jobs_set: JobName
        """
        current_table = self._get_current_position()
        if current_table and len(current_table) > 0:
            self.current_position_dictionary = {
                row[1]: (row[2], row[3]) for row in current_table
            }
            self.current_jobs_set = set(self.current_position_dictionary.keys())

    def _get_current_position(self) -> List[Tuple[int, str, int, int]]:
        """
        Get all registers from experiment_graph_draw.\n
        :return: row content: id, job_name, x, y
        :rtype: 4-tuple (int, str, int, int)
        """
        try:
            result = self.graph_data_db.get_all()
            return [(item.id, item.job_name, item.x, item.y) for item in result]
        except Exception as exc:
            logger.error((traceback.format_exc()))
            logger.error((str(exc)))
            return None

    def _insert_many_graph_coordinates(
        self, values: List[Tuple[str, int, int]]
    ) -> Optional[int]:
        """
        Create many graph coordinates
        """
        try:
            _vals = [
                {"job_name": item[0], "x": item[1], "y": item[2]} for item in values
            ]
            logger.debug(_vals)
            return self.graph_data_db.insert_many(_vals)
        except Exception as exc:
            logger.error((traceback.format_exc()))
            logger.error("Error on Insert many graph drawing : {}".format(str(exc)))
            return None

    def _clear_graph_database(self):
        """
        Clear all content from graph drawing database
        """
        try:
            self.graph_data_db.delete_all()
        except Exception as exc:
            logger.error((traceback.format_exc()))
            logger.error(("Error on Database clear: {}".format(str(exc))))
            return False
        return True
