import json
import logging

import requests

default_logger = logging.getLogger(__name__)
h = logging.StreamHandler()
h.setLevel(logging.DEBUG)
default_logger.addHandler(h)
default_logger.setLevel(logging.DEBUG)


class DynatraceAPI:
    def __init__(self, url: str, token: str, logger=default_logger):
        self.base_url = url
        self._auth = {"Authorization": f"Api-Token {token}"}
        self.logger = logger

    def _make_request(self, path, params=None, method="GET"):
        url = f"{self.base_url}{path}"
        self.logger.debug(f"Calling {url} with params: {params}")
        r = requests.request(method, url, params=params, headers=self._auth)
        self.logger.debug(f"Got response: {r} from {url}")
        return r.json()

    def metrics_descriptors(self):
        path = "/api/v2/metrics/descriptors"
        return self._make_request(path)

    def metrics_series(self, selector, resolution=None, date_from=None, date_to=None):
        path = f"/api/v2/metrics/series/{selector}"
        params = {"resolution": resolution, "from": date_from, "to": date_to}
        return self._make_request(path, params=params)

    def synthetic_monitors(self):
        path = "/api/v1/synthetic/monitors"
        return self._make_request(path)

    def synthetic_monitor(self, monitor_id):
        path = f"/api/v1/synthetic/monitors/{monitor_id}"
        return self._make_request(path)


def main():

    with open("config_customer.json", "r") as f:
        config = json.load(f)
    d = DynatraceAPI(config["dynatrace_base_url"], config["dynatrace_token"])

    from pprint import pformat

    # print(pformat(d.synthetic_monitor("HTTP_CHECK-4A8FA7A3BD1C6C64"), indent=2))

    for metric, details in d.metrics_series(
        "builtin:synthetic.browser.event.failure:names", date_from="now-5m"
    )["metrics"].items():
        for serie in details["series"]:
            print(serie)


if __name__ == "__main__":
    main()
