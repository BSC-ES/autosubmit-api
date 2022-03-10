#!/usr/bin/env python
import subprocess
import os
import sqlite3
from time import time, sleep


READ_ONLY_FILES = ["job_data_a3og.db",
"job_data_a438.db",
"job_data_a43p.db",
"job_data_a3nn.db",
"job_data_a431.db",
"job_data_a3tb.db",
"job_data_a3nk.db",
"job_data_a3zy.db",
"job_data_a3z9.db",
"job_data_a3xx.db",
"job_data_a43j.db",
"job_data_a410.db",
"job_data_a411.db",
"job_data_a40z.db",
"job_data_a35s.db",
"job_data_a34y.db",
"job_data_a35h.db",
"job_data_a3pd.db",
"job_data_a3fj.db",
"job_data_a3z4.db",
"job_data_a42m.db",
"job_data_a2in.db",
"job_data_a3xu.db",
"job_data_a41z.db",
"job_data_a43g.db",
"job_data_a40j.db",
"job_data_a3rd.db",
"job_data_a3w5.db",
"job_data_t0og.db",
"job_data_t08c.db",
"job_data_a3p9.db",
"job_data_a3yu.db",
"job_data_a37p.db",
"job_data_a3ge.db",
"job_data_a42g.db",
"job_data_a2al.db",
"job_data_a428.db",
"job_data_t0n8.db",
"job_data_t0n7.db",
"job_data_t0nh.db",
"job_data_t0ni.db",
"job_data_t0nf.db",
"job_data_t0ne.db",
"job_data_t0ng.db",
"job_data_t0nb.db",
"job_data_t0na.db",
"job_data_t0n4.db",
"job_data_t0n6.db",
"job_data_t0nj.db",
"job_data_t0n5.db",
"job_data_t0nc.db",
"job_data_t0n3.db",
"job_data_t0nd.db",
"job_data_a420.db",
"job_data_a3nv.db",
"job_data_a3oy.db",
"job_data_a3vw.db",
"job_data_a3p0.db",
"job_data_a3ux.db",
"job_data_a3oz.db",
"job_data_a3uu.db",
"job_data_a43m.db",
"job_data_a42f.db",
"job_data_a42e.db",
"job_data_a41m.db",
"job_data_a43h.db",
"job_data_a404.db",
"job_data_a42d.db",
"job_data_a43a.db",
"job_data_a42y.db",
"job_data_a434.db",
"job_data_a43b.db",
"job_data_a3t4.db",
"job_data_a41u.db",
"job_data_a426.db",
"job_data_a424.db",
"job_data_a43r.db",
"job_data_a403.db",
"job_data_a3ta.db",
"job_data_a3ul.db",
"job_data_a3pp.db",
"job_data_a43q.db",
"job_data_a405.db",
"job_data_a42h.db",
"job_data_a42l.db",
"job_data_a3ql.db",
"job_data_a3xz.db",
"job_data_a429.db",
"job_data_a3np.db",
"job_data_a3vy.db",
"job_data_a3vz.db",
"job_data_a3w1.db",
"job_data_a3w0.db",
"job_data_a439.db",
"job_data_t0ms.db",
"job_data_t02a.db",
"job_data_a42p.db",
"job_data_a42r.db",
"job_data_a3zf.db",
"job_data_a42z.db",
"job_data_a42b.db",
"job_data_t0mu.db",
"job_data_a430.db",
"job_data_t0mq.db",
"job_data_a3hd.db",
"job_data_t0mr.db",
"job_data_t0mt.db",
"job_data_a41x.db",
"job_data_t0mv.db",
"job_data_a3wy.db",
"job_data_a3wx.db",
"job_data_a3wv.db",
"job_data_a3ww.db",
"job_data_a3s1.db",
"job_data_a3x1.db",
"job_data_a3qw.db",
"job_data_a43o.db",
"job_data_t029.db",
"job_data_t09v.db",
"job_data_a408.db",
"job_data_a43t.db",
"job_data_a43v.db",
"job_data_a41o.db",
"job_data_a40m.db",
"job_data_t0mw.db",
"job_data_a409.db",
"job_data_a3rz.db",
"job_data_t0lk.db",
"job_data_a3pe.db",
"job_data_a42k.db",
"job_data_a41k.db",
"job_data_a3wo.db",
"job_data_a3yq.db",
"job_data_a3p4.db",
"job_data_a41r.db",
"job_data_a3vs.db",
"job_data_a3vr.db",
"job_data_a2mc.db",
"job_data_a3vp.db",
"job_data_a42w.db",
"job_data_a3kd.db",
"job_data_a43l.db",
"job_data_a43k.db",
"job_data_a435.db",
"job_data_a43n.db",
"job_data_a3z6.db",
"job_data_a40c.db",
"job_data_a41e.db",
"job_data_a43f.db",
"job_data_a41t.db",
"job_data_a40k.db",
"job_data_a41l.db",
"job_data_a42x.db",
"job_data_a3zq.db",
"job_data_a425.db",
"job_data_a437.db",
"job_data_a436.db",
"job_data_a432.db",
"job_data_a415.db",
"job_data_a42s.db",
"job_data_a42q.db",
"job_data_a42o.db",
"job_data_a42t.db",
"job_data_a42i.db",
"job_data_a41w.db",
"job_data_a3ow.db",
"job_data_a42u.db",
"job_data_a42n.db",
"job_data_a3zg.db",
"job_data_a42j.db",
"job_data_a40n.db",
"job_data_a3pg.db",
"job_data_a42c.db",
"job_data_a40u.db",
"job_data_a3tk.db",
"job_data_a3tj.db",
"job_data_a3th.db",
"job_data_a3ti.db",
"job_data_a3tg.db",
"job_data_a41q.db",
"job_data_a42a.db",
"job_data_a427.db",
"job_data_a413.db",
"job_data_a422.db",
"job_data_a423.db",
"job_data_a421.db",
"job_data_a41v.db",
"job_data_a3va.db",
"job_data_a3vc.db",
"job_data_a3ve.db",
"job_data_a3vd.db",
"job_data_a3vb.db",
"job_data_a41y.db"]

