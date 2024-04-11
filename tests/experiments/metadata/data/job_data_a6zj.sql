PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE experiment_run (
      run_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
      created TEXT NOT NULL,
      modified TEXT NOT NULL,
      start INTEGER NOT NULL,
      finish INTEGER,
      chunk_unit TEXT NOT NULL,
      chunk_size INTEGER NOT NULL,
      completed INTEGER NOT NULL,
      total INTEGER NOT NULL,
      failed INTEGER NOT NULL,
      queuing INTEGER NOT NULL,
      running INTEGER NOT NULL,
      submitted INTEGER NOT NULL,
      suspended INTEGER NOT NULL DEFAULT 0,
      metadata TEXT
      );
INSERT INTO experiment_run VALUES(1,'2024-04-11-16:53:56','2024-04-11-16:53:56',1712847236,0,'month',4,0,10,0,0,0,0,0,'{"CONFIG": {"AUTOSUBMIT_VERSION": "4.0.101", "MAXWAITINGJOBS": 20, "TOTALJOBS": 20, "SAFETYSLEEPTIME": 10, "RETRIALS": 0}, "MAIL": {"NOTIFICATIONS": false, "TO": null}, "STORAGE": {"TYPE": "pkl", "COPY_REMOTE_LOGS": true}, "DEFAULT": {"EXPID": "a6zj", "HPCARCH": "MARENOSTRUM4"}, "EXPERIMENT": {"DATELIST": "20000101", "MEMBERS": "fc0", "CHUNKSIZEUNIT": "month", "CHUNKSIZE": 4, "NUMCHUNKS": 4, "CHUNKINI": "", "CALENDAR": "standard"}, "PROJECT": {"PROJECT_TYPE": "none", "PROJECT_DESTINATION": ""}, "GIT": {"PROJECT_ORIGIN": "", "PROJECT_BRANCH": "", "PROJECT_COMMIT": "", "PROJECT_SUBMODULES": "", "FETCH_SINGLE_BRANCH": true}, "SVN": {"PROJECT_URL": "", "PROJECT_REVISION": ""}, "LOCAL": {"PROJECT_PATH": ""}, "PROJECT_FILES": {"FILE_PROJECT_CONF": "", "FILE_JOBS_CONF": "", "JOB_SCRIPTS_TYPE": ""}, "RERUN": {"RERUN": false, "RERUN_JOBLIST": ""}, "WRAPPERS": {"WRAPPER_V": {"TYPE": "vertical", "JOBS_IN_WRAPPER": "SIM"}}, "JOBS": {"LOCAL_SETUP": {"FILE": "LOCAL_SETUP.sh", "PLATFORM": "LOCAL", "RUNNING": "once", "DEPENDENCIES": {}, "ADDITIONAL_FILES": []}, "REMOTE_SETUP": {"FILE": "REMOTE_SETUP.sh", "DEPENDENCIES": {"LOCAL_SETUP": {}}, "WALLCLOCK": "00:05", "RUNNING": "once", "ADDITIONAL_FILES": []}, "INI": {"FILE": "INI.sh", "DEPENDENCIES": {"REMOTE_SETUP": {}}, "RUNNING": "member", "WALLCLOCK": "00:05", "ADDITIONAL_FILES": []}, "SIM": {"FILE": "SIM.sh", "DEPENDENCIES": {"INI": {}, "SIM-1": {}}, "RUNNING": "chunk", "WALLCLOCK": "00:05", "ADDITIONAL_FILES": []}, "POST": {"FILE": "POST.sh", "DEPENDENCIES": {"SIM": {}}, "RUNNING": "once", "WALLCLOCK": "00:05", "ADDITIONAL_FILES": []}, "CLEAN": {"FILE": "CLEAN.sh", "DEPENDENCIES": {"POST": {}}, "RUNNING": "once", "WALLCLOCK": "00:05", "ADDITIONAL_FILES": []}, "TRANSFER": {"FILE": "TRANSFER.sh", "PLATFORM": "LOCAL", "DEPENDENCIES": {"CLEAN": {}}, "RUNNING": "member", "ADDITIONAL_FILES": []}}, "PLATFORMS": {"MARENOSTRUM4": {"TYPE": "slurm", "HOST": "mn1.bsc.es", "PROJECT": "bsc32", "USER": "ltenorio", "QUEUE": "debug", "SCRATCH_DIR": "/gpfs/scratch", "ADD_PROJECT_TO_HOST": false, "MAX_WALLCLOCK": "48:00", "TEMP_DIR": ""}, "MARENOSTRUM_ARCHIVE": {"TYPE": "ps", "HOST": "dt02.bsc.es", "PROJECT": "bsc32", "USER": null, "SCRATCH_DIR": "/gpfs/scratch", "ADD_PROJECT_TO_HOST": false, "TEST_SUITE": false}, "TRANSFER_NODE": {"TYPE": "ps", "HOST": "dt01.bsc.es", "PROJECT": "bsc32", "USER": null, "ADD_PROJECT_TO_HOST": false, "SCRATCH_DIR": "/gpfs/scratch"}, "TRANSFER_NODE_BSCEARTH000": {"TYPE": "ps", "HOST": "bscearth000", "USER": null, "PROJECT": "Earth", "ADD_PROJECT_TO_HOST": false, "QUEUE": "serial", "SCRATCH_DIR": "/esarchive/scratch"}, "BSCEARTH000": {"TYPE": "ps", "HOST": "bscearth000", "USER": null, "PROJECT": "Earth", "ADD_PROJECT_TO_HOST": false, "QUEUE": "serial", "SCRATCH_DIR": "/esarchive/scratch"}, "NORD3": {"TYPE": "SLURM", "HOST": "nord1.bsc.es", "PROJECT": "bsc32", "USER": null, "QUEUE": "debug", "SCRATCH_DIR": "/gpfs/scratch", "MAX_WALLCLOCK": "48:00"}, "ECMWF-XC40": {"TYPE": "ecaccess", "VERSION": "pbs", "HOST": "cca", "USER": null, "PROJECT": "spesiccf", "ADD_PROJECT_TO_HOST": false, "SCRATCH_DIR": "/scratch/ms", "QUEUE": "np", "SERIAL_QUEUE": "ns", "MAX_WALLCLOCK": "48:00"}}, "ROOTDIR": "/home/ltenorio/autosubmit/a6zj", "PROJDIR": "/home/ltenorio/autosubmit/a6zj/proj/"}');
CREATE TABLE job_data (
      id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
      counter INTEGER NOT NULL,
      job_name TEXT NOT NULL,
      created TEXT NOT NULL,
      modified TEXT NOT NULL,
      submit INTEGER NOT NULL,
      start INTEGER NOT NULL,
      finish INTEGER NOT NULL,
      status TEXT NOT NULL,
      rowtype INTEGER NOT NULL,
      ncpus INTEGER NOT NULL,
      wallclock TEXT NOT NULL,
      qos TEXT NOT NULL,
      energy INTEGER NOT NULL,
      date TEXT NOT NULL,
      section TEXT NOT NULL,
      member TEXT NOT NULL,
      chunk INTEGER NOT NULL,
      last INTEGER NOT NULL,
      platform TEXT NOT NULL,
      job_id INTEGER NOT NULL,
      extra_data TEXT NOT NULL,
      nnodes INTEGER NOT NULL DEFAULT 0,
      run_id INTEGER,
      MaxRSS REAL NOT NULL DEFAULT 0.0,
      AveRSS REAL NOT NULL DEFAULT 0.0,
      out TEXT NOT NULL,
      err TEXT NOT NULL,
      rowstatus INTEGER NOT NULL DEFAULT 0,
      children TEXT,
      platform_output TEXT,
      UNIQUE(counter,job_name)
      );
DELETE FROM sqlite_sequence;
INSERT INTO sqlite_sequence VALUES('experiment_run',1);
CREATE INDEX ID_JOB_NAME ON job_data(job_name);
COMMIT;
