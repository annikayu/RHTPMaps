# ── map.py ────────────────────────────────────────────────────────────────────
# Build the interactive folium housing needs map.

import folium
import branca.colormap as cm
import geopandas as gpd
import pandas as pd

from config import (
    HOSPITAL_NAME, HOSPITAL_LAT, HOSPITAL_LON,
    AFFORD_THRESHOLD, CNA_AFFORD_THRESHOLD,
    RING_COLORS, COLOR_NO_DATA,
    RENT_GRADIENT, VACANCY_GRADIENT, BURDEN_GRADIENT,
    POP_DENSITY_GRADIENT, HOUSING_DENSITY_GRADIENT,
    OUTPUT_HTML,
)

RING_DASH = "8 4"


# ── Colormap builders ─────────────────────────────────────────────────────────

def _rent_cmap(gdf, threshold, gradient):
    valid = gdf["median_rent"].dropna()
    min_v = max(0.0, float(valid.min()) if len(valid) else 0)
    max_v = max(threshold * 1.1, float(valid.max()) if len(valid) else threshold * 1.1)
    return cm.LinearColormap(
        colors=gradient,
        index=[
            min_v,
            min_v + (threshold - min_v) * 0.4,
            threshold * 0.85,
            threshold,
            max_v,
        ],
        vmin=min_v, vmax=max_v,
        caption=f"Median Gross Rent  |  Threshold: ${threshold:,.0f}/mo",
    )


def _simple_cmap(gdf, col, colors, caption, cap_pct=0.95):
    valid = gdf[col].dropna()
    if len(valid) == 0:
        return cm.LinearColormap(colors=colors, vmin=0, vmax=100, caption=caption)
    return cm.LinearColormap(
        colors=colors,
        vmin=float(valid.min()),
        vmax=float(valid.quantile(cap_pct)),
        caption=caption,
    )


def _color(val, colormap):
    return COLOR_NO_DATA if pd.isna(val) else colormap(float(val))


# ── Generic choropleth FeatureGroup ──────────────────────────────────────────

def _choropleth_group(gdf, col, colormap, layer_name, tip_label,
                      tip_fmt="{:.1f}%", show=False):
    group = folium.FeatureGroup(name=layer_name, show=show)

    color_lut = {row["GEOID"]: _color(row[col], colormap)
                 for _, row in gdf[["GEOID", col]].iterrows()}

    name_col = "NAME" if "NAME" in gdf.columns else ("NAME_y" if "NAME_y" in gdf.columns else "GEOID")
    plot = gdf[["GEOID", name_col, col, "drive_minutes", "geometry"]].copy()
    plot = plot.rename(columns={name_col: "_name"})
    plot["_val"]   = plot[col].apply(lambda v: tip_fmt.format(v) if pd.notna(v) else "No data")
    plot["_drive"] = plot["drive_minutes"].apply(lambda m: f"{int(m)} min")

    folium.GeoJson(
        data=plot,
        style_function=lambda f, lut=color_lut: {
            "fillColor": lut.get(f["properties"]["GEOID"], COLOR_NO_DATA),
            "color": "#cccccc", "weight": 0.4, "fillOpacity": 0.75,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["_name", "_val", "_drive"],
            aliases=["Tract:", tip_label + ":", "Drive time:"],
            localize=True,
        ),
    ).add_to(group)
    return group


# ── Rent affordability choropleth (with custom tooltip) ───────────────────────

def _rent_choropleth(gdf, colormap, afford_threshold, afford_col,
                     layer_name, role_label, salary, show=False):
    group = folium.FeatureGroup(name=layer_name, show=show)

    color_lut = {row["GEOID"]: _color(row["median_rent"], colormap)
                 for _, row in gdf[["GEOID", "median_rent"]].iterrows()}

    name_col = "NAME" if "NAME" in gdf.columns else ("NAME_y" if "NAME_y" in gdf.columns else "GEOID")
    plot = gdf[["GEOID", name_col, "median_rent", afford_col, "drive_minutes", "geometry"]].copy()
    plot = plot.rename(columns={name_col: "_name"})
    plot["_rent"]      = plot["median_rent"].apply(lambda r: f"${r:,.0f}/mo" if pd.notna(r) else "No data")
    plot["_afford"]    = plot[afford_col].apply(
        lambda a: "Yes ✓" if a is True else ("No ✗" if a is False else "No data"))
    plot["_threshold"] = f"${afford_threshold:,.0f}/mo"
    plot["_drive"]     = plot["drive_minutes"].apply(lambda m: f"{int(m)} min")

    folium.GeoJson(
        data=plot,
        style_function=lambda f, lut=color_lut: {
            "fillColor": lut.get(f["properties"]["GEOID"], COLOR_NO_DATA),
            "color": "#cccccc", "weight": 0.4, "fillOpacity": 0.75,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["_name", "_rent", "_afford", "_threshold", "_drive"],
            aliases=["Tract:", "Median rent:", f"Affordable ({role_label}):", "Threshold:", "Drive time:"],
            localize=True,
        ),
    ).add_to(group)
    return group


