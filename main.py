from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import plotly.express as px
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
RESULTS_PATH = BASE_DIR / "ltw26-ergebnisse.csv"
GEOMETRY_PATH = BASE_DIR / "wahlbezirke.gpkg"
OST_LAYER_NAME = "03_Ost"
TARGET_AGS = "08111000"

FIRST_VOTE_PARTIES = {
	"GRUENE": "D1",
	"CDU": "D2",
	"SPD": "D3",
	"FDP": "D4",
	"AfD": "D5",
	"Die Linke": "D6",
	"FREIE WAEHLER": "D7",
	"Die PARTEI": "D8",
	"dieBasis": "D9",
	"OEDP": "D11",
	"Volt": "D12",
	"Buendnis C": "D13",
	"BSW": "D16",
	"Die Gerechtigkeitspartei": "D17",
	"Tierschutzpartei": "D20",
	"WerteUnion": "D21",
	"Andere": "D22",
}

SECOND_VOTE_PARTIES = {
	"GRUENE": "F1",
	"CDU": "F2",
	"SPD": "F3",
	"FDP": "F4",
	"AfD": "F5",
	"Die Linke": "F6",
	"FREIE WAEHLER": "F7",
	"Die PARTEI": "F8",
	"dieBasis": "F9",
	"KlimalisteBW": "F10",
	"OEDP": "F11",
	"Volt": "F12",
	"Buendnis C": "F13",
	"PdH": "F14",
	"Verjuengungsforschung": "F15",
	"BSW": "F16",
	"Die Gerechtigkeitspartei": "F17",
	"PDR": "F18",
	"PdF": "F19",
	"Tierschutzpartei": "F20",
	"WerteUnion": "F21",
}

DISPLAY_PARTY_NAMES = {
	"GRUENE": "Gruene",
	"CDU": "CDU",
	"SPD": "SPD",
	"FDP": "FDP",
	"AfD": "AfD",
	"Die Linke": "Die Linke",
	"FREIE WAEHLER": "Freie Waehler",
	"Die PARTEI": "Die PARTEI",
	"dieBasis": "dieBasis",
	"OEDP": "OEDP",
	"Volt": "Volt",
	"Buendnis C": "Buendnis C",
	"BSW": "BSW",
	"Die Gerechtigkeitspartei": "Die Gerechtigkeitspartei",
	"Tierschutzpartei": "Tierschutzpartei",
	"WerteUnion": "WerteUnion",
	"Andere": "Andere",
	"KlimalisteBW": "KlimalisteBW",
	"PdH": "PdH",
	"Verjuengungsforschung": "Verjuengungsforschung",
	"PDR": "PDR",
	"PdF": "PdF",
}

MAJOR_PARTIES = ["GRUENE", "CDU", "AfD", "SPD", "Die Linke", "FDP", "Volt", "BSW"]
COMPARE_PARTY_KEYS = [party for party in MAJOR_PARTIES if party != "GRUENE"]
COMPARE_PARTY_LABELS = {
	DISPLAY_PARTY_NAMES.get(party, party): party for party in COMPARE_PARTY_KEYS
}
DEFAULT_COMPARE_PARTY_LABEL = DISPLAY_PARTY_NAMES.get(COMPARE_PARTY_KEYS[0], COMPARE_PARTY_KEYS[0])
VIEW_OPTIONS = ["Gesamtbezirk", "Urnenwahl", "Briefwahl"]
VIEW_TO_GEBIETSART = {
	"Urnenwahl": "URNENWAHLBEZIRK",
	"Briefwahl": "BRIEFWAHLBEZIRK",
}
BASE_MAP_METRICS = {
	"Gruene Zweitstimmenanteil": {
		"column": "gruene_zweit_pct",
		"label": "Gruene Zweitstimmenanteil in %",
		"scale": "YlGn",
	},
	"Gruene Erststimmenanteil": {
		"column": "gruene_erst_pct",
		"label": "Gruene Erststimmenanteil in %",
		"scale": "YlGn",
	},
	"Wahlbeteiligung": {
		"column": "wahlbeteiligung_pct",
		"label": "Wahlbeteiligung in %",
		"scale": "Blues",
	},
	"Cem-Bonus": {
		"column": "cem_bonus_pp",
		"label": "Gruene Zweitstimme minus Erststimme in Prozentpunkten",
		"scale": "RdYlGn",
	},
	"Ausschoepfungsgrad Gruene": {
		"column": "gruene_ausschoepfung_pct",
		"label": "Gruene Zweitstimmen bezogen auf Wahlberechtigte in %",
		"scale": "Mint",
	},
}


st.set_page_config(
	page_title="Dashboard Landtagswahl 2026 Stuttgart Ost",
	layout="wide",
)


