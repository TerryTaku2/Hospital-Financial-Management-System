// Minimal inline-SVG chart helpers — no chart library, matches the rest of
// this app (plain HTML/CSS/JS, no build step). Two chart types:
//   renderAreaChart  — single-series trend over time, with hover crosshair
//   renderBarChart   — horizontal magnitude comparison, with hover + direct labels

const CHART_NS = "http://www.w3.org/2000/svg";

function _svgEl(tag, attrs) {
  const el = document.createElementNS(CHART_NS, tag);
  for (const key in attrs) el.setAttribute(key, attrs[key]);
  return el;
}

function _compactMoney(n) {
  const abs = Math.abs(n);
  if (abs >= 1000) return (n / 1000).toLocaleString(undefined, { maximumFractionDigits: 1 }) + "k";
  return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

// "Nice" axis max: rounds up to a clean step so gridlines read as round numbers.
function _niceMax(rawMax) {
  if (rawMax <= 0) return 10;
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawMax)));
  const norm = rawMax / magnitude;
  let step;
  if (norm <= 1) step = 1;
  else if (norm <= 2) step = 2;
  else if (norm <= 5) step = 5;
  else step = 10;
  return step * magnitude;
}

function _ensureTooltip() {
  let tip = document.getElementById("chart-tooltip");
  if (!tip) {
    tip = document.createElement("div");
    tip.id = "chart-tooltip";
    tip.className = "chart-tooltip";
    tip.hidden = true;
    document.body.appendChild(tip);
  }
  return tip;
}

function _showTooltip(evt, html) {
  const tip = _ensureTooltip();
  tip.innerHTML = html;
  tip.hidden = false;
  const pad = 12;
  tip.style.left = evt.clientX + pad + "px";
  tip.style.top = evt.clientY + pad + "px";
}

function _hideTooltip() {
  const tip = document.getElementById("chart-tooltip");
  if (tip) tip.hidden = true;
}

const SHORT_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
function _shortDate(isoDate) {
  const [y, m, d] = isoDate.split("-").map(Number);
  return `${SHORT_MONTHS[m - 1]} ${d}`;
}

/**
 * points: [{ period: "YYYY-MM-DD", revenue: number }], ascending by date.
 */
function renderAreaChart(container, points, { currency = "USD" } = {}) {
  container.innerHTML = "";
  if (!points || points.length === 0) {
    container.innerHTML = `<div class="chart-empty">No revenue posted in this period yet.</div>`;
    return;
  }

  const W = 640, H = 220;
  const marginLeft = 46, marginRight = 12, marginTop = 12, marginBottom = 26;
  const plotW = W - marginLeft - marginRight;
  const plotH = H - marginTop - marginBottom;

  const values = points.map((p) => Number(p.revenue));
  const maxVal = _niceMax(Math.max(...values, 0));
  const n = points.length;

  const xAt = (i) => marginLeft + (n === 1 ? plotW / 2 : (i / (n - 1)) * plotW);
  const yAt = (v) => marginTop + plotH - (v / maxVal) * plotH;

  const svg = _svgEl("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart-svg", role: "img" });

  // Gridlines + y-axis labels (4 steps).
  const steps = 4;
  for (let s = 0; s <= steps; s++) {
    const v = (maxVal / steps) * s;
    const y = yAt(v);
    svg.appendChild(_svgEl("line", { x1: marginLeft, x2: W - marginRight, y1: y, y2: y, class: "chart-gridline" }));
    const label = _svgEl("text", { x: marginLeft - 8, y: y + 4, class: "chart-axis-label", "text-anchor": "end" });
    label.textContent = _compactMoney(v);
    svg.appendChild(label);
  }

  // X-axis: ~6 evenly spaced date labels.
  const labelCount = Math.min(6, n);
  for (let i = 0; i < labelCount; i++) {
    const idx = labelCount === 1 ? 0 : Math.round((i / (labelCount - 1)) * (n - 1));
    const label = _svgEl("text", { x: xAt(idx), y: H - 6, class: "chart-axis-label", "text-anchor": "middle" });
    label.textContent = _shortDate(points[idx].period);
    svg.appendChild(label);
  }

  // Area fill + line.
  const linePath = points.map((p, i) => `${i === 0 ? "M" : "L"}${xAt(i)},${yAt(Number(p.revenue))}`).join(" ");
  const areaPath = `${linePath} L${xAt(n - 1)},${yAt(0)} L${xAt(0)},${yAt(0)} Z`;
  svg.appendChild(_svgEl("path", { d: areaPath, class: "chart-area" }));
  svg.appendChild(_svgEl("path", { d: linePath, class: "chart-line" }));

  // End marker on the line itself, direct label pinned to a fixed corner
  // (not the line's own y — a noisy series would collide with itself).
  const lastX = xAt(n - 1), lastY = yAt(values[n - 1]);
  svg.appendChild(_svgEl("circle", { cx: lastX, cy: lastY, r: 5, class: "chart-end-dot" }));
  const endLabel = _svgEl("text", {
    x: W - marginRight, y: marginTop + 12, class: "chart-end-label", "text-anchor": "end",
  });
  endLabel.textContent = `Latest: ${formatMoney(values[n - 1], currency)}`;
  svg.appendChild(endLabel);

  // Hover crosshair — one invisible full-height hit column per point.
  const colW = plotW / n;
  points.forEach((p, i) => {
    const hit = _svgEl("rect", {
      x: marginLeft + i * colW, y: marginTop, width: Math.max(colW, 1), height: plotH,
      fill: "transparent", class: "chart-hit",
    });
    hit.addEventListener("mousemove", (evt) => {
      svg.querySelectorAll(".chart-crosshair").forEach((el) => el.remove());
      const cx = xAt(i), cy = yAt(Number(p.revenue));
      const crosshair = _svgEl("line", { x1: cx, x2: cx, y1: marginTop, y2: marginTop + plotH, class: "chart-crosshair" });
      svg.appendChild(crosshair);
      const dot = _svgEl("circle", { cx, cy, r: 4, class: "chart-crosshair-dot" });
      dot.classList.add("chart-crosshair");
      svg.appendChild(dot);
      _showTooltip(evt, `<strong>${_shortDate(p.period)}</strong><br>${formatMoney(p.revenue, currency)}`);
    });
    hit.addEventListener("mouseleave", () => {
      svg.querySelectorAll(".chart-crosshair").forEach((el) => el.remove());
      _hideTooltip();
    });
    svg.appendChild(hit);
  });

  container.appendChild(svg);
}

