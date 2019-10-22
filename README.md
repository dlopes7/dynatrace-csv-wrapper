# Dynatrace API Wrapper

This project was used for Banco BCI. It is used by Mainsoft, a partner from Chile.

This wrappers provides:

* A `customTime` parameter, which accepts values: `yesterday`
* A `timezone` parameter, which accepts timezone values like `America/Santiago`
* The result is a .csv file

Examples:

* `curl -i  http://localhost:5000/api/v1/timeseries/com.dynatrace.builtin:synthetic.httpmonitor.availability.percent\?customTime\=yesterday\&timezone\=America/Santiago\&entity\=HTTP_CHECK-7E8DEFA7C700159C,HTTP_CHECK-8DE0560C5527F25E`
* `curl -i  http://localhost:5000/api/v2/metrics/series/builtin:synthetic.browser.event.failure:names\?customTime\=yesterday\&timezone\=America/Santiago\&resolution\=5m\&scope\=entity\(SYNTHETIC_TEST_STEP-20AFFBA53B2A65C9\)`