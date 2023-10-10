#!/usr/bin/env python

# Copyright 2018 Earth Sciences Department, BSC-CNS

# This file is part of Autosubmit.

# Autosubmit is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Autosubmit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Autosubmit.  If not, see <http://www.gnu.org/licenses/>.

import textwrap


class WrapperDirector:
    """
    Construct an object using the Builder interface.
    """

    def __init__(self):
        self._builder = None

    def construct(self, builder):
        self._builder = builder

        header = self._builder.build_header()
        job_thread = self._builder.build_job_thread()

        main = self._builder.build_main()

        # change to WrapperScript object
        wrapper_script = header + job_thread + main
        wrapper_script = wrapper_script.replace("_NEWLINE_", '\\n')

        return wrapper_script


class WrapperBuilder(object):

    def __init__(self, **kwargs):
        self.header_directive = kwargs['header_directive']
        self.job_scripts = kwargs['jobs_scripts']
        self.num_procs = kwargs['num_processors']
        self.expid = kwargs['expid']
        self.jobs_resources = kwargs.get('jobs_resources', dict())
        self.allocated_nodes = kwargs.get('allocated_nodes', '')
        self.machinefiles_name = ''
        self.machinefiles_indent = 0
        self.exit_thread = ''

    def build_header(self):
        return textwrap.dedent(self.header_directive) + self.build_imports()

    def build_imports(self):
        pass

    def build_job_thread(self):
        pass

    # hybrids
    def build_joblist_thread(self, **kwargs):
        pass

    # horizontal and hybrids
    def build_nodes_list(self):
        pass

    def build_machinefiles(self):
        pass

    def get_machinefile_function(self):
        machinefile_function = ""
        if 'MACHINEFILES' in self.jobs_resources and self.jobs_resources['MACHINEFILES']:
            machinefile_function = self.jobs_resources['MACHINEFILES']

            self.machinefiles_name = "jobname"

            if machinefile_function == 'COMPONENTS':
                return self.build_machinefiles_components()
            else:
                return self.build_machinefiles_standard()
        return machinefile_function

    def build_machinefiles_standard(self):
        pass

    def build_machinefiles_components(self):
        pass

    def build_machinefiles_components_alternate(self):
        pass

    def build_sequential_threads_launcher(self, **kwargs):
        pass

    def build_parallel_threads_launcher(self, **kwargs):
        pass

    # all should override -> abstract!
    def build_main(self):
        pass

    def _indent(self, text, amount, ch=' '):
        padding = amount * ch
        return ''.join(padding + line for line in text.splitlines(True))