def percentage(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
	numerator_values = pd.to_numeric(numerator, errors="coerce")
	denominator_values = pd.to_numeric(denominator, errors="coerce")
	safe_denominator = denominator_values.where(denominator_values != 0)
	return numerator_values.div(safe_denominator).mul(100).fillna(0.0).astype(float)


def format_int(value: float) -> str:
	return f"{int(round(value)):,}".replace(",", ".")


def format_pct(value: float) -> str:
	return f"{value:.1f} %".replace(".", ",")


def format_pp(value: float) -> str:
	return f"{value:+.1f} PP".replace(".", ",")


def clean_text_columns(frame: pd.DataFrame) -> pd.DataFrame:
	for column in frame.columns:
		if frame[column].dtype == "object":
			frame[column] = frame[column].fillna("").astype(str).str.strip()
	return frame


def get_compare_metric_columns(compare_party: str) -> tuple[str, str]:
	return (f"gruene_zu_{compare_party}_erst_pp", f"gruene_zu_{compare_party}_zweit_pp")


def build_map_metrics(compare_party: str, selected_view: str) -> dict[str, dict[str, str]]:
	compare_label = DISPLAY_PARTY_NAMES.get(compare_party, compare_party)
	compare_erst_column, compare_zweit_column = get_compare_metric_columns(compare_party)
	metrics = dict(BASE_MAP_METRICS)
	if selected_view != "Briefwahl":
		metrics["Mobilisierungsluecke Gruene"] = {
			"column": "mobilisierungsluecke_gruene_stimmen",
			"label": "Potenzial zusaetzlicher Gruene-Stimmen",
			"scale": "Tealgrn",
		}
	if selected_view == "Gesamtbezirk":
		metrics["Briefwahl-Effekt Zweit"] = {
			"column": "gruene_briefwahl_effekt_zweit_pp",
			"label": "Gruene Briefwahl minus Urnenwahl Zweitstimme in Prozentpunkten",
			"scale": "RdYlGn",
		}
		metrics["Briefwahl-Effekt Erst"] = {
			"column": "gruene_briefwahl_effekt_erst_pp",
			"label": "Gruene Briefwahl minus Urnenwahl Erststimme in Prozentpunkten",
			"scale": "RdYlGn",
		}
	metrics[f"Vorsprung Gruene vor {compare_label} Zweitstimme"] = {
		"column": compare_zweit_column,
		"label": f"Gruene minus {compare_label} Zweitstimme in Prozentpunkten",
		"scale": "RdYlGn",
	}
	metrics[f"Vorsprung Gruene vor {compare_label} Erststimme"] = {
		"column": compare_erst_column,
		"label": f"Gruene minus {compare_label} Erststimme in Prozentpunkten",
		"scale": "RdYlGn",
	}
	return metrics


def add_compare_metrics(frame: pd.DataFrame, compare_party: str) -> pd.DataFrame:
	enriched = frame.copy()
	compare_erst_column, compare_zweit_column = get_compare_metric_columns(compare_party)
	enriched[compare_erst_column] = enriched["gruene_erst_pct"] - enriched.get(f"erst_{compare_party}_pct", 0.0)
	enriched[compare_zweit_column] = enriched["gruene_zweit_pct"] - enriched.get(f"zweit_{compare_party}_pct", 0.0)
	return enriched


def prepare_map_frame(
	frame: gpd.GeoDataFrame,
	analysis_frames: dict[str, gpd.GeoDataFrame],
	selected_view: str,
	compare_party: str,
) -> gpd.GeoDataFrame:
	map_frame = add_compare_metrics(frame, compare_party)
	map_frame = ensure_strategy_columns(map_frame)
	if selected_view != "Briefwahl":
		map_frame = add_mobilization_gap(map_frame)
	if selected_view == "Gesamtbezirk":
		brief_effects = build_briefwahl_effect_frame(analysis_frames)
		map_frame = map_frame.merge(
			brief_effects[["base_key", "gruene_briefwahl_effekt_zweit_pp", "gruene_briefwahl_effekt_erst_pp"]],
			on="base_key",
			how="left",
		)
	return gpd.GeoDataFrame(map_frame, geometry="geometry", crs=frame.crs)


def display_party_name(party: str) -> str:
	return DISPLAY_PARTY_NAMES.get(party, party)


def add_rank_columns(enriched: pd.DataFrame, prefix: str, parties: dict[str, str], total_column: str) -> pd.DataFrame:
	available_parties = [party for party, column in parties.items() if column in enriched.columns and f"{prefix}_{party}_pct" in enriched.columns]
	if not available_parties:
		return enriched

	pct_frame = pd.DataFrame(
		{party: enriched[f"{prefix}_{party}_pct"] for party in available_parties},
		index=enriched.index,
	)
	rank_frame = pct_frame.rank(axis=1, ascending=False, method="min")
	enriched[f"gruene_{prefix}_rang"] = rank_frame.get("GRUENE", pd.Series(index=enriched.index, dtype=float))
	enriched[f"sieger_{prefix}"] = pct_frame.idxmax(axis=1).map(display_party_name)

	if "GRUENE" in pct_frame.columns:
		opponent_frame = pct_frame.drop(columns=["GRUENE"], errors="ignore")
		if not opponent_frame.empty:
			enriched[f"hauptgegner_{prefix}"] = opponent_frame.idxmax(axis=1)
			enriched[f"hauptgegner_{prefix}_label"] = enriched[f"hauptgegner_{prefix}"].map(display_party_name)
			enriched[f"hauptgegner_{prefix}_pct"] = opponent_frame.max(axis=1)
			enriched[f"gruene_zu_hauptgegner_{prefix}_pp"] = enriched[f"gruene_{prefix}_pct"] - enriched[f"hauptgegner_{prefix}_pct"]

	if total_column in enriched.columns:
		vote_frame = pd.DataFrame(
			{party: enriched[parties[party]] for party in available_parties if parties[party] in enriched.columns},
			index=enriched.index,
		)
		enriched[f"gruene_{prefix}_platz_1"] = rank_frame.get("GRUENE", 99).eq(1)
		enriched[f"gruene_{prefix}_platz_2"] = rank_frame.get("GRUENE", 99).eq(2)
		if "GRUENE" in vote_frame.columns:
			enriched[f"gruene_{prefix}_stimmenanteil_abs"] = percentage(vote_frame["GRUENE"], enriched[total_column])

	return enriched


def extract_numeric_columns(frame: pd.DataFrame) -> list[str]:
	base_columns = {
		"gemeldete Wahlbezirke",
		"Anzahl Wahlbezirke",
		"Wahlberechtigte gesamt (A)",
		"Wahlberechtigte ohne Wahlschein (A1)",
		"Wahlberechtigte mit Wahlschein (A2)",
		"Wahlberechtigte nicht im WVZ (A3)",
		"Waehler gesamt (B)",
		"Waehler ohne Wahlschein",
		"Waehler mit Wahlschein",
		"Erststimmen ungueltige (C)",
		"Erststimmen gueltige (D)",
		"Zweitstimmen ungueltige (E)",
		"Zweitstimmen gueltige (F)",
	}
	dynamic_columns = [column for column in frame.columns if column.startswith("D") or column.startswith("F")]
	return [column for column in frame.columns if column in base_columns or column in dynamic_columns]


@st.cache_data(show_spinner=False)
def load_results() -> pd.DataFrame:
	frame = pd.read_csv(RESULTS_PATH, sep=";", dtype=str, encoding="utf-8")
	frame = frame.loc[:, [column for column in frame.columns if column and not str(column).startswith("Unnamed")]]
	frame = clean_text_columns(frame)
	frame = frame[frame["Gebietsart"].isin(VIEW_TO_GEBIETSART.values())].copy()

	numeric_columns = extract_numeric_columns(frame)
	for column in numeric_columns:
		frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)

	frame["view_mode"] = frame["Gebietsart"].map(
		{
			"URNENWAHLBEZIRK": "Urnenwahl",
			"BRIEFWAHLBEZIRK": "Briefwahl",
		}
	)
	frame["join_key"] = frame["Bezirksnummer"].astype(str).str.strip()
	frame = frame[(frame["AGS"] == TARGET_AGS) & (frame["join_key"].str.startswith("003-"))].copy()
	frame["base_key"] = frame["join_key"]

	derived_columns: dict[str, pd.Series] = {}
	for party, column in FIRST_VOTE_PARTIES.items():
		if column in frame.columns:
			derived_columns[f"erst_{party}_votes"] = frame[column]
			derived_columns[f"erst_{party}_pct"] = percentage(frame[column], frame["Erststimmen gueltige (D)"])

	for party, column in SECOND_VOTE_PARTIES.items():
		if column in frame.columns:
			derived_columns[f"zweit_{party}_votes"] = frame[column]
			derived_columns[f"zweit_{party}_pct"] = percentage(frame[column], frame["Zweitstimmen gueltige (F)"])

	frame = frame.assign(**derived_columns)

	return frame


