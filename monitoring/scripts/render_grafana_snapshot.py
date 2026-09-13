#!/usr/bin/env python3
"""Create a self-contained interactive snapshot of a Grafana dashboard."""

from __future__ import print_function

import argparse
import json
import os
import re
import time
from html import escape
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def fetch_json(url, token=None):
    request = Request(url)
    if token:
        request.add_header("Authorization", "Bearer {0}".format(token))
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_time(value, now):
    if value == "now":
        return now
    match = re.match(r"^now-(\d+)([smhdw])$", value)
    if not match:
        return float(value)
    amount = int(match.group(1))
    seconds = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    return now - amount * seconds[match.group(2)]


def query_prometheus(base_url, expression, start, end, step, instant):
    endpoint = base_url.rstrip("/") + "/api/v1/query"
    params = {"query": expression}
    if not instant:
        endpoint = base_url.rstrip("/") + "/api/v1/query_range"
        params.update({"start": start, "end": end, "step": step})
    url = endpoint + "?" + urlencode(params)
    try:
        payload = fetch_json(url)
        if payload.get("status") != "success":
            return {"error": payload.get("error", "Prometheus query failed")}
        return {"resultType": payload["data"]["resultType"], "result": payload["data"]["result"]}
    except (HTTPError, URLError, ValueError) as error:
        return {"error": str(error)}


def collect_panels(panels, prometheus_url, start, end, step):
    collected = []
    for panel in panels:
        if panel.get("panels"):
            collected.extend(collect_panels(panel["panels"], prometheus_url, start, end, step))
        targets = []
        for target in panel.get("targets", []):
            expression = target.get("expr")
            if not expression:
                continue
            expression = expression.replace("$__interval", "1m")
            expression = expression.replace("$__rate_interval", "5m")
            if "${" in expression or "$node" in expression:
                targets.append({"refId": target.get("refId", "A"), "error": "Unresolved dashboard variable"})
                continue
            instant = bool(target.get("instant")) or panel.get("type") in ("stat", "gauge", "bargauge", "table")
            result = query_prometheus(prometheus_url, expression, start, end, step, instant)
            result["refId"] = target.get("refId", "A")
            result["legendFormat"] = target.get("legendFormat", "")
            targets.append(result)
        if targets or panel.get("type") == "row":
            collected.append({
                "id": panel.get("id"),
                "title": panel.get("title", ""),
                "type": panel.get("type", "text"),
                "description": panel.get("description", ""),
                "gridPos": panel.get("gridPos", {}),
                "targets": targets,
            })
    return collected