/**
 * rows: [{ label: string, value: number }], any order — rendered as given.
 * colorSteps: optional array of hex colors, one per row (e.g. an ordinal
 * ramp for AR aging buckets); defaults to a single flat brand hue.
 */
function renderBarChart(container, rows, { currency = "USD", colorSteps = null } = {}) {
  container.innerHTML = "";
  if (!rows || rows.length === 0 || rows.every((r) => Number(r.value) === 0)) {
    container.innerHTML = `<div class="chart-empty">No data yet.</div>`;
    return;
  }

  const rowH = 34, barH = 18;
  const marginLeft = 130, marginRight = 70, marginTop = 4, marginBottom = 4;
  const W = 560;
  const H = marginTop + marginBottom + rows.length * rowH;
  const plotW = W - marginLeft - marginRight;

  const maxVal = _niceMax(Math.max(...rows.map((r) => Number(r.value)), 0));
  const xAt = (v) => (v / maxVal) * plotW;

  const svg = _svgEl("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart-svg", role: "img" });

  rows.forEach((row, i) => {
    const value = Number(row.value);
    const y = marginTop + i * rowH;
    const barW = Math.max(xAt(value), value > 0 ? 3 : 0);
    const color = colorSteps ? colorSteps[i % colorSteps.length] : "var(--chart-series-1)";

    const label = _svgEl("text", { x: marginLeft - 10, y: y + barH / 2 + 4, class: "chart-bar-label", "text-anchor": "end" });
    label.textContent = row.label;
    svg.appendChild(label);

    const track = _svgEl("rect", {
      x: marginLeft, y, width: plotW, height: barH, rx: 4, class: "chart-bar-track",
    });
    svg.appendChild(track);

    const bar = _svgEl("rect", {
      x: marginLeft, y, width: barW, height: barH, rx: 4, fill: color, class: "chart-bar",
    });
    svg.appendChild(bar);

    const valueLabel = _svgEl("text", { x: marginLeft + barW + 8, y: y + barH / 2 + 4, class: "chart-bar-value" });
    valueLabel.textContent = formatMoney(value, currency);
    svg.appendChild(valueLabel);

    const hit = _svgEl("rect", { x: marginLeft, y, width: plotW, height: barH, fill: "transparent", class: "chart-hit" });
    hit.addEventListener("mousemove", (evt) => {
      bar.classList.add("chart-bar-hover");
      _showTooltip(evt, `<strong>${escapeHtml(row.label)}</strong><br>${formatMoney(value, currency)}`);
    });
    hit.addEventListener("mouseleave", () => {
      bar.classList.remove("chart-bar-hover");
      _hideTooltip();
    });
    svg.appendChild(hit);
  });

  container.appendChild(svg);
}
