from io import StringIO
import csv
import datetime
import json
from typing import Dict
import os
import logging
from logging.handlers import RotatingFileHandler
from collections import OrderedDict

from flask import Flask, make_response, request

from dynatrace_api import DynatraceAPI
from utils import millis


app = Flask(__name__)
current_file_path = os.path.dirname(os.path.realpath(__file__))


@app.errorhandler(500)
def internal_error(exception):
    app.logger.exception(exception)
    return make_response({"error": {"message": str(exception)}}, 500)


def log_setup():
    log_handler = RotatingFileHandler(os.path.join(current_file_path, "log/app.log"), maxBytes=5 * 1024 * 1024, backupCount=10,)
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(funcName)s - %(message)s ")
    log_handler.setFormatter(fmt)
    app.logger.addHandler(log_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    app.logger.addHandler(stream_handler)
    app.logger.setLevel(logging.DEBUG)


def json_to_csv(json_obj: Dict):
    data = []
    if "metrics" in json_obj:
        for selector, details in json_obj["metrics"].items():
            for serie in details["series"]:
                for value in serie["values"]:
                    ts = value["timestamp"]
                    val = value["value"]
                    if val is not None:
                        data.append([selector, serie["dimensions"][0][-16:], ts, val])
    elif "dataResult" in json_obj:
        timeseries_id = json_obj["timeseriesId"]
        for dimension, datapoints in json_obj["dataResult"]["dataPoints"].items():
            for datapoint in datapoints:
                ts = datapoint[0]
                val = datapoint[1]
                if val is not None:
                    val = 0 if val == 100 else 1
                    data.append([timeseries_id, dimension.split(",")[0][-16:], ts, val])

    return data


def v1_to_v2(json_obj: Dict):
    response_template = OrderedDict({"totalCount": 0, "nextPageKey": None, "metrics": {}})

    if "dataResult" in json_obj:
        timeseries_id = "builtin:synthetic.browser.event.failure"
        response_template["metrics"][timeseries_id] = {"series": []}
        for dimension, datapoints in json_obj["dataResult"]["dataPoints"].items():
            serie = {"dimensions": [dimension.split(",")[-1].strip()], "values": []}
            response_template["totalCount"] = len(datapoints)
            for datapoint in datapoints:
                val = None
                if datapoint[1] is not None:
                    val = 1 if datapoint[1] > 0 else 0
                serie["values"].append({"timestamp": datapoint[0], "value": val})
            response_template["metrics"][timeseries_id]["series"].append(serie)
    return response_template


def csv_download(lines):
    si = StringIO()
    cw = csv.writer(si)
    cw.writerows(lines)
    output = make_response(si.getvalue())
    # output.headers["Content-Disposition"] = "attachment; filename=results.csv"
    # output.headers["Content-type"] = "text/csv"
    return output


def build_custom_time(custom_time):
    now = datetime.datetime.utcnow()
    time_filters = {
        "yesterday": (
            millis(now.replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(days=1, seconds=1)),
            millis(now.replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(minutes=2, seconds=1)),
        )
    }
    return time_filters[custom_time]


@app.route("/api/v2/metrics/series/<selector>")
def metrics_series(selector):
    with open(f"{current_file_path}/config.json", "r") as f:
        config = json.load(f)
    d = DynatraceAPI(config["dynatrace_base_url"], config["dynatrace_token"], logger=app.logger)

    date_from = request.args.get("from", None)
    date_to = request.args.get("to", None)
    next_page_key = request.args.get("nextPageKey", None)
    page_size = request.args.get("pageSize", 100000)
    resolution = request.args.get("resolution", None)
    scope = request.args.get("scope", None)

    custom_time = request.args.get("customTime", None)
    if custom_time is not None:
        date_from, date_to = build_custom_time(custom_time)

    data = d.metrics_series(
        selector,
        date_from=date_from,
        date_to=date_to,
        next_page_key=next_page_key,
        page_size=page_size,
        resolution=resolution,
        scope=scope,
    )

    if "error" in data:
        return make_response(data, data["error"]["code"])

    data_response = OrderedDict({"totalCount": 0, "nextPageKey": None, "metrics": {}})
    data_response["totalCount"] = data["totalCount"]
    data_response["nextPageKey"] = data["nextPageKey"]
    data_response["metrics"] = data["metrics"]

    # lines = json_to_csv(data)
    # return csv_download(lines)
    return json.dumps(data_response, indent=2)


@app.route("/api/v1/timeseries/<identifier>")
def timeseries(identifier):
    with open(f"{current_file_path}/config.json", "r") as f:
        config = json.load(f)
    d = DynatraceAPI(config["dynatrace_base_url"], config["dynatrace_token"], logger=app.logger)

    date_from = request.args.get("startTimestamp", None)
    date_to = request.args.get("endTimestamp", None)
    predict = request.args.get("predict", False)
    aggregation = request.args.get("aggregation", None)
    query_mode = request.args.get("queryMode", "SERIES")
    entity = request.args.get("entity", None)
    tag = request.args.get("tag", None)
    percentile = request.args.get("percentile", None)
    include_parents_ids = request.args.get("includeParentIds", False)
    consider_maintenance = request.args.get("considerMaintenanceWindowsForAvailability", False)

    custom_time = request.args.get("customTime", None)
    if custom_time is not None:
        date_from, date_to = build_custom_time(custom_time)

    data = d.timeseries(
        identifier,
        include_data=True,
        aggregation=aggregation,
        start_timestamp=date_from,
        end_timestamp=date_to,
        predict=predict,
        query_mode=query_mode,
        entity=entity,
        tag=tag,
        percentile=percentile,
        include_parents_ids=include_parents_ids,
        consider_maintenance=consider_maintenance,
    )

    if "error" in data:
        return make_response(data, data["error"]["code"])

    # lines = json_to_csv(data)
    # return csv_download(lines)
    return json.dumps(v1_to_v2(data), indent=2)


def main():
    log_setup()
    app.run(host="0.0.0.0", port=80, debug=True)


if __name__ == "__main__":
    main()