@st.cache_data(show_spinner=False)
def load_geometry_catalog() -> tuple[gpd.GeoDataFrame, str]:
	layers = gpd.list_layers(GEOMETRY_PATH)
	layer_names = layers["name"].tolist()
	layer_name = OST_LAYER_NAME if OST_LAYER_NAME in layer_names else layer_names[0]
	geometry = gpd.read_file(GEOMETRY_PATH, layer=layer_name)
	geometry = clean_text_columns(geometry)

	if layer_name != OST_LAYER_NAME and {"STBNUM_T", "STBNAM_T"}.issubset(geometry.columns):
		geometry = geometry[(geometry["STBNUM_T"] == "03") | (geometry["STBNAM_T"].str.lower() == "ost")].copy()

	geometry = geometry.to_crs(4326)
	geometry["base_key"] = geometry["AWBEZ_T"].astype(str).str.strip()
	geometry["urnen_key"] = geometry["AWBEZ_T"].astype(str).str.strip()
	geometry["brief_key"] = geometry["BWBEZ_T"].astype(str).str.strip()

	records: list[dict[str, object]] = []
	for record in geometry.to_dict(orient="records"):
		base_key = str(record["base_key"]).strip()
		urnen_key = str(record["urnen_key"]).strip()
		brief_key = str(record["brief_key"]).strip()

		common_fields = {
			"base_key": base_key,
			"stadtbezirk": record.get("STBNAM_T", "Ost"),
			"stadtbezirk_nummer": record.get("STBNUM_T", "03"),
			"source_layer": layer_name,
			"geometry": record["geometry"],
		}

		records.append(
			{
				**common_fields,
				"view_mode": "Urnenwahl",
				"join_key": urnen_key,
				"map_id": f"Urnenwahl::{urnen_key}",
				"bezirk_label": urnen_key,
			}
		)
		records.append(
			{
				**common_fields,
				"view_mode": "Briefwahl",
				"join_key": brief_key,
				"map_id": f"Briefwahl::{brief_key}",
				"bezirk_label": brief_key,
			}
		)
		records.append(
			{
				**common_fields,
				"view_mode": "Gesamtbezirk",
				"join_key": base_key,
				"map_id": f"Gesamtbezirk::{base_key}",
				"bezirk_label": base_key,
			}
		)

	catalog = gpd.GeoDataFrame(records, geometry="geometry", crs=geometry.crs)
	return catalog, layer_name


def enrich_metrics(frame: pd.DataFrame) -> pd.DataFrame:
	enriched = frame.copy()
	enriched["wahlbeteiligung_pct"] = percentage(
		enriched["Waehler gesamt (B)"],
		enriched["Wahlberechtigte gesamt (A)"],
	)
	for party, column in FIRST_VOTE_PARTIES.items():
		if column in enriched.columns:
			enriched[f"erst_{party}_pct"] = percentage(enriched[column], enriched["Erststimmen gueltige (D)"])
	for party, column in SECOND_VOTE_PARTIES.items():
		if column in enriched.columns:
			enriched[f"zweit_{party}_pct"] = percentage(enriched[column], enriched["Zweitstimmen gueltige (F)"])
	enriched["gruene_erst_pct"] = percentage(enriched["D1"], enriched["Erststimmen gueltige (D)"])
	enriched["gruene_zweit_pct"] = percentage(enriched["F1"], enriched["Zweitstimmen gueltige (F)"])
	enriched["cdu_erst_pct"] = percentage(enriched["D2"], enriched["Erststimmen gueltige (D)"])
	enriched["cdu_zweit_pct"] = percentage(enriched["F2"], enriched["Zweitstimmen gueltige (F)"])
	enriched["gruene_zu_cdu_erst_pp"] = enriched["gruene_erst_pct"] - enriched["cdu_erst_pct"]
	enriched["gruene_zu_cdu_zweit_pp"] = enriched["gruene_zweit_pct"] - enriched["cdu_zweit_pct"]
	enriched["split_ticket_pp"] = enriched["gruene_zweit_pct"] - enriched["gruene_erst_pct"]
	enriched["cem_bonus_pp"] = enriched["gruene_zweit_pct"] - enriched["gruene_erst_pct"]
	enriched["gruene_ausschoepfung_pct"] = percentage(enriched["F1"], enriched["Wahlberechtigte gesamt (A)"])
	enriched = add_rank_columns(enriched, "erst", FIRST_VOTE_PARTIES, "Erststimmen gueltige (D)")
	enriched = add_rank_columns(enriched, "zweit", SECOND_VOTE_PARTIES, "Zweitstimmen gueltige (F)")
	return enriched