class PythonWrapperBuilder(WrapperBuilder):

    def build_imports(self):
        return textwrap.dedent("""
        import os
        import sys
        from threading import Thread
        from commands import getstatusoutput
        from datetime import datetime
        from math import ceil
        from collections import OrderedDict
        import copy

        # Defining scripts to be run
        scripts = {0}
        """).format(str(self.job_scripts), '\n'.ljust(13))

    def build_job_thread(self):
        return textwrap.dedent("""
        class JobThread(Thread):
            def __init__ (self, template, id_run):
                Thread.__init__(self)
                self.template = template
                self.id_run = id_run

            def run(self):
                jobname = self.template.replace('.cmd', '')
                os.system("echo $(date +%s) > "+jobname+"_STAT")
                out = str(self.template) + "." + str(self.id_run) + ".out"
                err = str(self.template) + "." + str(self.id_run) + ".err"
                command = "bash " + str(self.template) + " " + str(self.id_run) + " " + os.getcwd()
                (self.status) = getstatusoutput(command + " > " + out + " 2> " + err)
        """).format('\n'.ljust(13))

    # hybrids
    def build_joblist_thread(self):
        pass

    # horizontal and hybrids
    def build_nodes_list(self):
        return self.get_nodes() + self.build_cores_list()

    def get_nodes(self):
        return textwrap.dedent("""
        # Getting the list of allocated nodes
        {0}
        os.system("mkdir -p machinefiles")

        with open('node_list', 'r') as file:
             all_nodes = file.read()

        all_nodes = all_nodes.split("_NEWLINE_")
        """).format(self.allocated_nodes, '\n'.ljust(13))

    def build_cores_list(self):
        return textwrap.dedent("""
        total_cores = {0}
        jobs_resources = {1}

        processors_per_node = int(jobs_resources['PROCESSORS_PER_NODE'])

        idx = 0
        all_cores = []
        while total_cores > 0:
            if processors_per_node > 0:
                processors_per_node -= 1
                total_cores -= 1
                all_cores.append(all_nodes[idx])
            else:
                idx += 1
                processors_per_node = int(jobs_resources['PROCESSORS_PER_NODE'])

        processors_per_node = int(jobs_resources['PROCESSORS_PER_NODE'])
        """).format(self.num_procs, str(self.jobs_resources), '\n'.ljust(13))

    def build_machinefiles(self):
        machinefile_function = self.get_machinefile_function()
        if machinefile_function:
            return self.get_machinefile_function() + self._indent(self.write_machinefiles(), self.machinefiles_indent)
        return ""

    def build_machinefiles_standard(self):
        return textwrap.dedent("""
        machines = str()

        cores = int(jobs_resources[section]['PROCESSORS'])
        tasks = int(jobs_resources[section]['TASKS'])
        nodes = int(ceil(int(cores)/float(tasks)))
        if tasks < processors_per_node:
            cores = tasks
       
        job_cores = cores
        while nodes > 0:
            while cores > 0:
                if len(all_cores) > 0:
                    node = all_cores.pop(0)
                    if node:
                        machines += node +"_NEWLINE_"
                        cores -= 1
            for rest in range(processors_per_node-tasks):
                if len(all_cores) > 0:
                    all_cores.pop(0)
            nodes -= 1
            if tasks < processors_per_node:
                cores = job_cores
        """).format('\n'.ljust(13))

    def _create_components_dict(self):
        return textwrap.dedent("""
        xio_procs = int(jobs_resources[section]['COMPONENTS']['XIO_NUMPROC'])
        rnf_procs = int(jobs_resources[section]['COMPONENTS']['RNF_NUMPROC'])
        ifs_procs = int(jobs_resources[section]['COMPONENTS']['IFS_NUMPROC'])
        nem_procs = int(jobs_resources[section]['COMPONENTS']['NEM_NUMPROC'])
        
        components = OrderedDict([
            ('XIO', xio_procs),
            ('RNF', rnf_procs),
            ('IFS', ifs_procs),
            ('NEM', nem_procs)
        ])
        
        jobs_resources[section]['COMPONENTS'] = components
        """).format('\n'.ljust(13))

    def build_machinefiles_components(self):
        return textwrap.dedent("""
        {0}
        
        machines = str()
        for component, cores in jobs_resources[section]['COMPONENTS'].items():        
            while cores > 0:
                if len(all_cores) > 0:
                    node = all_cores.pop(0)
                    if node:
                        machines += node +"_NEWLINE_"
                        cores -= 1
        """).format(self._create_components_dict(), '\n'.ljust(13))

    def write_machinefiles(self):
        return textwrap.dedent("""
        machines = "_NEWLINE_".join([s for s in machines.split("_NEWLINE_") if s])
        with open("machinefiles/machinefile_"+{0}, "w") as machinefile:
            machinefile.write(machines)
        """).format(self.machinefiles_name, '\n'.ljust(13))

    def build_sequential_threads_launcher(self, jobs_list, thread, footer=True):
        sequential_threads_launcher = textwrap.dedent("""
        for i in range(len({0})):
            current = {1}
            current.start()
            current.join()
        """).format(jobs_list, thread, '\n'.ljust(13))

        if footer:
            sequential_threads_launcher += self._indent(textwrap.dedent("""
            completed_filename = {0}[i].replace('.cmd', '_COMPLETED')
            completed_path = os.path.join(os.getcwd(), completed_filename)
            if os.path.exists(completed_path):
                print datetime.now(), "The job ", current.template," has been COMPLETED"
            else:
                print datetime.now(), "The job ", current.template," has FAILED"
                {1}
            """).format(jobs_list, self.exit_thread, '\n'.ljust(13)), 4)

        return sequential_threads_launcher

    def build_parallel_threads_launcher(self, jobs_list, thread, footer=True):
        parallel_threads_launcher = textwrap.dedent("""
        pid_list = []

        for i in range(len({0})):
            if type({0}[i]) != list:
                job = {0}[i]
                jobname = job.replace(".cmd", '')
                section = jobname.split('_')[-1]

            {2}

            current = {1}({0}[i], i)
            pid_list.append(current)
            current.start()

        # Waiting until all scripts finish
        for i in range(len(pid_list)):
            pid = pid_list[i]
            pid.join()
        """).format(jobs_list, thread, self._indent(self.build_machinefiles(), 8), '\n'.ljust(13))

        if footer:
            parallel_threads_launcher += self._indent(textwrap.dedent("""
            completed_filename = {0}[i].replace('.cmd', '_COMPLETED')
            completed_path = os.path.join(os.getcwd(), completed_filename)
            if os.path.exists(completed_path):
                print datetime.now(), "The job ", pid.template," has been COMPLETED"
            else:
                print datetime.now(), "The job ", pid.template," has FAILED"
                {1}
            """).format(jobs_list, self.exit_thread, '\n'.ljust(13)), 4)

        return parallel_threads_launcher

    # all should override -> abstract!
    def build_main(self):
        pass

    def dependency_directive(self):
        pass

    def queue_directive(self):
        pass

    def _indent(self, text, amount, ch=' '):
        padding = amount * ch
        return ''.join(padding + line for line in text.splitlines(True))


