from __future__ import annotations

import argparse
import html
import json
import math
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio
from scripts.validate_dashboard import load_dashboard_config


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def load_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def select_time_window(
    records: list[dict[str, Any]], minutes: int, now: datetime | None = None
) -> list[dict[str, Any]]:
    end = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    start = end - timedelta(minutes=minutes)
    return [
        record
        for record in records
        if (timestamp := _parse_timestamp(record.get("ts"))) is not None
        and start <= timestamp <= end
    ]


def percentile(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil((p / 100) * len(ordered)))
    return float(ordered[rank - 1])


def _minute_buckets(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "requests": 0,
            "errors": 0,
            "latencies": [],
            "cost": 0.0,
            "tokens": 0,
            "quality": [],
        }
    )
    for record in records:
        timestamp = _parse_timestamp(record.get("ts"))
        if timestamp is None:
            continue
        key = timestamp.strftime("%H:%M")
        event = record.get("event")
        bucket = buckets[key]
        if event == "request_received":
            bucket["requests"] += 1
        elif event == "request_failed":
            bucket["errors"] += 1
        elif event == "response_sent":
            bucket["latencies"].append(float(record.get("latency_ms", 0) or 0))
            bucket["cost"] += float(record.get("cost_usd", 0) or 0)
            bucket["tokens"] += int(record.get("tokens_in", 0) or 0)
            bucket["tokens"] += int(record.get("tokens_out", 0) or 0)
            quality = record.get("quality_score")
            if isinstance(quality, (int, float)):
                bucket["quality"].append(float(quality))
    return [
        {"minute": minute, **values}
        for minute, values in sorted(buckets.items(), key=lambda item: item[0])
    ]


def aggregate_dashboard(records: list[dict[str, Any]]) -> dict[str, Any]:
    request_records = [record for record in records if record.get("event") == "request_received"]
    error_records = [record for record in records if record.get("event") == "request_failed"]
    response_records = [record for record in records if record.get("event") == "response_sent"]

    latencies = [float(record.get("latency_ms", 0) or 0) for record in response_records]
    costs = [float(record.get("cost_usd", 0) or 0) for record in response_records]
    tokens_in = [int(record.get("tokens_in", 0) or 0) for record in response_records]
    tokens_out = [int(record.get("tokens_out", 0) or 0) for record in response_records]
    qualities = [
        float(record["quality_score"])
        for record in response_records
        if isinstance(record.get("quality_score"), (int, float))
    ]
    error_breakdown = Counter(str(record.get("error_type") or "Unknown") for record in error_records)
    request_count = len(request_records)
    error_rate = (len(error_records) / request_count * 100) if request_count else 0.0

    return {
        "latency": {
            "p50": round(percentile(latencies, 50), 2),
            "p95": round(percentile(latencies, 95), 2),
            "p99": round(percentile(latencies, 99), 2),
        },
        "traffic": {"count": request_count, "rate_per_minute": round(request_count / 60, 2)},
        "errors": {
            "rate_pct": round(error_rate, 2),
            "count": len(error_records),
            "breakdown": dict(sorted(error_breakdown.items())),
        },
        "cost": {"total_usd": round(sum(costs), 6)},
        "tokens": {"input": sum(tokens_in), "output": sum(tokens_out)},
        "quality": {"mean": round(mean(qualities), 3) if qualities else 0.0},
        "series": _minute_buckets(records),
    }


def _status(value: float, operator: str, threshold: float) -> tuple[str, str]:
    healthy = value <= threshold if operator == "lte" else value >= threshold
    return ("healthy", "Trong ngưỡng") if healthy else ("breach", "Vượt ngưỡng")


def _sparkline(values: list[float], color: str) -> str:
    if not values:
        values = [0.0]
    low, high = min(values), max(values)
    spread = max(high - low, 1.0)
    denominator = max(len(values) - 1, 1)
    points = " ".join(
        f"{index * 260 / denominator:.1f},{58 - ((value - low) / spread * 46):.1f}"
        for index, value in enumerate(values)
    )
    return (
        '<svg class="spark" viewBox="0 0 260 64" role="img" aria-label="Xu hướng theo phút">'
        '<path d="M0 58 H260" stroke="#26324a" stroke-width="1" />'
        f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3" '
        'stroke-linecap="round" stroke-linejoin="round" /></svg>'
    )