@st.cache_data(show_spinner=False)
def build_analysis_frames() -> tuple[dict[str, gpd.GeoDataFrame], pd.DataFrame, pd.DataFrame]:
	results = load_results()
	geometry_catalog, _ = load_geometry_catalog()

	mapping = geometry_catalog[geometry_catalog["view_mode"].isin(["Urnenwahl", "Briefwahl"])][
		["view_mode", "join_key", "base_key"]
	].drop_duplicates()
	matched = results.merge(mapping, on=["view_mode", "join_key"], how="inner", suffixes=("", "_geo"))
	matched["base_key"] = matched["base_key_geo"]
	matched = matched.drop(columns=["base_key_geo"])
	unmapped = results.merge(mapping, on=["view_mode", "join_key"], how="left", indicator=True)
	unmapped = unmapped[unmapped["_merge"] == "left_only"].drop(columns=["_merge", "base_key_y"], errors="ignore")

	numeric_columns = extract_numeric_columns(results)
	analysis_frames: dict[str, gpd.GeoDataFrame] = {}

	for view_mode in ["Urnenwahl", "Briefwahl"]:
		data_subset = matched[matched["view_mode"] == view_mode].copy()
		geo_subset = geometry_catalog[
			(geometry_catalog["view_mode"] == view_mode)
			& (geometry_catalog["join_key"].isin(data_subset["join_key"]))
		].copy()
		merged = geo_subset.merge(
			data_subset,
			on=["view_mode", "join_key", "base_key"],
			how="left",
			suffixes=("", "_data"),
		)
		for column in numeric_columns:
			merged[column] = merged[column].fillna(0)
		merged["bezirk_name"] = merged["Gebietsname"].fillna(merged["bezirk_label"])
		analysis_frames[view_mode] = enrich_metrics(merged)

	grouped = matched.groupby("base_key", as_index=False)[numeric_columns].sum()
	gesamt_geo = geometry_catalog[
		(geometry_catalog["view_mode"] == "Gesamtbezirk")
		& (geometry_catalog["base_key"].isin(grouped["base_key"]))
	].copy()
	urnen_names = (
		matched[matched["view_mode"] == "Urnenwahl"][["base_key", "Gebietsname"]]
		.drop_duplicates("base_key")
		.rename(columns={"Gebietsname": "urnen_name"})
	)
	brief_names = (
		matched[matched["view_mode"] == "Briefwahl"][["base_key", "Gebietsname"]]
		.drop_duplicates("base_key")
		.rename(columns={"Gebietsname": "brief_name"})
	)
	grouped = grouped.merge(urnen_names, on="base_key", how="left").merge(brief_names, on="base_key", how="left")
	grouped["bezirk_name"] = grouped["urnen_name"].fillna(grouped["brief_name"]).fillna(grouped["base_key"])
	grouped["join_key"] = grouped["base_key"]
	grouped["view_mode"] = "Gesamtbezirk"

	gesamt = gesamt_geo.merge(grouped, on=["view_mode", "join_key", "base_key"], how="left")
	for column in numeric_columns:
		gesamt[column] = gesamt[column].fillna(0)
	gesamt["bezirk_name"] = gesamt["bezirk_name"].fillna(gesamt["bezirk_label"])
	analysis_frames["Gesamtbezirk"] = enrich_metrics(gesamt)

	return analysis_frames, matched, unmapped


def summarize_frame(frame: pd.DataFrame) -> pd.Series:
	numeric_columns = extract_numeric_columns(frame)
	summary = frame[numeric_columns].sum(numeric_only=True)
	for party, column in FIRST_VOTE_PARTIES.items():
		if column in summary.index:
			summary[f"erst_{party}_pct"] = 100 * summary[column] / summary["Erststimmen gueltige (D)"] if summary["Erststimmen gueltige (D)"] else 0
	for party, column in SECOND_VOTE_PARTIES.items():
		if column in summary.index:
			summary[f"zweit_{party}_pct"] = 100 * summary[column] / summary["Zweitstimmen gueltige (F)"] if summary["Zweitstimmen gueltige (F)"] else 0
	summary["gruene_erst_pct"] = 100 * summary["D1"] / summary["Erststimmen gueltige (D)"] if summary["Erststimmen gueltige (D)"] else 0
	summary["gruene_zweit_pct"] = 100 * summary["F1"] / summary["Zweitstimmen gueltige (F)"] if summary["Zweitstimmen gueltige (F)"] else 0
	summary["cdu_erst_pct"] = 100 * summary["D2"] / summary["Erststimmen gueltige (D)"] if summary["Erststimmen gueltige (D)"] else 0
	summary["cdu_zweit_pct"] = 100 * summary["F2"] / summary["Zweitstimmen gueltige (F)"] if summary["Zweitstimmen gueltige (F)"] else 0
	summary["wahlbeteiligung_pct"] = 100 * summary["Waehler gesamt (B)"] / summary["Wahlberechtigte gesamt (A)"] if summary["Wahlberechtigte gesamt (A)"] else 0
	summary["split_ticket_pp"] = summary["gruene_zweit_pct"] - summary["gruene_erst_pct"]
	summary["cem_bonus_pp"] = summary["gruene_zweit_pct"] - summary["gruene_erst_pct"]
	summary["gruene_ausschoepfung_pct"] = 100 * summary["F1"] / summary["Wahlberechtigte gesamt (A)"] if summary["Wahlberechtigte gesamt (A)"] else 0
	summary["gruene_zu_cdu_erst_pp"] = summary["gruene_erst_pct"] - summary["cdu_erst_pct"]
	summary["gruene_zu_cdu_zweit_pp"] = summary["gruene_zweit_pct"] - summary["cdu_zweit_pct"]
	return summary


def build_map(frame: gpd.GeoDataFrame, metric_name: str, map_metrics: dict[str, dict[str, str]]) -> px.choropleth_mapbox:
	metric_config = map_metrics[metric_name]
	map_frame = frame.copy()
	geojson = json.loads(map_frame.to_json())
	center = map_frame.unary_union.centroid
	hover_data = {
		"bezirk_label": True,
		"gruene_erst_pct": ":.1f",
		"gruene_zweit_pct": ":.1f",
		"wahlbeteiligung_pct": ":.1f",
		"map_id": False,
	}
	labels = {
		metric_config["column"]: metric_config["label"],
	}
	for column in [
		"cem_bonus_pp",
		"mobilisierungsluecke_gruene_stimmen",
		"gruene_briefwahl_effekt_zweit_pp",
		"gruene_briefwahl_effekt_erst_pp",
	]:
		if column in map_frame.columns:
			hover_data[column] = ":.1f"

	for column in map_frame.columns:
		if column.startswith("gruene_zu_") and column.endswith("_zweit_pp"):
			party_code = column.removeprefix("gruene_zu_").removesuffix("_zweit_pp").upper()
			party_label = DISPLAY_PARTY_NAMES.get(party_code, party_code)
			hover_data[column] = ":.1f"
			labels[column] = f"Gruene minus {party_label} Zweit PP"

	fig = px.choropleth_mapbox(
		map_frame,
		geojson=geojson,
		locations="map_id",
		featureidkey="properties.map_id",
		color=metric_config["column"],
		color_continuous_scale=metric_config["scale"],
		mapbox_style="carto-positron",
		center={"lat": center.y, "lon": center.x},
		zoom=12,
		opacity=0.72,
		hover_name="bezirk_name",
		hover_data=hover_data,
		labels=labels,
	)
	fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
	return fig


