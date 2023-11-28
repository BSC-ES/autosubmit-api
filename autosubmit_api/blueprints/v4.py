from flask import Blueprint
from autosubmit_api.views import not_implemented_handler
from autosubmit_api.views import v3 as v3_views
from autosubmit_api.views import v4 as v4_views


def create_v4_blueprint():
    blueprint = Blueprint("v4", __name__)

    blueprint.route("/login")(v3_views.login)
    blueprint.route("/verify-token")(v3_views.login)

    blueprint.route("/experiments/<string:expid>/description", methods=["PUT"])(
        not_implemented_handler
    )  # TODO
    blueprint.route("/experiments/<string:expid>/config")(
        v3_views.get_current_configuration
    )
    blueprint.route("/experiments/<string:expid>/info")(v3_views.exp_info)
    blueprint.route("/experiments/<string:expid>/status-counters")(
        v3_views.exp_counters
    )

    blueprint.route("/experiments")(v4_views.search_experiments_view)

    blueprint.route("/experiments/<string:expid>/runs")(v3_views.get_runs)
    blueprint.route("/experiments/<string:expid>/check-running")(
        v3_views.get_if_running
    )
    blueprint.route("/experiments/<string:expid>/running-detail")(
        v3_views.get_running_detail
    )
    blueprint.route("/experiments/<string:expid>/summary")(v3_views.get_expsummary)

    blueprint.route("/routes/<string:route>/shutdown")(v3_views.shutdown)

    blueprint.route("/experiments/<string:expid>/performance")(
        v3_views.get_exp_performance
    )
    blueprint.route("/experiments/<string:expid>/graph")(
        not_implemented_handler  # TODO v3_views.get_graph_format
    )
    blueprint.route("/experiments/<string:expid>/tree")(v3_views.get_exp_tree)
    blueprint.route("/experiments/<string:expid>/quick")(v3_views.get_quick_view_data)

    blueprint.route("/experiments/<string:expid>/run-log")(
        v3_views.get_experiment_run_log
    )
    blueprint.route("/job-logs/<string:logfile>")(v3_views.get_job_log_from_path)

    blueprint.route("/experiments/<string:expid>/graph-diff")(
        not_implemented_handler  # TODO v3_views.get_experiment_pklinfo
    )
    blueprint.route("/experiments/<string:expid>/tree-diff")(
        not_implemented_handler  # TODO v3_views.get_experiment_tree_pklinfo
    )
    blueprint.route("/experiments/<string:expid>/stats")(
        not_implemented_handler  # TODO v3_views.get_experiment_statistics
    )
    blueprint.route("/experiments/<string:expid>/jobs/<string:jobname>/history")(
        v3_views.get_exp_job_history
    )
    blueprint.route("/experiments/<string:expid>/runs/<string:runid>")(
        v3_views.get_experiment_run_job_detail
    )
    blueprint.route("/filestatus")(v3_views.get_file_status)

    return blueprint
