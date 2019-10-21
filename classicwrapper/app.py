from io import StringIO
import csv
import datetime
import json
import pytz
from typing import Dict

from flask import Flask, make_response, request

from dynatrace_api import DynatraceAPI
from utils import millis


app = Flask(__name__)


def json_to_csv(json_obj: Dict):
    data = []
    if "metrics" in json_obj:
        for selector, details in json_obj["metrics"].items():
            for serie in details["series"]:
                for value in serie["values"]:
                    ts = value["timestamp"]
                    val = value["value"]
                    if val is not None:
                        data.append([selector, "|".join(serie["dimensions"]), ts, val])
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
            millis(now.replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(seconds=1)),
        )
    }
    return time_filters[custom_time]


@app.route("/api/v2/metrics/series/<selector>")
def metrics_series(selector):
    with open(
        "config_customer.json", "r"
    ) as f:  # TODO - This file needs to be config.json
        config = json.load(f)
    d = DynatraceAPI(config["dynatrace_base_url"], config["dynatrace_token"])

    date_from = request.args.get("from", None)
    date_to = request.args.get("to", None)
    custom_time = request.args.get("customTime", None)
    timezone = request.args.get("timezone", None)
    if custom_time is not None:
        date_from, date_to = build_custom_time(custom_time, timezone)

    lines = json_to_csv(
        d.metrics_series(selector, date_from=date_from, date_to=date_to)
    )
    return csv_download(lines)


def main():
    app.run(debug=True)


if __name__ == "__main__":
    main()