def build_party_share_chart(summary: pd.Series) -> px.bar:
	chart_data = []
	for party in MAJOR_PARTIES:
		chart_data.append(
			{
				"Partei": DISPLAY_PARTY_NAMES.get(party, party),
				"Stimmart": "Erststimme",
				"Anteil": summary.get(f"erst_{party}_pct", 0.0),
			}
		)
		chart_data.append(
			{
				"Partei": DISPLAY_PARTY_NAMES.get(party, party),
				"Stimmart": "Zweitstimme",
				"Anteil": summary.get(f"zweit_{party}_pct", 0.0),
			}
		)

	chart_frame = pd.DataFrame(chart_data)
	fig = px.bar(
		chart_frame,
		x="Partei",
		y="Anteil",
		color="Stimmart",
		barmode="group",
		color_discrete_sequence=["#0b6e4f", "#7fbf3f"],
	)
	fig.update_layout(margin={"r": 0, "t": 20, "l": 0, "b": 0}, yaxis_title="Anteil in %")
	return fig


def build_top_chart(frame: pd.DataFrame, metric_column: str, title: str) -> px.bar:
	ranking = frame[["bezirk_label", "bezirk_name", metric_column]].sort_values(metric_column, ascending=False).head(10)
	ranking["label"] = ranking["bezirk_label"] + " | " + ranking["bezirk_name"]
	fig = px.bar(
		ranking.sort_values(metric_column),
		x=metric_column,
		y="label",
		orientation="h",
		title=title,
		color=metric_column,
		color_continuous_scale="YlGn",
	)
	fig.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0}, yaxis_title="")
	return fig


def build_scatter(frame: pd.DataFrame) -> px.scatter:
	scatter = frame[["bezirk_label", "bezirk_name", "wahlbeteiligung_pct", "gruene_zweit_pct"]].copy()
	scatter["label"] = scatter["bezirk_label"] + " | " + scatter["bezirk_name"]
	fig = px.scatter(
		scatter,
		x="wahlbeteiligung_pct",
		y="gruene_zweit_pct",
		text="bezirk_label",
		hover_name="label",
		color="gruene_zweit_pct",
		color_continuous_scale="Tealgrn",
	)
	fig.update_traces(textposition="top center")
	fig.update_layout(
		margin={"r": 0, "t": 20, "l": 0, "b": 0},
		xaxis_title="Wahlbeteiligung in %",
		yaxis_title="Gruene Zweitstimmen in %",
	)
	return fig


def add_mobilization_gap(frame: pd.DataFrame) -> pd.DataFrame:
	enriched = frame.copy()
	valid_turnout = enriched.loc[enriched["Wahlberechtigte gesamt (A)"] > 0, "wahlbeteiligung_pct"]
	average_turnout = float(valid_turnout.mean()) if not valid_turnout.empty else 0.0
	enriched["ost_durchschnitt_wahlbeteiligung_pct"] = average_turnout
	enriched["mobilisierungsluecke_pp"] = (average_turnout - enriched["wahlbeteiligung_pct"]).clip(lower=0)
	enriched["mobilisierungsluecke_gruene_stimmen"] = (
		enriched["mobilisierungsluecke_pp"]
		/ 100
		* enriched["Wahlberechtigte gesamt (A)"]
		* enriched["gruene_zweit_pct"]
		/ 100
	)
	return enriched


def ensure_strategy_columns(frame: pd.DataFrame) -> pd.DataFrame:
	required_columns = {
		"cem_bonus_pp",
		"hauptgegner_zweit_label",
		"gruene_zu_hauptgegner_zweit_pp",
		"gruene_erst_rang",
		"gruene_zweit_rang",
		"gruene_zweit_platz_1",
		"gruene_erst_platz_1",
	}
	if required_columns.issubset(frame.columns):
		return frame
	return enrich_metrics(frame)


def build_briefwahl_effect_frame(analysis_frames: dict[str, gpd.GeoDataFrame]) -> pd.DataFrame:
	urnen = analysis_frames["Urnenwahl"][[
		"base_key",
		"bezirk_name",
		"gruene_zweit_pct",
		"gruene_erst_pct",
		"wahlbeteiligung_pct",
		"gruene_zu_cdu_zweit_pp",
	]].rename(
		columns={
			"gruene_zweit_pct": "gruene_zweit_urne_pct",
			"gruene_erst_pct": "gruene_erst_urne_pct",
			"wahlbeteiligung_pct": "wahlbeteiligung_urne_pct",
			"gruene_zu_cdu_zweit_pp": "gruene_zu_cdu_urne_pp",
		}
	)
	brief = analysis_frames["Briefwahl"][[
		"base_key",
		"bezirk_name",
		"gruene_zweit_pct",
		"gruene_erst_pct",
		"gruene_zu_cdu_zweit_pp",
	]].rename(
		columns={
			"gruene_zweit_pct": "gruene_zweit_brief_pct",
			"gruene_erst_pct": "gruene_erst_brief_pct",
			"gruene_zu_cdu_zweit_pp": "gruene_zu_cdu_brief_pp",
		}
	)
	effects = urnen.merge(brief, on="base_key", how="inner", suffixes=("_urne", "_brief"))
	effects["bezirk_name"] = effects["bezirk_name_urne"].fillna(effects["bezirk_name_brief"]).fillna(effects["base_key"])
	effects["gruene_briefwahl_effekt_zweit_pp"] = effects["gruene_zweit_brief_pct"] - effects["gruene_zweit_urne_pct"]
	effects["gruene_briefwahl_effekt_erst_pp"] = effects["gruene_erst_brief_pct"] - effects["gruene_erst_urne_pct"]
	effects["cdu_briefwahl_effekt_zweit_pp"] = effects["gruene_zu_cdu_brief_pp"] - effects["gruene_zu_cdu_urne_pp"]
	return effects.sort_values("base_key")


def build_main_opponent_chart(frame: pd.DataFrame) -> px.bar:
	counts = (
		frame["hauptgegner_zweit_label"]
		.fillna("n/a")
		.value_counts()
		.rename_axis("Hauptgegner")
		.reset_index(name="Bezirke")
	)
	fig = px.bar(counts, x="Hauptgegner", y="Bezirke", color="Bezirke", color_continuous_scale="YlOrRd")
	fig.update_layout(margin={"r": 0, "t": 20, "l": 0, "b": 0})
	return fig


def build_rank_heatmap(frame: pd.DataFrame) -> px.imshow:
	rank_frame = pd.DataFrame(
		{
			"Erststimme": frame.set_index("bezirk_label")["gruene_erst_rang"],
			"Zweitstimme": frame.set_index("bezirk_label")["gruene_zweit_rang"],
		}
	).sort_index()
	fig = px.imshow(
		rank_frame,
		text_auto=True,
		aspect="auto",
		color_continuous_scale="RdYlGn_r",
		labels={"x": "Stimmart", "y": "Bezirk", "color": "Gruene-Rang"},
	)
	fig.update_layout(margin={"r": 0, "t": 20, "l": 0, "b": 0})
	return fig


