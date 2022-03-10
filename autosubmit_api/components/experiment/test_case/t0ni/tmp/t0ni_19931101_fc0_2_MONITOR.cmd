#!/esarchive/autosubmit/t0ni/proj/auto-ecearth3/es-esmvaltool/common-tools/auto-ecearth/nord3_launcher

###############################################################################
#                   MONITOR t0ni EXPERIMENT
###############################################################################
#
#BSUB -q sequential
#BSUB -J t0ni_19931101_fc0_2_MONITOR
#BSUB -oo /gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_19931101_fc0_2_MONITOR.cmd.out
#BSUB -eo /gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_19931101_fc0_2_MONITOR.cmd.err
#BSUB -W 01:00
#BSUB -n 4



#
###############################################################################
###################
# Autosubmit header
###################

import time

job_name_ptrn = '/gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_19931101_fc0_2_MONITOR'
stat_file = open(job_name_ptrn + '_STAT', 'w')
stat_file.write('{0:.0f}\n'.format(time.time()))
stat_file.close()


###################
# Autosubmit job
###################

import subprocess
import os
from typing import DefaultDict
import yaml
import json
import glob


class Monitor():
    def __init__(self):
        self.container = (
            "/esarchive/software/containers/esmvaltool/esmvaltool-m1.0.0.sif")
        self._experiment = "piControl"
        self.projdir = "/esarchive/autosubmit/t0ni/proj/auto-ecearth3"
        self.scratch_dir = os.path.join("/gpfs/scratch",
                                        "bsc32", "bsc32627",
                                        "t0ni")
        self.expid = "t0ni"
        self.member = "fc0"
        self.start_date = "19931101"
        self.cmor_add_startdate = "FALSE"
        self.cmor_model_id = "EC-EARTH-AOGCM"
        self.cmor_exp_custom = "FALSE"
        self.bsc_outclass = "reduced"
        self.cmip6_outclass = ""
        self.available_variables = DefaultDict(set)
        self.cmor_activity_id = "CMIP"

        self._get_sub_experiment_id()
        if not self.sub_experiment_id:
            self.add_startdate = False
            self.startdate = None
        else:
            self.add_startdate = True
            self.startdate = self.sub_experiment_id

    @property
    def esmvaltool_args(self):
        return ("--check-level relaxed "
                "--log-level debug "
                "--max-parallel-tasks 4 "
                f"--config-file {self.config_user} "
                f"--config-developer-file {self.config_developer} ")

    @property
    def monitor_folder(self):
        return os.path.join(self.esmvaltool_folder, 'common-tools', 'monitor')

    @property
    def esmvaltool_folder(self):
        return os.path.join(self.projdir, 'es-esmvaltool')

    @property
    def config_user(self):
        return os.path.join(self.esmvaltool_folder, 'config-files',
                            "config-user.yml")

    @property
    def config_developer(self):
        return os.path.join(self.esmvaltool_folder, 'config-files',
                            "config-developer.yml")

    @staticmethod
    def _print_bytes(value):
        if value:
            print(value.decode('utf-8'))

    def _get_sub_experiment_id(self):
        
        output = subprocess.check_output(
            "set -xuve; "
            f". {self.projdir}/plugins/cmorization.sh; "
            "create_sub_experiment_id; "
            "echo ${sub_experiment_id}",
            shell=True,
            env={
                "CMOR_EXP_CUSTOM": self.cmor_exp_custom,
                "BSC_OUTCLASS": self.bsc_outclass,
                "CMIP6_OUTCLASS": self.cmip6_outclass,
                "CMOR_ADD_STARTDATE": self.cmor_add_startdate,
                "CMOR_ACTIVITY_ID": self.cmor_activity_id
            },
        )
        self._print_bytes(output)
        self.sub_experiment_id = output[-1]

    def run(self):
        self.load_outclass()
        for domain in 'OCEAN ATMOS'.lower().split(' '):
            print(f'Preparing {domain} recipe...')
            recipe = os.path.join(self.monitor_folder,
                                  f"recipe_monitor_{domain}.yml")
            if not os.path.isfile(recipe):
                raise ValueError(f"Can not find recipe file at {recipe}")

            if self.cmor_model_id == "EC-EARTH-AOGCM":
                dataset = "EC-Earth3"
            else:
                dataset = self.cmor_model_id.replace('EC-EARTH', 'EC-Earth3')

            dataset_info = {
                "project": "ECEARTH",
                "expid": self.expid,
                "dataset": dataset,
                "exp": self._experiment,
                "ensemble": f"r{int(self.member[2:]) + 1}i1p1f1",
                "start_year": int(self.start_date[:4]),
                "activity": self.cmor_activity_id,
                "end_year": int("1993")
            }

            with open(recipe) as recipe_handler:
                current_recipe = yaml.load(recipe_handler,
                                           Loader=yaml.SafeLoader)
            current_recipe["datasets"] = [dataset_info]
            for diag_name, diagnostic in list(
                    current_recipe['diagnostics'].items()):
                for var_name, variable in list(
                        diagnostic['variables'].items()):
                    if not self.in_outclass(
                            variable.get('short_name', var_name), variable):
                        print(
                            f"Removing variable {var_name} from {diag_name} because it is missing from the outclass"
                        )
                        del diagnostic['variables'][var_name]
                if not diagnostic['variables']:
                    print(
                        f"Removing diagnostic {diag_name} because there are no remaining variables"
                    )
                    del current_recipe['diagnostics'][diag_name]
                    continue
                for _, script in diagnostic['scripts'].items():
                    script['script'] = os.path.join(self.monitor_folder,
                                                    'monitor.py')

            os.makedirs(self.scratch_dir, exist_ok=True)
            recipe = os.path.join(self.scratch_dir,
                                  f"recipe_t0ni_19931101_fc0_2_MONITOR_{domain}.yml".lower())
            with open(recipe, 'w') as recipe_handler:
                yaml.dump(current_recipe, recipe_handler)
            environment = dict(
                os.environ, **{
                    "PROJ_LIB":
                    "/opt/conda/share/proj/",
                    "SINGULARITY_BINDPATH":
                    f"/esarchive,/home/bsc32,{self.projdir}",
                })
            print(f'Running {domain} recipe...')
            try:
                output = subprocess.check_output(
                    "set -xuve; "
                    "module purge; "
                    "module load Singularity; "
                    "newgrp Earth; "
                    f"singularity run {self.container} run "
                    f"{self.esmvaltool_args} {recipe}",
                    env=environment,
                    shell=True,
                )
            except subprocess.CalledProcessError as ex:
                self._print_bytes(ex.stdout)
                self._print_bytes(ex.stderr)
                raise
            self._print_bytes(output)
            os.remove(recipe)
            print(f'Recipe {domain} completed!')

    def load_outclass(self):
        if self.bsc_outclass != "":
          intermediate_outclass_path='outclass'
          outclass_path = os.path.join(
              self.projdir,
              intermediate_outclass_path,
              self.bsc_outclass,
          )

        else:
          intermediate_outclass_path=os.path.join('sources/runtime/classic/ctrl/output-control-files/cmip6')
          outclass_path = os.path.join(
              self.projdir,
              intermediate_outclass_path,
              self.cmip6_outclass,
          )
        outclass_file = glob.glob(os.path.join(outclass_path,
                                               "*varlist*.json"))
        if not outclass_file:
            raise ValueError(
                f'Outclass file can not be found for {self.bsc_outclass}{self.cmip6_outclass}')
        with open(outclass_file[0]) as f:
            outclass = json.load(f)
        for _, output in outclass.items():
            for table, values in output.items():
                self.available_variables[table].update(values)
        if not self.available_variables:
            raise ValueError(
                f'Can not read variables for outclass {self.bsc_outclass}{self.cmip6_outclass}')

    def in_outclass(self, var_name, variable_info):
        if var_name.endswith('Ysum'):
            check_all_mips = True
            var_name = var_name[0:-4]
        else:
            check_all_mips = True
        required_vars = set(self.get_required_vars(var_name))
        if check_all_mips:
            found_vars = set()
            for mip in self.available_variables.values():
                found_vars.update(mip.intersection(required_vars))
                if found_vars == required_vars:
                    return True
            return False
        if required_vars.issubset(
                self.available_variables[variable_info['mip']]):
            return True
        else:
            return False

    def get_required_vars(self, var_name):
        subfixes = (
            'mean',
            'sum',
        )
        for subfix in subfixes:
            if var_name.endswith(subfix):
                return (var_name[0:-len(subfix)], )
        if var_name.startswith('heatc'):
            return ('thetao', )
        derived_vars = {
            'siextentn': ('siconc', ),
            'siextents': ('siconc', ),
            'sivoln': ('sivol', ),
            'sivols': ('sivol', ),
        }
        return derived_vars.get(var_name, (var_name, ))


if __name__ == "__main__":
    Monitor().run()

###################
# Autosubmit tailer
###################

stat_file = open(job_name_ptrn + '_STAT', 'a')
stat_file.write('{0:.0f}\n'.format(time.time()))
stat_file.close()
open(job_name_ptrn + '_COMPLETED', 'a').close()
exit(0)
