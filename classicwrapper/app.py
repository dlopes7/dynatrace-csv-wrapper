from io import StringIO
import csv
import datetime
import json
import pytz
from typing import Dict
import os
import logging
from logging.handlers import RotatingFileHandler

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
    log_handler = RotatingFileHandler(
        os.path.join(current_file_path, "log/app.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=10,
    )
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(funcName)s - %(message)s ")
    log_handler.setFormatter(fmt)
    app.logger.addHandler(log_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    app.logger.addHandler(stream_handler)

    app.logger.setLevel(logging.DEBUG)


def json_to_csv(json_obj: Dict, timezone=None):
    data = []
    if timezone is not None:
        timezone = pytz.timezone(timezone)
    if "metrics" in json_obj:
        for selector, details in json_obj["metrics"].items():
            for serie in details["series"]:
                for value in serie["values"]:
                    ts = value["timestamp"]
                    val = value["value"]
                    date = datetime.datetime.fromtimestamp(
                        ts / 1000, timezone
                    ).strftime("%d/%m/%Y %H:%M:%S%z")
                    if val is not None:
                        data.append(
                            [selector, "|".join(serie["dimensions"]), ts, date, val]
                        )
    return data


def csv_download(lines):
    si = StringIO()
    cw = csv.writer(si)
    cw.writerows(lines)
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=results.csv"
    output.headers["Content-type"] = "text/csv"
    return output


def build_custom_time(custom_time, timezone=None):
    if timezone is not None:
        timezone = pytz.timezone(timezone)

    now = datetime.datetime.now(timezone)
    time_filters = {
        "yesterday": (
            millis(
                now.replace(hour=0, minute=0, second=0, microsecond=0)
                - datetime.timedelta(days=1, seconds=1)
            ),
            millis(
                now.replace(hour=0, minute=0, second=0, microsecond=0)
                - datetime.timedelta(minutes=2, seconds=1)
            ),
        )
    }
    return time_filters[custom_time]


@app.route("/api/v2/metrics/series/<selector>")
def metrics_series(selector):
    with open(f"{current_file_path}/config.json", "r") as f:
        config = json.load(f)
    d = DynatraceAPI(
        config["dynatrace_base_url"], config["dynatrace_token"], logger=app.logger
    )

    date_from = request.args.get("from", None)
    date_to = request.args.get("to", None)
    next_page_key = request.args.get("nextPageKey", None)
    page_size = request.args.get("pageSize", None)
    resolution = request.args.get("resolution", None)
    scope = request.args.get("scope", None)

    custom_time = request.args.get("customTime", None)
    timezone = request.args.get("timezone", None)
    if custom_time is not None:
        date_from, date_to = build_custom_time(custom_time, timezone)

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

    lines = json_to_csv(data, timezone)
    return csv_download(lines)


def main():
    log_setup()
    app.run(host="0.0.0.0")


if __name__ == "__main__":
    main()