def build_cem_bonus_chart(frame: pd.DataFrame) -> px.bar:
	ranking = frame[["bezirk_label", "bezirk_name", "cem_bonus_pp"]].copy()
	ranking = ranking.sort_values("cem_bonus_pp", ascending=False)
	ranking["label"] = ranking["bezirk_label"] + " | " + ranking["bezirk_name"]
	fig = px.bar(
		ranking,
		x="cem_bonus_pp",
		y="label",
		orientation="h",
		color="cem_bonus_pp",
		color_continuous_scale="RdYlGn",
		labels={"cem_bonus_pp": "Cem-Bonus in PP", "label": "Bezirk"},
	)
	fig.update_layout(margin={"r": 0, "t": 20, "l": 0, "b": 0}, yaxis_title="")
	return fig


def build_mobilization_chart(frame: pd.DataFrame) -> px.bar:
	ranking = frame[["bezirk_label", "bezirk_name", "mobilisierungsluecke_gruene_stimmen"]].copy()
	ranking = ranking.sort_values("mobilisierungsluecke_gruene_stimmen", ascending=False).head(10)
	ranking["label"] = ranking["bezirk_label"] + " | " + ranking["bezirk_name"]
	fig = px.bar(
		ranking.sort_values("mobilisierungsluecke_gruene_stimmen"),
		x="mobilisierungsluecke_gruene_stimmen",
		y="label",
		orientation="h",
		color="mobilisierungsluecke_gruene_stimmen",
		color_continuous_scale="Tealgrn",
	)
	fig.update_layout(margin={"r": 0, "t": 20, "l": 0, "b": 0}, yaxis_title="", xaxis_title="Moegliche zusaetzliche Gruene-Stimmen")
	return fig


def build_brief_effect_chart(effects: pd.DataFrame) -> px.bar:
	chart_data = effects.copy()
	chart_data["bezirk_label"] = chart_data["bezirk_name"].fillna(chart_data["base_key"])
	duplicate_names = chart_data["bezirk_label"].duplicated(keep=False)
	chart_data.loc[duplicate_names, "bezirk_label"] = (
		chart_data.loc[duplicate_names, "bezirk_label"]
		+ " ("
		+ chart_data.loc[duplicate_names, "base_key"].astype(str)
		+ ")"
	)
	fig = px.bar(
		chart_data.sort_values("gruene_briefwahl_effekt_zweit_pp"),
		x="gruene_briefwahl_effekt_zweit_pp",
		y="bezirk_label",
		orientation="h",
		color="gruene_briefwahl_effekt_zweit_pp",
		color_continuous_scale="RdYlGn",
		hover_data={"base_key": True},
		labels={"gruene_briefwahl_effekt_zweit_pp": "Briefwahl-Effekt Gruene Zweit PP", "bezirk_label": "Bezirk"},
	)
	fig.update_layout(margin={"r": 0, "t": 20, "l": 0, "b": 0})
	return fig


def render_header(layer_name: str, matched_rows: int, unmapped_rows: int) -> None:
	st.title("Landtagswahl 2026: Dashboard Gruene Stuttgart Ost")
	st.caption(
		"Analysebasis: alle Stuttgarter-Ost-Wahlbezirke innerhalb Stuttgart, raeumlich gefiltert ueber den GPKG-Layer "
		f"`{layer_name}`. Join erfolgreich fuer {matched_rows} Wahlbezirkszeilen."
	)
	if unmapped_rows:
		st.warning(
			f"{unmapped_rows} Wahlbezirkszeilen sind in der CSV fuer Stuttgart Ost vorhanden, aber nicht kartierbar. "
			"Aktuell betrifft das zentral ausgezaehlte Briefwahlbezirke wie Schwabenzentrum. "
			"Er erscheint deshalb nicht in Karte und Bezirksrankings."
		)


def render_overview(frame: gpd.GeoDataFrame, summary: pd.Series, compare_party: str) -> None:
	mobilization = frame["wahlbeteiligung_pct"].corr(frame["gruene_zweit_pct"])
	top_zweit = frame.sort_values("gruene_zweit_pct", ascending=False).iloc[0]
	strongest_gap = frame.sort_values("gruene_zu_cdu_zweit_pp", ascending=False).iloc[0]
	compare_key = compare_party
	compare_label = DISPLAY_PARTY_NAMES.get(compare_key, compare_key)

	st.caption(f"Aktive Vergleichspartei: {compare_label}")

	row1 = st.columns(4)
	row1[0].metric("Wahlberechtigte", format_int(summary["Wahlberechtigte gesamt (A)"]))
	row1[1].metric("Waehlende", format_int(summary["Waehler gesamt (B)"]))
	row1[2].metric("Wahlbeteiligung", format_pct(summary["wahlbeteiligung_pct"]))
	row1[3].metric("Gruene Zweitstimmen", format_int(summary["F1"]))

	row2 = st.columns(4)
	row2[0].metric("Gruene Erststimmenanteil", format_pct(summary["gruene_erst_pct"]))
	row2[1].metric("Gruene Zweitstimmenanteil", format_pct(summary["gruene_zweit_pct"]))
	row2[2].metric("Cem-Bonus", format_pp(summary["cem_bonus_pp"]))
	row2[3].metric("Ausschoepfungsgrad Gruene", format_pct(summary["gruene_ausschoepfung_pct"]))

	row3 = st.columns(4)
	row3[0].metric("Gruene vs CDU Erststimme", format_pp(summary["gruene_zu_cdu_erst_pp"]))
	row3[1].metric("Gruene vs CDU Zweitstimme", format_pp(summary["gruene_zu_cdu_zweit_pp"]))
	row3[2].metric(
		f"Gruene vs {compare_label} Zweitstimme",
		format_pp(summary["gruene_zweit_pct"] - summary.get(f"zweit_{compare_key}_pct", 0.0)),
	)
	row3[3].metric("Mobilisierungsindex", f"{mobilization:.2f}" if pd.notna(mobilization) else "n/a")

	insight_left, insight_right = st.columns(2)
	insight_left.info(
		f"Staerkster Gruene-Zweitstimmenbezirk: {top_zweit['bezirk_label']} | {top_zweit['bezirk_name']} mit "
		f"{format_pct(top_zweit['gruene_zweit_pct'])}."
	)
	insight_right.info(
		f"Groesster Vorsprung vor der CDU in der Zweitstimme: {strongest_gap['bezirk_label']} | {strongest_gap['bezirk_name']} "
		f"mit {format_pp(strongest_gap['gruene_zu_cdu_zweit_pp'])}."
	)

	st.plotly_chart(build_party_share_chart(summary), use_container_width=True)