# ── Legend HTML ───────────────────────────────────────────────────────────────

def _legend_html() -> str:
    def swatch(colors, left, right, title):
        stops = ", ".join(colors)
        return f"""
        <div style="margin-bottom:10px;">
          <b style="font-size:12px;">{title}</b><br>
          <div style="height:11px;background:linear-gradient(to right,{stops});
               border-radius:3px;border:1px solid #ccc;margin:3px 0;"></div>
          <div style="display:flex;justify-content:space-between;font-size:10px;color:#666;">
            <span>{left}</span><span>{right}</span>
          </div>
        </div>"""

    ring_entries = "".join(
        f'<span style="color:{RING_COLORS[m]};font-weight:bold;">&#9135;&#9135;</span>&nbsp;{m}min&nbsp;'
        for m in sorted(RING_COLORS)
    )

    return f"""
    <div style="
        position:fixed; bottom:30px; right:30px; z-index:1000;
        background:white; padding:14px 18px;
        border-radius:8px; border:1px solid #ddd;
        font-family:Arial,sans-serif; font-size:12px;
        box-shadow:2px 2px 8px rgba(0,0,0,0.2);
        min-width:245px; max-height:88vh; overflow-y:auto; line-height:1.7;
    ">
      <b style="font-size:13px;">Housing Needs Map</b><br>
      <span style="font-size:10px;color:#888;">Nor-Lea Hospital · Lovington NM</span>
      <hr style="margin:8px 0;border:none;border-top:1px solid #eee;">

      {swatch(RENT_GRADIENT,
          "Low rent (affordable)", f"High rent (≥ threshold)",
          "&#x25A0; Median Gross Rent")}

      {swatch(VACANCY_GRADIENT,
          "Low vacancy (tight)", "High vacancy (available)",
          "&#x25A0; Vacancy Rate")}

      {swatch(BURDEN_GRADIENT,
          "Low cost burden", "High cost burden",
          "&#x25A0; % Renters Cost-Burdened (≥30%)")}

      {swatch(POP_DENSITY_GRADIENT,
          "Low density", "High density",
          "&#x25A0; Population Density")}

      {swatch(HOUSING_DENSITY_GRADIENT,
          "Low density", "High density",
          "&#x25A0; Housing Unit Density")}

      <hr style="margin:8px 0;border:none;border-top:1px solid #eee;">
      <b style="font-size:12px;">Drive-time rings</b><br>
      {ring_entries}<br><br>
      <span style="display:inline-block;width:12px;height:12px;
        background:{COLOR_NO_DATA};border-radius:2px;
        vertical-align:middle;margin-right:4px;"></span>No data
    </div>
    """


# ── Summary stats panel (collapsible) ────────────────────────────────────────