PATH = "/esarchive/autosubmit/as_metadata/data"

def fixing_read_only():
  # for file_name in READ_ONLY_FILES:
  #   file_path = os.path.join(PATH, file_name)
  #   subprocess.Popen(["cp", file_path, "{}_copy".format(file_path)])
  
  # print("Wait until all commands are completed")
  # sleep(10)

  # for file_name in READ_ONLY_FILES:
  #   file_path = os.path.join(PATH, file_name)
  #   subprocess.Popen(["rm", "-rf", file_path])

  # print("Wait until all commands are completed")
  # sleep(10)
  
  for file_name in READ_ONLY_FILES:
    file_path = os.path.join(PATH, file_name)
    subprocess.Popen(["mv", "{}_copy".format(file_path), file_path])

  print("Wait for commands")
  sleep(10)

  print("Assigning permissions")
  for file_name in READ_ONLY_FILES:
    file_path = os.path.join(PATH, file_name)
    print(file_path)
    subprocess.Popen(["chmod", "776", file_path])

def main():
  currentDirectories = subprocess.Popen(['ls', '-t', PATH],
                                              stdout=subprocess.PIPE,
                                              stderr=subprocess.STDOUT) if (os.path.exists(PATH)) else None
  stdOut, stdErr = currentDirectories.communicate(
  ) if currentDirectories else (None, None)
  db_files = stdOut.split() if stdOut else []
  # db_files = ["job_data_a29z.db"]
  for dbfile in db_files:
    if dbfile.startswith("job_data_") and dbfile.endswith(".db"):
      path_file = os.path.join(PATH, dbfile)
      
      modification_time = int(os.stat(path_file).st_mtime)
      seconds_diff = int(time() - modification_time)
      days_diff = int(seconds_diff/(60*60*24))
      if days_diff < 45:
        print(path_file)
        print(days_diff)
        conn = sqlite3.connect(path_file)
        c = conn.cursor()
        try:
          c.execute("UPDATE job_data set status='COMPLETED' WHERE submit > 0 and start > 0 and finish > 0 and last = 0 and status != 'FAILED'")
          c.execute("UPDATE job_data set status='RUNNING' WHERE submit > 0 and start > 0 and finish = 0 and last = 0 and status != 'FAILED'")
          c.execute("UPDATE job_data set status='QUEUING' WHERE submit > 0 and start = 0 and finish = 0 and last = 0 and status != 'FAILED'")
          conn.commit()
          conn.close()
        except Exception as exp:
          print("{} -> {}".format(exp, path_file))


if __name__ == "__main__":
    # main()
    pass