def render_map_tab(frame: gpd.GeoDataFrame, analysis_frames: dict[str, gpd.GeoDataFrame], selected_view: str, selected_metric: str, compare_party: str) -> None:
	map_metrics = build_map_metrics(compare_party, selected_view)
	compare_label = DISPLAY_PARTY_NAMES.get(compare_party, compare_party)
	_, compare_zweit_column = get_compare_metric_columns(compare_party)
	map_frame = prepare_map_frame(frame, analysis_frames, selected_view, compare_party)
	st.caption(f"Kartenvergleich aktuell gegen: {compare_label}")
	st.plotly_chart(build_map(map_frame, selected_metric, map_metrics), use_container_width=True)
	diagnostic_columns = [
		"bezirk_label",
		"bezirk_name",
		"gruene_erst_pct",
		"gruene_zweit_pct",
		"wahlbeteiligung_pct",
		"cem_bonus_pp",
		compare_zweit_column,
	]
	for column in ["mobilisierungsluecke_gruene_stimmen", "gruene_briefwahl_effekt_zweit_pp", "gruene_briefwahl_effekt_erst_pp"]:
		if column in map_frame.columns:
			diagnostic_columns.append(column)
	diagnostic = map_frame[diagnostic_columns].copy()
	diagnostic = diagnostic.rename(
		columns={
			"bezirk_label": "Bezirk",
			"bezirk_name": "Name",
			"gruene_erst_pct": "Gruene Erst %",
			"gruene_zweit_pct": "Gruene Zweit %",
			"wahlbeteiligung_pct": "Wahlbeteiligung %",
			"cem_bonus_pp": "Cem-Bonus PP",
			compare_zweit_column: f"Gruene minus {compare_label} Zweit PP",
			"mobilisierungsluecke_gruene_stimmen": "Mobilisierungsluecke Stimmen",
			"gruene_briefwahl_effekt_zweit_pp": "Briefwahl-Effekt Zweit PP",
			"gruene_briefwahl_effekt_erst_pp": "Briefwahl-Effekt Erst PP",
		}
	)
	st.dataframe(diagnostic.sort_values("Gruene Zweit %", ascending=False), use_container_width=True)


def render_bezirke_tab(frame: gpd.GeoDataFrame) -> None:
	left, right = st.columns(2)
	left.plotly_chart(
		build_top_chart(frame, "gruene_zweit_pct", "Top 10 Bezirke nach Gruene-Zweitstimmenanteil"),
		use_container_width=True,
	)
	right.plotly_chart(
		build_top_chart(frame, "wahlbeteiligung_pct", "Top 10 Bezirke nach Wahlbeteiligung"),
		use_container_width=True,
	)
	st.plotly_chart(build_scatter(frame), use_container_width=True)


def render_strategy_tab(frame: gpd.GeoDataFrame, analysis_frames: dict[str, gpd.GeoDataFrame], selected_view: str) -> None:
	strategy_frame = add_mobilization_gap(ensure_strategy_columns(frame))
	brief_effects = build_briefwahl_effect_frame(analysis_frames)
	strategy_frame = strategy_frame.merge(
		brief_effects[["base_key", "gruene_briefwahl_effekt_zweit_pp", "gruene_briefwahl_effekt_erst_pp"]],
		on="base_key",
		how="left",
	)
	avg_cem_bonus = strategy_frame["cem_bonus_pp"].mean()
	mobilisierung_summe = strategy_frame["mobilisierungsluecke_gruene_stimmen"].sum()
	avg_brief_effekt = brief_effects["gruene_briefwahl_effekt_zweit_pp"].mean() if not brief_effects.empty else 0.0
	positive_brief = int((brief_effects["gruene_briefwahl_effekt_zweit_pp"] > 0).sum()) if not brief_effects.empty else 0
	positive_cem_bonus = int((strategy_frame["cem_bonus_pp"] > 0).sum())
	top5_share = 100 * strategy_frame.nlargest(5, "F1")["F1"].sum() / strategy_frame["F1"].sum() if strategy_frame["F1"].sum() else 0

	row = st.columns(5)
	row[0].metric("Cem-Bonus", format_pp(avg_cem_bonus))
	row[1].metric("Briefwahl-Effekt Zweit", format_pp(avg_brief_effekt))
	row[2].metric("Positive Briefwahl-Bezirke", str(positive_brief))
	row[3].metric("Cem-Bonus-Bezirke", str(positive_cem_bonus))
	row[4].metric("Mobilisierungsluecke", format_int(mobilisierung_summe))
	st.caption(f"Top-5-Konzentration der Gruene-Zweitstimmen: {format_pct(top5_share)}")
	st.info(
		"Mobilisierungsluecke: Geschaetztes zusaetzliches Gruene-Stimmenpotenzial in Bezirken mit unterdurchschnittlicher "
		"Wahlbeteiligung. Berechnung je Bezirk: max(Ost-Durchschnitt Beteiligung - Bezirks-Beteiligung, 0) x "
		"Wahlberechtigte x Gruene-Zweitstimmenanteil. In der Briefwahl ist der Wert nur eingeschraenkt belastbar."
	)

	left, right = st.columns(2)
	left.plotly_chart(build_cem_bonus_chart(strategy_frame), use_container_width=True)
	if selected_view == "Briefwahl":
		right.info("Mobilisierungsluecke ist fuer reine Briefwahl nicht belastbar, weil in den Briefwahlzeilen keine Wahlberechtigten hinterlegt sind.")
	else:
		right.plotly_chart(build_mobilization_chart(strategy_frame), use_container_width=True)

	spacer_left, chart_col, spacer_right = st.columns([1, 6, 1])
	if selected_view == "Gesamtbezirk":
		chart_col.plotly_chart(build_brief_effect_chart(brief_effects), use_container_width=True)
	else:
		chart_col.info("Briefwahl-Effekt wird auf Gesamtbezirksebene aus Urnen- und Briefwahldaten berechnet.")

	strategy_table = strategy_frame[[
		"bezirk_label",
		"bezirk_name",
		"cem_bonus_pp",
		"gruene_briefwahl_effekt_zweit_pp",
		"gruene_briefwahl_effekt_erst_pp",
		"mobilisierungsluecke_gruene_stimmen",
	]].copy()
	strategy_table = strategy_table.rename(
		columns={
			"bezirk_label": "Bezirk",
			"bezirk_name": "Name",
			"cem_bonus_pp": "Cem-Bonus PP",
			"gruene_briefwahl_effekt_zweit_pp": "Briefwahl-Effekt Zweit PP",
			"gruene_briefwahl_effekt_erst_pp": "Briefwahl-Effekt Erst PP",
			"mobilisierungsluecke_gruene_stimmen": "Mobilisierungsluecke Stimmen",
		}
	)
	st.dataframe(strategy_table.sort_values("Cem-Bonus PP", ascending=False), use_container_width=True)


