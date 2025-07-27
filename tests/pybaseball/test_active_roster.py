from typing import Callable

import pytest

from pybaseball import active_roster
from pybaseball.active_roster import URL

@pytest.fixture(name="sample_html")
def _sample_html(get_data_file_contents: Callable[[str], str]) -> str:
    return get_data_file_contents('active_roster.html')

def test_active_roster(bref_get_monkeypatch: Callable, sample_html: str) -> None:
    url = URL.format(team='WSN', year=2025)

    bref_get_monkeypatch(sample_html, url)

    with pytest.raises(ValueError) as ex_info:
        active_roster('FAKE')
    assert str(ex_info.value) == 'Team must be the three-letter abbreviation of an active MLB team.'

    active_roster_result = active_roster('WSN')

    # make sure IL is populated
    assert active_roster_result[active_roster_result["Name"] == "Cade Cavalli"]["IL"].values[0] == "15-day"

    # make sure a player who hasn't played in the majors has MLB ID set correctly
    assert active_roster_result[active_roster_result["Name"] == "Andry Lara"]["mlb_ID"].values[0]