def render_dashboard_html(
    metrics: dict[str, Any], contract: dict[str, Any], generated_at: datetime
) -> str:
    dashboard = contract["dashboard"]
    panels = {panel["id"]: panel for panel in dashboard["panels"]}
    series = metrics["series"]
    latency_values = [percentile(bucket["latencies"], 95) for bucket in series]
    traffic_values = [float(bucket["requests"]) for bucket in series]
    error_values = [float(bucket["errors"]) for bucket in series]
    cost_values = [float(bucket["cost"]) for bucket in series]
    token_values = [float(bucket["tokens"]) for bucket in series]
    quality_values = [mean(bucket["quality"]) if bucket["quality"] else 0.0 for bucket in series]

    def threshold_line(panel_id: str, value: float) -> str:
        threshold = panels[panel_id]["threshold"]
        css_class, label = _status(value, threshold["operator"], float(threshold["value"]))
        symbol = "≤" if threshold["operator"] == "lte" else "≥"
        return (
            f'<div class="threshold {css_class}"><span>{label}</span>'
            f'<span>SLO {symbol} {html.escape(str(threshold["value"]))} {html.escape(panels[panel_id]["unit"])}</span></div>'
        )

    breakdown = metrics["errors"]["breakdown"]
    breakdown_text = ", ".join(f"{html.escape(key)}: {value}" for key, value in breakdown.items()) or "Không có lỗi"
    cards = [
        (
            "Latency percentiles",
            "P95",
            f'{metrics["latency"]["p95"]:,.0f} ms',
            f'P50 {metrics["latency"]["p50"]:,.0f} · P99 {metrics["latency"]["p99"]:,.0f}',
            _sparkline(latency_values, "#59b5ff"),
            threshold_line("latency", metrics["latency"]["p95"]),
        ),
        (
            "Request traffic",
            "Requests",
            f'{metrics["traffic"]["count"]:,}',
            f'{metrics["traffic"]["rate_per_minute"]:.2f} requests/phút',
            _sparkline(traffic_values, "#7ae0c3"),
            threshold_line("traffic", metrics["traffic"]["rate_per_minute"]),
        ),
        (
            "Error rate & breakdown",
            "Error rate",
            f'{metrics["errors"]["rate_pct"]:.2f}%',
            breakdown_text,
            _sparkline(error_values, "#ff8095"),
            threshold_line("errors", metrics["errors"]["rate_pct"]),
        ),
        (
            "Cost over time",
            "Total cost",
            f'${metrics["cost"]["total_usd"]:.4f}',
            "Tổng trong cửa sổ 60 phút",
            _sparkline(cost_values, "#d0a5ff"),
            threshold_line("cost", metrics["cost"]["total_usd"]),
        ),
        (
            "Input & output tokens",
            "Total tokens",
            f'{metrics["tokens"]["input"] + metrics["tokens"]["output"]:,}',
            f'Input {metrics["tokens"]["input"]:,} · Output {metrics["tokens"]["output"]:,}',
            _sparkline(token_values, "#ffbf69"),
            threshold_line("tokens", metrics["tokens"]["input"] + metrics["tokens"]["output"]),
        ),
        (
            "Quality proxy",
            "Mean score",
            f'{metrics["quality"]["mean"]:.3f}',
            "Thang điểm 0–1",
            _sparkline(quality_values, "#8bd450"),
            threshold_line("quality", metrics["quality"]["mean"]),
        ),
    ]
    card_html = "".join(
        f'''<section class="card">
          <div class="card-title"><h2>{html.escape(title)}</h2><span>{html.escape(label)}</span></div>
          <div class="value">{html.escape(value)}</div>
          <div class="detail">{detail}</div>
          {sparkline}
          {threshold}
        </section>'''
        for title, label, value, detail, sparkline, threshold in cards
    )
    generated_text = generated_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return f'''<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="{dashboard["refresh_seconds"]}">
  <title>{html.escape(dashboard["title"])}</title>
  <style>
    :root {{ color-scheme: dark; --bg:#0a1020; --panel:#121b31; --line:#26324a; --text:#f5f7fb; --muted:#9cabc7; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:radial-gradient(circle at 85% -10%, #1c3b5e 0, transparent 36%), var(--bg); color:var(--text); font:15px/1.45 "Segoe UI", Arial, sans-serif; }}
    main {{ width:min(1440px, calc(100% - 56px)); margin:0 auto; padding:32px 0 40px; }}
    header {{ display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:24px; }}
    .eyebrow {{ color:#59b5ff; font-size:12px; font-weight:700; letter-spacing:.14em; text-transform:uppercase; }}
    h1 {{ margin:4px 0 2px; font-size:30px; letter-spacing:-.02em; }}
    header p, .meta {{ color:var(--muted); margin:0; }}
    .meta {{ text-align:right; font-size:13px; }}
    .grid {{ display:grid; grid-template-columns:repeat(3, 1fr); gap:18px; }}
    .card {{ min-height:290px; padding:22px; border:1px solid var(--line); border-radius:16px; background:linear-gradient(145deg, rgba(23,35,62,.98), rgba(15,23,42,.98)); box-shadow:0 18px 40px rgba(0,0,0,.18); }}
    .card-title {{ display:flex; justify-content:space-between; gap:12px; align-items:center; }}
    h2 {{ margin:0; font-size:16px; }}
    .card-title span {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.08em; }}
    .value {{ margin-top:18px; font-size:36px; line-height:1; font-weight:730; letter-spacing:-.03em; }}
    .detail {{ min-height:42px; margin-top:10px; color:var(--muted); font-size:13px; }}
    .spark {{ width:100%; height:64px; margin:12px 0 10px; overflow:visible; }}
    .threshold {{ display:flex; justify-content:space-between; gap:10px; border-radius:9px; padding:8px 10px; font-size:12px; font-weight:650; }}
    .threshold.healthy {{ color:#aaf0d9; background:rgba(36,160,120,.14); border:1px solid rgba(74,222,173,.25); }}
    .threshold.breach {{ color:#ffb3c0; background:rgba(214,64,94,.14); border:1px solid rgba(255,128,149,.28); }}
    footer {{ margin-top:18px; color:var(--muted); font-size:12px; display:flex; justify-content:space-between; }}
    @media (max-width:1000px) {{ .grid {{ grid-template-columns:repeat(2,1fr); }} }}
    @media (max-width:680px) {{ main {{ width:min(100% - 28px, 1440px); }} header {{ align-items:flex-start; flex-direction:column; gap:12px; }} .meta {{ text-align:left; }} .grid {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <main>
    <header>
      <div><div class="eyebrow">AI Operations · K4</div><h1>{html.escape(dashboard["title"])}</h1><p>Nguồn chuẩn: data/logs.jsonl</p></div>
      <div class="meta">Time range: 60 phút<br>Refresh: {dashboard["refresh_seconds"]} giây<br>{generated_text}</div>
    </header>
    <div class="grid">{card_html}</div>
    <footer><span>6/6 panel theo config/dashboard.yaml</span><span>Metrics → Traces → Logs</span></footer>
  </main>
</body>
</html>'''


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/seguisb.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def _draw_sparkline(
    draw: ImageDraw.ImageDraw,
    values: list[float],
    box: tuple[int, int, int, int],
    color: str,
) -> None:
    left, top, right, bottom = box
    draw.line((left, bottom, right, bottom), fill="#26324a", width=1)
    if not values:
        values = [0.0]
    low, high = min(values), max(values)
    spread = max(high - low, 1.0)
    denominator = max(len(values) - 1, 1)
    points = [
        (
            int(left + index * (right - left) / denominator),
            int(bottom - ((value - low) / spread * (bottom - top))),
        )
        for index, value in enumerate(values)
    ]
    if len(points) == 1:
        points.append((right, points[0][1]))
    draw.line(points, fill=color, width=4, joint="curve")