def render_competition_tab(summary: pd.Series, compare_party: str) -> None:
	compare_label = DISPLAY_PARTY_NAMES.get(compare_party, compare_party)
	st.subheader(f"Gruene im Vergleich zu {compare_label}")
	metric_row = st.columns(4)
	metric_row[0].metric("Gruene Erststimme", format_pct(summary["gruene_erst_pct"]))
	metric_row[1].metric(f"{compare_label} Erststimme", format_pct(summary.get(f"erst_{compare_party}_pct", 0.0)))
	metric_row[2].metric("Gruene Zweitstimme", format_pct(summary["gruene_zweit_pct"]))
	metric_row[3].metric(f"{compare_label} Zweitstimme", format_pct(summary.get(f"zweit_{compare_party}_pct", 0.0)))

	compare_frame = pd.DataFrame(
		[
			{
				"Stimmart": "Erststimme",
				"Gruene": summary["gruene_erst_pct"],
				compare_label: summary.get(f"erst_{compare_party}_pct", 0.0),
			},
			{
				"Stimmart": "Zweitstimme",
				"Gruene": summary["gruene_zweit_pct"],
				compare_label: summary.get(f"zweit_{compare_party}_pct", 0.0),
			},
		]
	)
	melted = compare_frame.melt(id_vars="Stimmart", var_name="Partei", value_name="Anteil")
	fig = px.bar(
		melted,
		x="Stimmart",
		y="Anteil",
		color="Partei",
		barmode="group",
		color_discrete_sequence=["#16803c", "#c94f4f"],
	)
	fig.update_layout(margin={"r": 0, "t": 20, "l": 0, "b": 0}, yaxis_title="Anteil in %")
	st.plotly_chart(fig, use_container_width=True)

	gap_frame = pd.DataFrame(
		[
			{
				"Stimmart": "Erststimme",
				"Differenz": summary["gruene_erst_pct"] - summary.get(f"erst_{compare_party}_pct", 0.0),
			},
			{
				"Stimmart": "Zweitstimme",
				"Differenz": summary["gruene_zweit_pct"] - summary.get(f"zweit_{compare_party}_pct", 0.0),
			},
		]
	)
	gap_fig = px.bar(
		gap_frame,
		x="Stimmart",
		y="Differenz",
		color="Differenz",
		color_continuous_scale="RdYlGn",
		labels={"Differenz": "Gruene minus Vergleichspartei in PP"},
	)
	gap_fig.update_layout(margin={"r": 0, "t": 20, "l": 0, "b": 0}, yaxis_title="Differenz in PP")
	st.plotly_chart(gap_fig, use_container_width=True)


def render_data_tab(frame: gpd.GeoDataFrame) -> None:
	data_frame = ensure_strategy_columns(frame)
	data_frame = data_frame[[
		"bezirk_label",
		"bezirk_name",
		"Wahlberechtigte gesamt (A)",
		"Waehler gesamt (B)",
		"wahlbeteiligung_pct",
		"D1",
		"F1",
		"gruene_erst_pct",
		"gruene_zweit_pct",
		"gruene_zu_cdu_zweit_pp",
		"cem_bonus_pp",
	]].copy()
	st.dataframe(data_frame.sort_values("bezirk_label"), use_container_width=True)
	st.download_button(
		label="Tabelle als CSV herunterladen",
		data=data_frame.to_csv(index=False).encode("utf-8"),
		file_name="dashboard_stuttgart_ost.csv",
		mime="text/csv",
	)


def main() -> None:
	analysis_frames, matched, unmapped = build_analysis_frames()
	scope_results = load_results()
	geometry_catalog, layer_name = load_geometry_catalog()

	render_header(layer_name, len(matched), len(unmapped))

	with st.sidebar:
		st.header("Filter")
		selected_view = st.selectbox("Auswertungsebene", VIEW_OPTIONS, index=0)
		if selected_view == "Gesamtbezirk":
			st.info("Gesamtbezirk aggregiert den Urnenwahlbezirk mit dem zugeordneten Briefwahlbezirk. Offizielle Einzelseiten wie 003-07 zeigen in der Regel nur den Urnen- oder Briefwahlbezirk separat.")
		compare_party_label = st.selectbox(
			"Vergleichspartei",
			list(COMPARE_PARTY_LABELS.keys()),
			index=0,
			key="compare_party_label",
		)
		compare_party = COMPARE_PARTY_LABELS[compare_party_label]
		map_metrics = build_map_metrics(compare_party, selected_view)
		selected_metric = st.selectbox("Kartenmetrik", list(map_metrics.keys()), index=0)
		st.caption(f"Ausgewaehlt: {compare_party_label}")

		st.markdown("---")
		st.write("Datenbasis")
		st.caption(f"Layer: {layer_name}")
		st.caption(f"Geometrien: {len(geometry_catalog[geometry_catalog['view_mode'] == 'Gesamtbezirk'])} Gesamtbezirke")
		st.caption(f"Join-Zeilen: {len(matched)}")
		st.caption(f"Nicht kartierbar: {len(unmapped)}")

	frame = analysis_frames[selected_view].sort_values("bezirk_label").reset_index(drop=True)
	if selected_view == "Gesamtbezirk":
		summary = summarize_frame(scope_results)
	else:
		summary = summarize_frame(scope_results[scope_results["view_mode"] == selected_view])

	if selected_view == "Gesamtbezirk":
		st.caption("Hinweis: Werte in dieser Ansicht sind pro Bezirk als Urnen- und Briefwahlergebnis zusammengefasst.")

	overview_tab, strategy_tab, map_tab, bezirke_tab, competition_tab, data_tab = st.tabs(
		["Uebersicht", "Strategie-KPIs", "Karte", "Bezirke", "Parteienvergleich", "Daten"]
	)

	with overview_tab:
		render_overview(frame, summary, compare_party)
	with strategy_tab:
		render_strategy_tab(frame, analysis_frames, selected_view)
	with map_tab:
		render_map_tab(frame, analysis_frames, selected_view, selected_metric, compare_party)
	with bezirke_tab:
		render_bezirke_tab(frame)
	with competition_tab:
		render_competition_tab(summary, compare_party)
	with data_tab:
		render_data_tab(frame)


if __name__ == "__main__":
	main()
