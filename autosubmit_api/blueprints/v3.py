from flask import Blueprint
from autosubmit_api.views import v3 as v3_views


def create_v3_blueprint():
    blueprint = Blueprint("v3", __name__)

    blueprint.route("/login")(v3_views.login)
    blueprint.route("/tokentest", methods=["GET", "POST"])(v3_views.test_token)
    blueprint.route("/updatedesc", methods=["GET", "POST"])(v3_views.update_description)
    blueprint.route("/cconfig/<string:expid>", methods=["GET"])(
        v3_views.get_current_configuration
    )
    blueprint.route("/expinfo/<string:expid>", methods=["GET"])(v3_views.exp_info)
    blueprint.route("/expcount/<string:expid>", methods=["GET"])(v3_views.exp_counters)
    blueprint.route(
        "/searchowner/<string:owner>/<string:exptype>/<string:onlyactive>",
        methods=["GET"],
    )(v3_views.search_owner)
    blueprint.route("/searchowner/<string:owner>", methods=["GET"])(
        v3_views.search_owner
    )
    blueprint.route(
        "/search/<string:expid>/<string:exptype>/<string:onlyactive>", methods=["GET"]
    )(v3_views.search_expid)
    blueprint.route("/search/<string:expid>", methods=["GET"])(v3_views.search_expid)
    blueprint.route("/running/", methods=["GET"])(v3_views.search_running)
    blueprint.route("/runs/<string:expid>", methods=["GET"])(v3_views.get_runs)
    blueprint.route("/ifrun/<string:expid>", methods=["GET"])(v3_views.get_if_running)
    blueprint.route("/logrun/<string:expid>", methods=["GET"])(
        v3_views.get_running_detail
    )
    blueprint.route("/summary/<string:expid>", methods=["GET"])(v3_views.get_expsummary)
    blueprint.route("/shutdown/<string:route>")(v3_views.shutdown)
    blueprint.route("/performance/<string:expid>", methods=["GET"])(
        v3_views.get_exp_performance
    )
    blueprint.route(
        "/graph/<string:expid>/<string:layout>/<string:grouped>", methods=["GET"]
    )(v3_views.get_graph_format)
    blueprint.route("/tree/<string:expid>", methods=["GET"])(v3_views.get_exp_tree)
    blueprint.route("/quick/<string:expid>", methods=["GET"])(
        v3_views.get_quick_view_data
    )
    blueprint.route("/exprun/<string:expid>", methods=["GET"])(
        v3_views.get_experiment_run_log
    )
    blueprint.route("/joblog/<string:logfile>", methods=["GET"])(
        v3_views.get_job_log_from_path
    )
    blueprint.route("/pklinfo/<string:expid>/<string:timeStamp>", methods=["GET"])(
        v3_views.get_experiment_pklinfo
    )
    blueprint.route("/pkltreeinfo/<string:expid>/<string:timeStamp>", methods=["GET"])(
        v3_views.get_experiment_tree_pklinfo
    )
    blueprint.route(
        "/stats/<string:expid>/<string:filter_period>/<string:filter_type>"
    )(v3_views.get_experiment_statistics)
    blueprint.route("/history/<string:expid>/<string:jobname>")(
        v3_views.get_exp_job_history
    )
    blueprint.route("/rundetail/<string:expid>/<string:runid>")(
        v3_views.get_experiment_run_job_detail
    )
    blueprint.route("/filestatus/")(v3_views.get_file_status)

    return blueprint