def render_dashboard_png(
    metrics: dict[str, Any], contract: dict[str, Any], generated_at: datetime, output: Path
) -> None:
    width, height = 1600, 980
    image = Image.new("RGB", (width, height), "#0a1020")
    draw = ImageDraw.Draw(image)
    draw.ellipse((1120, -420, 1860, 320), fill="#152e4a")

    title_font = _load_font(36, bold=True)
    eyebrow_font = _load_font(16, bold=True)
    body_font = _load_font(17)
    small_font = _load_font(14)
    card_title_font = _load_font(19, bold=True)
    value_font = _load_font(42, bold=True)
    label_font = _load_font(13, bold=True)

    dashboard = contract["dashboard"]
    panels = {panel["id"]: panel for panel in dashboard["panels"]}
    draw.text((70, 44), "AI OPERATIONS · K4", fill="#59b5ff", font=eyebrow_font)
    draw.text((70, 72), dashboard["title"], fill="#f5f7fb", font=title_font)
    draw.text((70, 124), "Nguồn chuẩn: data/logs.jsonl", fill="#9cabc7", font=body_font)
    generated_text = generated_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    meta = f"Time range: 60 phút\nRefresh: {dashboard['refresh_seconds']} giây\n{generated_text}"
    draw.multiline_text((1240, 64), meta, fill="#9cabc7", font=small_font, spacing=5, align="right")

    series = metrics["series"]
    latency_values = [percentile(bucket["latencies"], 95) for bucket in series]
    traffic_values = [float(bucket["requests"]) for bucket in series]
    error_values = [float(bucket["errors"]) for bucket in series]
    cost_values = [float(bucket["cost"]) for bucket in series]
    token_values = [float(bucket["tokens"]) for bucket in series]
    quality_values = [mean(bucket["quality"]) if bucket["quality"] else 0.0 for bucket in series]
    breakdown = metrics["errors"]["breakdown"]
    breakdown_text = ", ".join(f"{key}: {value}" for key, value in breakdown.items()) or "Không có lỗi"
    cards = [
        ("latency", "Latency percentiles", "P95", f'{metrics["latency"]["p95"]:,.0f} ms', f'P50 {metrics["latency"]["p50"]:,.0f} · P99 {metrics["latency"]["p99"]:,.0f}', latency_values, "#59b5ff", metrics["latency"]["p95"]),
        ("traffic", "Request traffic", "Requests", f'{metrics["traffic"]["count"]:,}', f'{metrics["traffic"]["rate_per_minute"]:.2f} requests/phút', traffic_values, "#7ae0c3", metrics["traffic"]["rate_per_minute"]),
        ("errors", "Error rate & breakdown", "Error rate", f'{metrics["errors"]["rate_pct"]:.2f}%', breakdown_text, error_values, "#ff8095", metrics["errors"]["rate_pct"]),
        ("cost", "Cost over time", "Total cost", f'${metrics["cost"]["total_usd"]:.4f}', "Tổng trong cửa sổ 60 phút", cost_values, "#d0a5ff", metrics["cost"]["total_usd"]),
        ("tokens", "Input & output tokens", "Total tokens", f'{metrics["tokens"]["input"] + metrics["tokens"]["output"]:,}', f'Input {metrics["tokens"]["input"]:,} · Output {metrics["tokens"]["output"]:,}', token_values, "#ffbf69", metrics["tokens"]["input"] + metrics["tokens"]["output"]),
        ("quality", "Quality proxy", "Mean score", f'{metrics["quality"]["mean"]:.3f}', "Thang điểm 0–1", quality_values, "#8bd450", metrics["quality"]["mean"]),
    ]

    card_width, card_height = 472, 336
    x_positions = [70, 564, 1058]
    y_positions = [186, 544]
    for index, (panel_id, title, label, value, detail, values, color, actual) in enumerate(cards):
        x = x_positions[index % 3]
        y = y_positions[index // 3]
        draw.rounded_rectangle(
            (x, y, x + card_width, y + card_height),
            radius=18,
            fill="#121b31",
            outline="#26324a",
            width=2,
        )
        draw.text((x + 24, y + 22), title, fill="#f5f7fb", font=card_title_font)
        label_width = draw.textlength(label.upper(), font=label_font)
        draw.text((x + card_width - 24 - label_width, y + 26), label.upper(), fill="#9cabc7", font=label_font)
        draw.text((x + 24, y + 70), value, fill="#f5f7fb", font=value_font)
        draw.text((x + 24, y + 126), detail, fill="#9cabc7", font=small_font)
        _draw_sparkline(draw, values, (x + 24, y + 178, x + card_width - 24, y + 236), color)

        threshold = panels[panel_id]["threshold"]
        css_class, status_label = _status(float(actual), threshold["operator"], float(threshold["value"]))
        symbol = "≤" if threshold["operator"] == "lte" else "≥"
        fill = "#173b36" if css_class == "healthy" else "#462434"
        text_color = "#aaf0d9" if css_class == "healthy" else "#ffb3c0"
        draw.rounded_rectangle((x + 24, y + 264, x + card_width - 24, y + 310), radius=9, fill=fill)
        draw.text((x + 38, y + 277), status_label, fill=text_color, font=label_font)
        slo_text = f"SLO {symbol} {threshold['value']} {panels[panel_id]['unit']}"
        slo_width = draw.textlength(slo_text, font=label_font)
        draw.text((x + card_width - 38 - slo_width, y + 277), slo_text, fill=text_color, font=label_font)

    draw.text((70, 930), "6/6 panel theo config/dashboard.yaml", fill="#9cabc7", font=small_font)
    footer_text = "Metrics → Traces → Logs"
    footer_width = draw.textlength(footer_text, font=small_font)
    draw.text((1530 - footer_width, 930), footer_text, fill="#9cabc7", font=small_font)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG", optimize=True)


def generate_outputs(args: argparse.Namespace) -> int:
    contract = load_dashboard_config(args.config)
    records = load_records(args.logs)
    minutes = int(contract["dashboard"]["time_range_minutes"])
    selected = select_time_window(records, minutes)
    metrics = aggregate_dashboard(selected)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc)
    args.output.write_text(
        render_dashboard_html(metrics, contract, generated_at), encoding="utf-8"
    )
    args.snapshot_json.write_text(
        json.dumps(
            {
                "generated_at": generated_at.isoformat(),
                "time_range_minutes": minutes,
                "records_in_window": len(selected),
                "metrics": metrics,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    render_dashboard_png(metrics, contract, generated_at, args.screenshot_png)
    print(f"Dashboard: {args.output}")
    print(f"Snapshot: {args.snapshot_json}")
    print(f"Screenshot: {args.screenshot_png}")
    print(f"Records in 60-minute window: {len(selected)}")
    return int(contract["dashboard"]["refresh_seconds"])


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Sinh dashboard HTML từ structured logs")
    parser.add_argument("--logs", type=Path, default=REPO_ROOT / "data" / "logs.jsonl")
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "config" / "dashboard.yaml")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "submission" / "evidence" / "dashboard.html",
    )
    parser.add_argument(
        "--snapshot-json",
        type=Path,
        default=REPO_ROOT / "submission" / "evidence" / "dashboard-metrics.json",
    )
    parser.add_argument(
        "--screenshot-png",
        type=Path,
        default=REPO_ROOT / "submission" / "evidence" / "dashboard.png",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Tái tạo output theo refresh_seconds; dừng bằng Ctrl+C.",
    )
    args = parser.parse_args()

    if args.watch:
        try:
            while True:
                refresh_seconds = generate_outputs(args)
                time.sleep(refresh_seconds)
        except KeyboardInterrupt:
            print("Đã dừng dashboard watch mode.")
            return 0

    generate_outputs(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