def _summary_panel_html(stats: list) -> str:
    """
    Collapsible panel showing affordability stats per drive band.
    stats: list of dicts with keys: minutes, rn_pct, cna_pct, avg_vac, avg_burden, n_tracts
    """
    def bar(pct, color):
        if pct is None:
            return '<span style="color:#aaa;font-size:10px;">N/A</span>'
        w = max(0, min(100, pct))
        return (
            f'<div style="display:flex;align-items:center;gap:4px;">'
            f'<div style="width:60px;background:#eee;border-radius:3px;height:8px;">'
            f'<div style="width:{w:.0f}%;background:{color};border-radius:3px;height:8px;"></div>'
            f'</div>'
            f'<span style="font-size:11px;">{pct:.0f}%</span>'
            f'</div>'
        )

    rows = ""
    for s in stats:
        m = s["minutes"]
        ring_color = RING_COLORS.get(m, "#888")
        rows += f"""
        <tr style="border-bottom:1px solid #f0f0f0;">
          <td style="padding:5px 4px;font-weight:bold;white-space:nowrap;">
            <span style="color:{ring_color};">&#9679;</span>&nbsp;{m} min
            <br><span style="font-size:9px;color:#aaa;">{s['n_tracts']} tracts</span>
          </td>
          <td style="padding:5px 4px;">{bar(s['rn_pct'],  '#27ae60')}</td>
          <td style="padding:5px 4px;">{bar(s['cna_pct'], '#e67e22')}</td>
          <td style="padding:5px 4px;font-size:11px;color:#555;">
            {f"{s['avg_vac']:.1f}%" if s['avg_vac'] is not None else "—"}
          </td>
          <td style="padding:5px 4px;font-size:11px;color:#555;">
            {f"{s['avg_burden']:.1f}%" if s['avg_burden'] is not None else "—"}
          </td>
        </tr>"""

    return f"""
    <div id="stats-panel" style="
        position:fixed; top:300px; left:10px; z-index:1000;
        background:white; border-radius:8px; border:1px solid #ddd;
        font-family:Arial,sans-serif; font-size:12px;
        box-shadow:2px 2px 8px rgba(0,0,0,0.2);
        width:310px;
    ">
      <div id="stats-header" onclick="toggleStats()"
           style="padding:10px 14px;cursor:pointer;
                  border-radius:8px 8px 0 0;background:#f8f8f8;
                  border-bottom:1px solid #eee;
                  display:flex;justify-content:space-between;align-items:center;">
        <b style="font-size:12px;">&#x25CF; Affordability Summary</b>
        <span id="stats-arrow" style="font-size:14px;color:#888;">&#x25BC;</span>
      </div>
      <div id="stats-body" style="padding:8px 12px 12px;display:none;overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;font-size:11px;table-layout:fixed;">
          <thead>
            <tr style="color:#888;font-size:10px;text-transform:uppercase;border-bottom:2px solid #eee;">
              <th style="padding:4px;text-align:left;">Band</th>
              <th style="padding:4px;text-align:left;">RN ≤$2,208</th>
              <th style="padding:4px;text-align:left;">CNA ≤$950</th>
              <th style="padding:4px;text-align:left;">Vac.</th>
              <th style="padding:4px;text-align:left;">Burden</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
        <div style="font-size:9px;color:#aaa;margin-top:6px;">
          % = tracts w/ rent data where median rent ≤ threshold
        </div>
      </div>
    </div>
    <script>
    function toggleStats() {{
        var body  = document.getElementById('stats-body');
        var arrow = document.getElementById('stats-arrow');
        if (body.style.display === 'none') {{
            body.style.display = 'block';
            arrow.innerHTML = '&#x25B2;';
        }} else {{
            body.style.display = 'none';
            arrow.innerHTML = '&#x25BC;';
        }}
    }}
    </script>
    """


# ── Left panel: income band toggle ───────────────────────────────────────────

def _income_panel_html(map_var: str) -> str:
    """
    Left-side panel with radio buttons to switch between RN and CNA
    affordability views. Uses JavaScript to toggle the correct layer
    control checkboxes by matching their label text.
    """
    rn_label  = "Median Rent — RN ($88,260/yr)"
    cna_label = "Median Rent — CNA ($38,000/yr)"

    return f"""
    <div id="income-panel" style="
        position:fixed; top:80px; left:10px; z-index:1000;
        background:white; padding:14px 16px;
        border-radius:8px; border:1px solid #ddd;
        font-family:Arial,sans-serif; font-size:13px;
        box-shadow:2px 2px 8px rgba(0,0,0,0.2);
        min-width:190px; line-height:1.5;
    ">
      <b style="font-size:13px;">Worker Type</b><br>
      <span style="font-size:10px;color:#888;">Affordability threshold<br>(30% of gross income)</span>
      <hr style="margin:8px 0;border:none;border-top:1px solid #eee;">

      <label style="cursor:pointer;display:block;">
        <input type="radio" name="income_band" value="rn"
               onchange="switchBand('rn')" checked>
        &nbsp;<b>RN</b> — $88,260/yr<br>
        <span style="font-size:10px;color:#555;margin-left:20px;">
          Threshold: $2,208/mo
        </span>
      </label>

      <label style="cursor:pointer;display:block;margin-top:6px;">
        <input type="radio" name="income_band" value="cna"
               onchange="switchBand('cna')">
        &nbsp;<b>CNA</b> — $38,000/yr<br>
        <span style="font-size:10px;color:#555;margin-left:20px;">
          Threshold: $950/mo
        </span>
      </label>
    </div>

    <script>
    function switchBand(band) {{
        var rnLabel  = "{rn_label}";
        var cnaLabel = "{cna_label}";
        var items = document.querySelectorAll(
            '.leaflet-control-layers-overlays label'
        );
        items.forEach(function(label) {{
            var span = label.querySelector('span');
            if (!span) return;
            var text  = span.textContent.trim();
            var input = label.querySelector('input[type="checkbox"]');
            if (!input) return;
            if (text === rnLabel) {{
                if (band === 'rn'  && !input.checked) input.click();
                if (band === 'cna' &&  input.checked) input.click();
            }}
            if (text === cnaLabel) {{
                if (band === 'cna' && !input.checked) input.click();
                if (band === 'rn'  &&  input.checked) input.click();
            }}
        }});
    }}

    // Constrain map panning to the contiguous United States
    document.addEventListener('DOMContentLoaded', function() {{
        {map_var}.setMaxBounds([[18, -130], [52, -60]]);
        {map_var}.setMinZoom(4);
    }});
    </script>
    """


