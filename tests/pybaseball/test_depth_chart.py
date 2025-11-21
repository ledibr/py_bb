from typing import Callable

import pytest

from pybaseball import depth_chart_batting, depth_chart_pitching
from pybaseball.depth_chart import URL


@pytest.fixture(name="sample_batting_html")
def _sample_batting_html(get_data_file_contents: Callable[[str], str]) -> str:
    return get_data_file_contents('depth_chart_batting.html')

@pytest.fixture(name="sample_pitching_html")
def _sample_pitching_html(get_data_file_contents: Callable[[str], str]) -> str:
    return get_data_file_contents('depth_chart_pitching.html')

def test_depth_chart_pitching(bref_get_monkeypatch: Callable, sample_pitching_html: str):
    pitching_url = URL.format(team_abbrev='WSN', team_dashes='washington-nationals', player_type='pitching')

    bref_get_monkeypatch(sample_pitching_html, pitching_url)

    # ensure error is raised if bad level is given
    with pytest.raises(ValueError) as ex_info:
        depth_chart_pitching('WSN', min_level='fake')
    assert str(ex_info.value) == "Invalid value of 'fake'. Values must be a valid member of the enum: Level"

    # spot check status
    depth_chart_result = depth_chart_pitching('WSN')
    assert depth_chart_result[depth_chart_result['Name'] == 'Michael Soroka']["status"].values[0] == "26-man"

def test_depth_chart_batting(bref_get_monkeypatch: Callable, sample_batting_html: str):
    batting_url = URL.format(team_abbrev='WSN', team_dashes='washington-nationals', player_type='batting')

    bref_get_monkeypatch(sample_batting_html, batting_url)

    # ensure error is raised if bad team is given
    with pytest.raises(ValueError) as ex_info:
        depth_chart_batting('FAKE')
    assert str(ex_info.value) == "Supplied team must be an active MLB team."

    depth_chart_result = depth_chart_batting('WSN')

    # spot check status
    assert depth_chart_result[depth_chart_result['Name'] == 'Dylan Crews']["status"].values[0] == "IL-10"