HTML_TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__TITLE__</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    :root { color-scheme: dark; }
    body { margin: 0; padding: 24px; background: #111217; color: #d8d9da; font: 14px system-ui, sans-serif; }
    h1 { margin: 0 0 4px; font-size: 24px; }
    .meta { color: #8d8f99; margin-bottom: 20px; }
    .grid { display: grid; grid-template-columns: repeat(24, minmax(0, 1fr)); gap: 12px; }
    .panel { grid-column: span 12; min-height: 260px; padding: 12px; border: 1px solid #2b2d36; border-radius: 6px; background: #181a20; overflow: hidden; }
    .panel.wide { grid-column: span 24; }
    .panel h2 { margin: 0 0 6px; font-size: 16px; }
    .panel p { margin: 0 0 8px; color: #8d8f99; }
    .chart { width: 100%; height: 240px; }
    .stat { display: flex; align-items: center; justify-content: center; height: 220px; font-size: 48px; font-weight: 600; }
    .table { width: 100%; border-collapse: collapse; }
    .table th, .table td { padding: 7px; border-bottom: 1px solid #2b2d36; text-align: left; }
    .error { color: #ff6b6b; white-space: pre-wrap; }
    @media (max-width: 900px) { .panel, .panel.wide { grid-column: span 24; } }
  </style>
</head>
<body>
  <h1>__TITLE__</h1>
  <div class="meta">Snapshot: __GENERATED__ · Range: __FROM__ to __TO__</div>
  <div id="dashboard" class="grid"></div>
  <script>
    const snapshot = __SNAPSHOT__;
    const root = document.getElementById('dashboard');

    function labelFor(metric, format) {
      if (format) {
        return format.replace(/\{\{([^}]+)\}\}/g, function (_, key) {
          return metric[key.trim()] || key.trim();
        });
      }
      const values = Object.keys(metric).filter(k => k !== '__name__').map(k => k + '=' + metric[k]);
      return values.join(', ') || metric.__name__ || 'value';
    }

    function valuesFor(result) {
      if (!result || !result.result) return [];
      return result.result;
    }

    function lastValue(result) {
      const rows = valuesFor(result);
      if (!rows.length) return null;
      if (result.resultType === 'matrix') return rows[0].values[rows[0].values.length - 1][1];
      return rows[0].value ? rows[0].value[1] : null;
    }

    function tablePanel(panel, targetResults) {
      const rows = [];
      targetResults.forEach(result => {
        valuesFor(result).forEach(item => {
          const value = item.value ? item.value[1] : (item.values ? item.values[item.values.length - 1][1] : '');
          const metric = item.metric || {};
          rows.push('<tr><td>' + escapeHtml(labelFor(metric, result.legendFormat)) + '</td><td>' + escapeHtml(value) + '</td></tr>');
        });
      });
      return '<table class="table"><thead><tr><th>Series</th><th>Value</th></tr></thead><tbody>' + rows.join('') + '</tbody></table>';
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, function (c) {
        return {'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c];
      });
    }

    function renderTimeseries(element, results) {
      const traces = [];
      results.forEach(result => {
        valuesFor(result).forEach(item => {
          const values = item.values || [];
          traces.push({
            x: values.map(v => new Date(Number(v[0]) * 1000)),
            y: values.map(v => Number(v[1])),
            mode: 'lines',
            name: labelFor(item.metric || {}, result.legendFormat),
            connectgaps: false
          });
        });
      });
      Plotly.newPlot(element, traces, {
        paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
        font: {color: '#d8d9da'}, margin: {l: 48, r: 16, t: 8, b: 36},
        xaxis: {gridcolor: '#2b2d36'}, yaxis: {gridcolor: '#2b2d36'}
      }, {responsive: true, displaylogo: false});
    }

    snapshot.panels.forEach((panel, index) => {
      const element = document.createElement('section');
      element.className = 'panel' + (panel.gridPos && panel.gridPos.w >= 18 ? ' wide' : '');
      const heading = document.createElement('h2');
      heading.textContent = panel.title || 'Panel ' + (index + 1);
      element.appendChild(heading);
      if (panel.description) {
        const description = document.createElement('p');
        description.textContent = panel.description;
        element.appendChild(description);
      }
      const errors = panel.targets.filter(t => t.error);
      if (errors.length) {
        element.innerHTML += '<div class="error">' + escapeHtml(errors.map(t => t.error).join('\n')) + '</div>';
      } else if (panel.type === 'row') {
        element.className = 'panel wide';
        element.style.minHeight = 'auto';
      } else if (panel.type === 'table') {
        element.innerHTML += tablePanel(panel, panel.targets);
      } else if (panel.type === 'stat' || panel.type === 'gauge' || panel.type === 'bargauge') {
        const values = panel.targets.map(lastValue).filter(v => v !== null);
        element.innerHTML += '<div class="stat">' + escapeHtml(values.length ? values.join(' / ') : 'No data') + '</div>';
      } else {
        const chart = document.createElement('div');
        chart.className = 'chart';
        element.appendChild(chart);
        renderTimeseries(chart, panel.targets);
      }
      root.appendChild(element);
    });
  </script>
</body>
</html>'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--grafana-url", default=os.environ.get("GRAFANA_URL", "http://localhost:3000"))
    parser.add_argument("--prometheus-url", default=os.environ.get("PROMETHEUS_URL", "http://localhost:9090"))
    parser.add_argument("--dashboard-uid", default="cluster-health-overview")
    parser.add_argument("--from-time", default="now-3h")
    parser.add_argument("--to-time", default="now")
    parser.add_argument("--step", default="60s")
    args = parser.parse_args()

    token = os.environ.get("GRAFANA_TOKEN")
    if not token:
        parser.error("GRAFANA_TOKEN is not set")

    dashboard_url = args.grafana_url.rstrip("/") + "/api/dashboards/uid/" + args.dashboard_uid
    payload = fetch_json(dashboard_url, token)
    dashboard = payload.get("dashboard") or payload.get("data", {}).get("dashboard")
    if not dashboard:
        parser.error("Grafana response does not contain a dashboard")

    now = time.time()
    start = parse_time(args.from_time, now)
    end = parse_time(args.to_time, now)
    panels = collect_panels(dashboard.get("panels", []), args.prometheus_url, start, end, args.step)
    snapshot = {
        "title": dashboard.get("title", "Grafana snapshot"),
        "generated": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(now)),
        "from": args.from_time,
        "to": args.to_time,
        "panels": panels,
    }
    document = HTML_TEMPLATE.replace("__TITLE__", escape(snapshot["title"]))
    document = document.replace("__GENERATED__", escape(snapshot["generated"]))
    document = document.replace("__FROM__", escape(snapshot["from"]))
    document = document.replace("__TO__", escape(snapshot["to"]))
    document = document.replace("__SNAPSHOT__", json.dumps(snapshot).replace("<", "\\u003c"))
    output_dir = os.path.dirname(os.path.abspath(args.output))
    os.makedirs(output_dir, exist_ok=True)
    with open(args.output, "w") as output_file:
        output_file.write(document)


if __name__ == "__main__":
    main()