# ── Main build function ───────────────────────────────────────────────────────

def build_map(
    joined_gdf: gpd.GeoDataFrame,
    isochrones_gdf: gpd.GeoDataFrame,
) -> folium.Map:

    within_120 = joined_gdf[joined_gdf["drive_minutes"].notna()].copy()

    # Derive county + state boundaries by dissolving
    joined_gdf["_county"] = joined_gdf["GEOID"].str[:5]
    joined_gdf["_state"]  = joined_gdf["GEOID"].str[:2]
    county_gdf = joined_gdf.dissolve(by="_county").reset_index()
    state_gdf  = joined_gdf.dissolve(by="_state").reset_index()

    # Build colormaps
    rn_cm      = _rent_cmap(within_120, AFFORD_THRESHOLD,     RENT_GRADIENT)
    cna_cm     = _rent_cmap(within_120, CNA_AFFORD_THRESHOLD, RENT_GRADIENT)
    vac_cm     = _simple_cmap(within_120, "vacancy_rate",
                              VACANCY_GRADIENT, "Vacancy Rate (%)")
    burden_cm  = _simple_cmap(within_120, "cost_burdened_pct",
                              BURDEN_GRADIENT, "% Renters Cost-Burdened")
    pop_cm     = _simple_cmap(within_120, "pop_density",
                              POP_DENSITY_GRADIENT, "Population Density (per sq mi)")
    housing_cm = _simple_cmap(within_120, "housing_density",
                              HOUSING_DENSITY_GRADIENT, "Housing Unit Density (per sq mi)")

    # ── Base map (initial view = US, constrained by JS) ───────────────────────
    fmap = folium.Map(
        location=[38.5, -96],
        zoom_start=4,
        tiles="CartoDB positron",
        control_scale=True,
    )
    # Fly to the analysis area on load
    fmap.fit_bounds([
        [within_120.geometry.bounds.miny.min() - 0.5,
         within_120.geometry.bounds.minx.min() - 0.5],
        [within_120.geometry.bounds.maxy.max() + 0.5,
         within_120.geometry.bounds.maxx.max() + 0.5],
    ])

    # ── Summary stats per drive band ──────────────────────────────────────────
    from config import DRIVE_TIMES
    band_stats = []
    for minutes in sorted(DRIVE_TIMES):
        band = joined_gdf[joined_gdf["drive_minutes"] == minutes]
        has_rent = band["median_rent"].notna().sum()
        rn_aff   = band["rn_affordable"].eq(True).sum()
        cna_aff  = band["cna_affordable"].eq(True).sum()
        avg_vac    = band["vacancy_rate"].mean()
        avg_burden = band["cost_burdened_pct"].mean()
        band_stats.append({
            "minutes":    minutes,
            "n_tracts":   len(band),
            "rn_pct":     (rn_aff  / has_rent * 100) if has_rent else None,
            "cna_pct":    (cna_aff / has_rent * 100) if has_rent else None,
            "avg_vac":    float(avg_vac)    if pd.notna(avg_vac)    else None,
            "avg_burden": float(avg_burden) if pd.notna(avg_burden) else None,
        })

    # ── Layer 1: RN rent affordability (default ON) ───────────────────────────
    _rent_choropleth(
        within_120, rn_cm, AFFORD_THRESHOLD, "rn_affordable",
        "Median Rent — RN ($88,260/yr)", "RN", 88_260, show=True,
    ).add_to(fmap)

    # ── Layer 2: CNA rent affordability (default OFF) ─────────────────────────
    _rent_choropleth(
        within_120, cna_cm, CNA_AFFORD_THRESHOLD, "cna_affordable",
        "Median Rent — CNA ($38,000/yr)", "CNA", 38_000, show=False,
    ).add_to(fmap)

    # ── Layer 3: Vacancy rate (default OFF) ───────────────────────────────────
    _choropleth_group(
        within_120, "vacancy_rate", vac_cm,
        "Vacancy Rate (%)", "Vacancy rate", "{:.1f}%", show=False,
    ).add_to(fmap)

    # ── Layer 4: % cost-burdened renters (default OFF) ────────────────────────
    _choropleth_group(
        within_120, "cost_burdened_pct", burden_cm,
        "% Renters Cost-Burdened", "Cost-burdened renters", "{:.1f}%", show=False,
    ).add_to(fmap)

    # ── Layer 5: Population density choropleth (default OFF) ──────────────────
    _choropleth_group(
        within_120, "pop_density", pop_cm,
        "Population Density (per sq mi)", "Pop. density", "{:,.0f}/sq mi", show=False,
    ).add_to(fmap)

    # ── Layer 6: Housing unit density choropleth (default OFF) ────────────────
    _choropleth_group(
        within_120, "housing_density", housing_cm,
        "Housing Unit Density (per sq mi)", "Housing density", "{:,.0f}/sq mi", show=False,
    ).add_to(fmap)

    # ── County boundary lines (light) ─────────────────────────────────────────
    county_borders = folium.FeatureGroup(name="County boundaries", show=True)
    folium.GeoJson(
        data=county_gdf.__geo_interface__,
        style_function=lambda _: {
            "color": "#bbbbbb", "weight": 0.9, "fillOpacity": 0.0,
        },
        tooltip=folium.GeoJsonTooltip(fields=["_county"], aliases=["County FIPS:"]),
    ).add_to(county_borders)
    county_borders.add_to(fmap)

    # ── State boundary lines (slightly darker than county) ────────────────────
    state_borders = folium.FeatureGroup(name="State boundaries", show=True)
    folium.GeoJson(
        data=state_gdf.__geo_interface__,
        style_function=lambda _: {
            "color": "#555555", "weight": 1.8, "fillOpacity": 0.0,
        },
    ).add_to(state_borders)
    state_borders.add_to(fmap)

    # ── Isochrone rings ───────────────────────────────────────────────────────
    for _, iso_row in isochrones_gdf.sort_values("drive_minutes", ascending=False).iterrows():
        minutes = int(iso_row["drive_minutes"])
        color   = RING_COLORS.get(minutes, "#555")
        folium.GeoJson(
            data=iso_row["geometry"].__geo_interface__,
            name=f"{minutes}-min drive ring",
            style_function=lambda _, c=color: {
                "color": c, "weight": 2.5,
                "dashArray": RING_DASH, "fillOpacity": 0.0,
            },
            tooltip=folium.Tooltip(f"{minutes} min drive"),
            show=True,
        ).add_to(fmap)

    # ── Hospital marker ───────────────────────────────────────────────────────
    folium.Marker(
        location=[HOSPITAL_LAT, HOSPITAL_LON],
        tooltip=HOSPITAL_NAME,
        popup=folium.Popup(
            f"<b>{HOSPITAL_NAME}</b><br>Lovington, NM<br>"
            f"RN: $88,260/yr · CNA: $38,000/yr",
            max_width=230,
        ),
        icon=folium.Icon(color="blue", icon="plus-sign", prefix="glyphicon"),
    ).add_to(fmap)

    # ── Layer control ─────────────────────────────────────────────────────────
    folium.LayerControl(collapsed=False).add_to(fmap)

    # ── Scale bar for primary rent colormap ───────────────────────────────────
    rn_cm.add_to(fmap)

    # ── Legend (right side) ───────────────────────────────────────────────────
    fmap.get_root().html.add_child(folium.Element(_legend_html()))

    # ── Income band toggle panel (left side) + US bounds + min zoom ───────────
    map_var = fmap.get_name()
    fmap.get_root().html.add_child(folium.Element(_income_panel_html(map_var)))

    # ── Collapsible summary stats panel ───────────────────────────────────────
    fmap.get_root().html.add_child(folium.Element(_summary_panel_html(band_stats)))

    # ── Save ──────────────────────────────────────────────────────────────────
    fmap.save(OUTPUT_HTML)
    print(f"  Map saved → {OUTPUT_HTML}")
    return fmap
