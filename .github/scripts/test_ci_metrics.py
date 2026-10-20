import http.server
import importlib.util
import json
import os
import tempfile
import threading
import unittest
import urllib.parse

_spec = importlib.util.spec_from_file_location(
    "ci_metrics", os.path.join(os.path.dirname(__file__), "ci-metrics.py")
)
ci_metrics = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ci_metrics)

T0 = 1792536000


def _matrix(*series):
    return {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {"metric": metric, "values": [[T0 + 30 * i, v] for i, v in enumerate(values)]}
                for metric, values in series
            ],
        },
    }


# quay-quay restarted between two scrapes: up never reads 0, the start time moves.
STARTED = _matrix(({"instance": "quay-quay:9091"}, [str(T0), str(T0), str(T0 + 75), str(T0 + 75)]))
UP = _matrix(({"job": "quay-pushgateway", "instance": "quay-quay:9091"}, ["1", "1", "0", "0", "1"]))
# Counter reset at the restart: the series drops from 40 to 3. A final NaN must not become last.
CONNECTS = _matrix(
    ({"process_name": "registry"}, ["10", "40", "3", "8", "NaN"]),
    ({"process_name": "web"}, ["5", "6", "7"]),
)


class SummarizeTest(unittest.TestCase):
    def test_table_rows_and_gaps(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "queries"))
            for name, body in (
                ("up", UP),
                ("pushgateway_start_time", STARTED),
                ("db_connect_calls", CONNECTS),
            ):
                with open(os.path.join(d, "queries", f"{name}.json"), "w") as f:
                    json.dump(body, f)
            meta = {
                "window": {"start": str(T0), "end": str(T0 + 120), "step": "30s"},
                "scrape_interval": "30s",
                "quay_series": 12,
                "queries": {
                    "up": {"expr": "up", "series": 1},
                    "pushgateway_start_time": {"expr": "s", "series": 1},
                    "db_connect_calls": {"expr": "x", "series": 2},
                    "broken": {"expr": "y", "error": "HTTP 400: parse error"},
                },
                "errors": [],
            }
            with open(os.path.join(d, "meta.json"), "w") as f:
                json.dump(meta, f)

            ci_metrics.main(["summarize", "--in", d])

            with open(os.path.join(d, "summary.md")) as f:
                summary = f.read()

        self.assertIn("| up | 1 | 0 | 1 | 1 |", summary)
        self.assertIn("| db_connect_calls | 2 | 3 | 40 | 8 |", summary)
        self.assertIn("| broken | error: HTTP 400: parse error | | | |", summary)
        self.assertIn("- quay-quay:9091: 2026-10-20T22:41:00Z to 2026-10-20T22:41:30Z", summary)
        self.assertIn(
            "Pushgateway restarts: 1\n- quay-quay:9091: started 2026-10-20T22:41:15Z", summary
        )
        self.assertIn("Window 2026-10-20T22:40:00Z to 2026-10-20T22:42:00Z", summary)
        self.assertIn("12 quay_* series.", summary)
        self.assertNotIn("WARNING", summary)

    def _summarize_empty(self, quay_series, start=""):
        with tempfile.TemporaryDirectory() as d:
            meta = {
                "window": {"start": start, "end": str(T0), "step": "30s"},
                "quay_series": quay_series,
                "queries": {},
            }
            with open(os.path.join(d, "meta.json"), "w") as f:
                json.dump(meta, f)
            ci_metrics.main(["summarize", "--in", d])
            with open(os.path.join(d, "summary.md")) as f:
                return f.read()

    def test_zero_quay_series_is_loud(self):
        self.assertIn("WARNING: 0 quay_* series captured", self._summarize_empty(0))

    def test_unknown_quay_series_does_not_blame_quay(self):
        summary = self._summarize_empty(None)
        self.assertIn("WARNING: quay_* series count unknown", summary)
        self.assertNotIn("pushed no metrics", summary)
        self.assertIn("Window unknown to 2026-10-20T22:40:00Z", summary)

    def test_rfc3339_window_is_kept(self):
        summary = self._summarize_empty(1, start="2026-10-20T22:38:00Z")
        self.assertIn("Window 2026-10-20T22:38:00Z to 2026-10-20T22:40:00Z", summary)

    def test_trailing_up_gap(self):
        result = _matrix(({"instance": "a"}, ["1", "0", "0"]))["data"]["result"]
        self.assertEqual(
            ci_metrics.up_gaps(result), [{"instance": "a", "start": T0 + 30, "end": T0 + 60}]
        )


class _StubPrometheus(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(url.query)
        if url.path == "/api/v1/status/config":
            body = {"data": {"yaml": "global:\n  scrape_interval: 30s\n  scrape_timeout: 10s\n"}}
        elif url.path == "/api/v1/series":
            body = {"data": [{"__name__": "quay_a"}, {"__name__": "quay_b"}]}
        elif params["query"] == ["up"]:
            body = UP
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "error": "bad expr"}).encode())
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def log_message(self, *args):
        pass


class ExportTest(unittest.TestCase):
    def test_writes_files_and_records_failed_query(self):
        server = http.server.HTTPServer(("127.0.0.1", 0), _StubPrometheus)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        with tempfile.TemporaryDirectory() as d:
            queries = os.path.join(d, "queries.json")
            with open(queries, "w") as f:
                json.dump([{"name": "broken", "expr": "nope("}, {"name": "up", "expr": "up"}], f)
            out = os.path.join(d, "out")

            ci_metrics.main(
                [
                    "export",
                    "--prom-url",
                    f"http://127.0.0.1:{server.server_port}",
                    "--start",
                    str(T0),
                    "--end",
                    str(T0 + 120),
                    "--queries",
                    queries,
                    "--out",
                    out,
                ]
            )

            with open(os.path.join(out, "meta.json")) as f:
                meta = json.load(f)
            with open(os.path.join(out, "queries", "up.json")) as f:
                self.assertEqual(json.load(f), UP)
            self.assertFalse(os.path.exists(os.path.join(out, "queries", "broken.json")))

        self.assertEqual(meta["queries"]["broken"]["error"], "HTTP 400: bad expr")
        self.assertEqual(meta["queries"]["up"]["series"], 1)
        self.assertEqual(meta["quay_series"], 2)
        self.assertEqual(meta["scrape_interval"], "30s")
        self.assertEqual(
            meta["up_gaps"], [{"instance": "quay-quay:9091", "start": T0 + 60, "end": T0 + 90}]
        )


if __name__ == "__main__":
    unittest.main()
