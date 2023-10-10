# #!/usr/bin/env python

# # Copyright 2017 Earth Sciences Department, BSC-CNS

# # This file is part of Autosubmit.

# # Autosubmit is free software: you can redistribute it and/or modify
# # it under the terms of the GNU General Public License as published by
# # the Free Software Foundation, either version 3 of the License, or
# # (at your option) any later version.

# # Autosubmit is distributed in the hope that it will be useful,
# # but WITHOUT ANY WARRANTY; without even the implied warranty of
# # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# # GNU General Public License for more details.

# # You should have received a copy of the GNU General Public License
# # along with Autosubmit.  If not, see <http://www.gnu.org/licenses/>.

# import datetime
# import numpy as np
# import matplotlib.pyplot as plt
# import matplotlib.gridspec as gridspec
# import matplotlib.patches as mpatches
# from autosubmitAPIwu.experiment.statistics import ExperimentStats
# from autosubmitAPIwu.job.job_common import Status
# from bscearth.utils.log import Log
# from autosubmitAPIwu.job.job import Job

# # Autosubmit stats constants
# RATIO = 4
# MAX_JOBS_PER_PLOT = 12.0


# def create_bar_diagram(experiment_id, jobs_list, general_stats, output_file, period_ini=None, period_fi=None):
#     # Error prevention
#     plt.close('all')
#     # Stats variables definition
#     num_plots = int(np.ceil(len(jobs_list) / MAX_JOBS_PER_PLOT))
#     ind = np.arange(int(MAX_JOBS_PER_PLOT))
#     width = 0.16
#     # Creating stats figure
#     fig = plt.figure(figsize=(RATIO * 4, 3 * RATIO * num_plots))
#     fig.suptitle('STATS - ' + experiment_id, fontsize=24, fontweight='bold')
#     # Variables initialization
#     ax, ax2 = [], []
#     rects = [None] * 6
#     exp_stats = ExperimentStats(jobs_list, period_ini, period_fi)
#     grid_spec = gridspec.GridSpec(RATIO * num_plots + 2, 1)
#     for plot in range(1, num_plots + 1):
#         # Calculating jobs inside the given plot
#         l1 = int((plot - 1) * MAX_JOBS_PER_PLOT)
#         l2 = int(plot * MAX_JOBS_PER_PLOT)
#         # Building plot axis
#         ax.append(fig.add_subplot(grid_spec[RATIO * plot - RATIO + 2:RATIO * plot + 1]))
#         ax[plot - 1].set_ylabel('hours')
#         ax[plot - 1].set_xticks(ind + width)
#         ax[plot - 1].set_xticklabels([job.name for job in jobs_list[l1:l2]], rotation='vertical')
#         ax[plot - 1].set_title(experiment_id, fontsize=20)
#         ax[plot - 1].set_ylim(0, float(1.10 * exp_stats.max_time))
#         # Axis 2
#         ax2.append(ax[plot - 1].twinx())
#         ax2[plot - 1].set_ylabel('# failed jobs')
#         ax2[plot - 1].set_yticks(range(0, exp_stats.max_fail + 2))
#         ax2[plot - 1].set_ylim(0, exp_stats.max_fail + 1)
#         # Building rects
#         rects[0] = ax[plot - 1].bar(ind, exp_stats.queued[l1:l2], width, color='orchid')
#         rects[1] = ax[plot - 1].bar(ind + width, exp_stats.run[l1:l2], width, color='limegreen')
#         rects[2] = ax2[plot - 1].bar(ind + width * 2, exp_stats.failed_jobs[l1:l2], width, color='red')
#         rects[3] = ax[plot - 1].bar(ind + width * 3, exp_stats.fail_queued[l1:l2], width, color='purple')
#         rects[4] = ax[plot - 1].bar(ind + width * 4, exp_stats.fail_run[l1:l2], width, color='tomato')
#         rects[5] = ax[plot - 1].plot([0., width * 6 * MAX_JOBS_PER_PLOT], [exp_stats.threshold, exp_stats.threshold],
#                                      "k--", label='wallclock sim')

#     # Building legends subplot
#     legends_plot = fig.add_subplot(grid_spec[0, 0])
#     legends_plot.set_frame_on(False)
#     legends_plot.axes.get_xaxis().set_visible(False)
#     legends_plot.axes.get_yaxis().set_visible(False)

#     # Building legends
#     build_legends(legends_plot, rects, exp_stats, general_stats)

#     # Saving output figure
#     grid_spec.tight_layout(fig, rect=[0, 0.03, 1, 0.97])
#     plt.savefig(output_file)

#     create_csv_stats(exp_stats, jobs_list, output_file)

# def create_csv_stats(exp_stats, jobs_list, output_file):
#     job_names = [job.name for job in jobs_list]
#     start_times = exp_stats.start_times
#     end_times = exp_stats.end_times
#     queuing_times = exp_stats.queued
#     running_times = exp_stats.run

#     output_file = output_file.replace('pdf', 'csv')
#     with open(output_file, 'wb') as file:
#         file.write("Job,Started,Ended,Queuing time (hours),Running time (hours)\n")
#         for i in range(len(jobs_list)):
#             file.write("{0},{1},{2},{3},{4}\n".format(job_names[i], start_times[i], end_times[i], queuing_times[i], running_times[i]))

# def build_legends(plot, rects, experiment_stats, general_stats):
#     # Main legend with colourful rectangles
#     legend_rects = [[rect[0] for rect in rects]]
#     legend_titles = [
#         ['Queued (h)', 'Run (h)', 'Failed jobs (#)', 'Fail Queued (h)', 'Fail Run (h)', 'Max wallclock (h)']
#     ]
#     legend_locs = ["upper right"]
#     legend_handlelengths = [None]

#     # General stats legends, if exists
#     if len(general_stats) > 0:
#         legend_rects.append(get_whites_array(len(general_stats)))
#         legend_titles.append([str(key) + ': ' + str(value) for key, value in general_stats])
#         legend_locs.append("upper center")
#         legend_handlelengths.append(0)

#     # Total stats legend
#     legend_rects.append(get_whites_array(len(experiment_stats.totals)))
#     legend_titles.append(experiment_stats.totals)
#     legend_locs.append("upper left")
#     legend_handlelengths.append(0)

#     # Creating the legends
#     legends = create_legends(plot, legend_rects, legend_titles, legend_locs, legend_handlelengths)
#     for legend in legends:
#         plt.gca().add_artist(legend)


# def create_legends(plot, rects, titles, locs, handlelengths):
#     legends = []
#     for i in xrange(len(rects)):
#         legends.append(create_legend(plot, rects[i], titles[i], locs[i], handlelengths[i]))
#     return legends


# def create_legend(plot, rects, titles, loc, handlelength=None):
#     return plot.legend(rects, titles, loc=loc, handlelength=handlelength)


# def get_whites_array(length):
#     white = mpatches.Rectangle((0, 0), 0, 0, alpha=0.0)
#     return [white for _ in xrange(length)]