class PythonVerticalWrapperBuilder(PythonWrapperBuilder):

    def build_main(self):
        self.exit_thread = "os._exit(1)"
        return self.build_sequential_threads_launcher("scripts", "JobThread(scripts[i], i)")


class PythonHorizontalWrapperBuilder(PythonWrapperBuilder):

    def build_main(self):
        nodelist = self.build_nodes_list()
        threads_launcher = self.build_parallel_threads_launcher("scripts", "JobThread")
        return nodelist + threads_launcher


class PythonVerticalHorizontalWrapperBuilder(PythonWrapperBuilder):

    def build_joblist_thread(self):
        return textwrap.dedent("""
        class JobListThread(Thread):
            def __init__ (self, jobs_list, id_run):
                Thread.__init__(self)
                self.jobs_list = jobs_list
                self.id_run = id_run

            def run(self):
                {0}
        """).format(
            self._indent(self.build_sequential_threads_launcher("self.jobs_list", "JobThread(self.jobs_list[i], i)"),
                         8), '\n'.ljust(13))

    def build_main(self):
        self.exit_thread = "sys.exit()"
        joblist_thread = self.build_joblist_thread()
        nodes_list = self.build_nodes_list()
        threads_launcher = self.build_parallel_threads_launcher("scripts", "JobListThread", footer=False)
        return joblist_thread + nodes_list + threads_launcher


class PythonHorizontalVerticalWrapperBuilder(PythonWrapperBuilder):

    def build_joblist_thread(self):
        return textwrap.dedent("""
        class JobListThread(Thread):
            def __init__ (self, jobs_list, id_run, all_cores):
                Thread.__init__(self)
                self.jobs_list = jobs_list
                self.id_run = id_run
                self.all_cores = all_cores

            def run(self):
                all_cores = self.all_cores
                {0}
        """).format(
            self._indent(self.build_parallel_threads_launcher("self.jobs_list", "JobThread"), 8), '\n'.ljust(13))

    def build_main(self):
        nodes_list = self.build_nodes_list()
        self.exit_thread = "os._exit(1)"
        joblist_thread = self.build_joblist_thread()
        threads_launcher = self.build_sequential_threads_launcher("scripts", "JobListThread(scripts[i], i, "
                                                                             "copy.deepcopy(all_cores))", footer=False)
        return joblist_thread + nodes_list + threads_launcher


class BashWrapperBuilder(WrapperBuilder):

    def build_imports(self):
        return ""

    def build_main(self):
        return textwrap.dedent("""
        # Initializing variables
        scripts="{0}"
        i=0
        pids=""
        """).format(' '.join(str(s) for s in self.job_scripts), '\n'.ljust(13))

    def build_job_thread(self):
        return textwrap.dedent("""
        execute_script()
            {{
                out="$1.$2.out"
                err="$1.$2.err"
                bash $1 > $out 2> $err &
                pid=$!
            }}
        """).format('\n'.ljust(13))

    def build_sequential_threads_launcher(self):
        return textwrap.dedent("""
        for script in $scripts; do
            execute_script "$SCRATCH/{0}/LOG_{0}/$script" $i
            wait $pid
            if [ $? -eq 0 ]; then
                echo "The job $script has been COMPLETED"
            else
                echo "The job $script has FAILED"
                exit 1
            fi
            i=$((i+1))
        done
        """).format(self.expid, '\n'.ljust(13))

    def build_parallel_threads_launcher(self):
        return textwrap.dedent("""
        for script in $scripts; do
            execute_script "$SCRATCH/{0}/LOG_{0}/$script" $i
            pids+="$pid "
            i=$((i+1))
        done

        # Waiting until all scripts finish
        for pid in $pids; do
            wait $pid
            if [ $? -eq 0 ]; then
                echo "The job $pid has been COMPLETED"
            else
                echo "The job $pid has FAILED"
            fi
        done
        """).format(self.expid, '\n'.ljust(13))


class BashVerticalWrapperBuilder(BashWrapperBuilder):

    def build_main(self):
        return super(BashVerticalWrapperBuilder, self).build_main() + self.build_sequential_threads_launcher()


class BashHorizontalWrapperBuilder(BashWrapperBuilder):

    def build_main(self):
        return super(BashHorizontalWrapperBuilder, self).build_main() + self.build_parallel_threads_launcher()
