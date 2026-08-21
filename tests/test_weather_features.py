import pandas as pd

from src.model.features import add_weather_features


def _row(roof, surface, temp, wind):
    return {"roof": roof, "surface": surface, "temp": temp, "wind": wind}


def test_dome_game_gets_neutral_fallback_values():
    df = pd.DataFrame([_row("dome", "fieldturf", None, None)])
    out = add_weather_features(df)
    row = out.iloc[0]
    assert row["is_outdoor"] == 0.0
    assert row["temp_outdoor"] == 70.0
    assert row["wind_outdoor"] == 0.0
    assert row["is_grass"] == 0.0


def test_closed_roof_is_treated_as_indoor():
    df = pd.DataFrame([_row("closed", "fieldturf", None, None)])
    out = add_weather_features(df)
    assert out.iloc[0]["is_outdoor"] == 0.0


def test_outdoor_game_keeps_its_real_temp_and_wind():
    df = pd.DataFrame([_row("outdoors", "grass", 42.0, 8.0)])
    out = add_weather_features(df)
    row = out.iloc[0]
    assert row["is_outdoor"] == 1.0
    assert row["temp_outdoor"] == 42.0
    assert row["wind_outdoor"] == 8.0
    assert row["is_grass"] == 1.0


def test_open_roof_is_treated_as_outdoor():
    df = pd.DataFrame([_row("open", "grass", 55.0, 5.0)])
    out = add_weather_features(df)
    assert out.iloc[0]["is_outdoor"] == 1.0


def test_outdoor_game_with_genuinely_missing_temp_falls_back_to_neutral():
    # A real gap flagged in the docstring: outdoor + missing temp is
    # distinct from indoor, but gets the same 70/0 fallback in this v1.
    df = pd.DataFrame([_row("outdoors", "grass", None, None)])
    out = add_weather_features(df)
    row = out.iloc[0]
    assert row["is_outdoor"] == 1.0
    assert row["temp_outdoor"] == 70.0
    assert row["wind_outdoor"] == 0.0


def test_surface_whitespace_inconsistency_is_normalized():
    df = pd.DataFrame([_row("outdoors", "grass ", 50.0, 5.0), _row("outdoors", "grass", 50.0, 5.0)])
    out = add_weather_features(df)
    assert (out["is_grass"] == 1.0).all()


def test_turf_surfaces_are_not_counted_as_grass():
    df = pd.DataFrame([_row("dome", surf, None, None) for surf in ["fieldturf", "matrixturf", "astroturf", "sportturf", "a_turf"]])
    out = add_weather_features(df)
    assert (out["is_grass"] == 0.0).all()
