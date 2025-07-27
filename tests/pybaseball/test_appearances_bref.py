from typing import Callable

import pytest

from pybaseball.appearances_bref import URL, appearances_bref


@pytest.fixture(name="sample_html")
def _sample_html(get_data_file_contents: Callable[[str], str]) -> str:
    return get_data_file_contents('appearances_bref.html')

def test_appearance(bref_get_monkeypatch: Callable, sample_html: str) -> None:
    url = URL.format(year=1913)

    bref_get_monkeypatch(sample_html, url)

    with pytest.raises(ValueError) as ex_info:
        appearances_bref(1870)
    assert str(ex_info.value).startswith('This query currently only returns appearances until the 1871 season.')

    appearances_result = appearances_bref(1913)

    # test awards column
    assert appearances_result[appearances_result["Player"] == "Walter Johnson"]["Awards"].values[0] == \
           "MVP-1"

    # test specific value in results
    assert appearances_result[appearances_result["Player"] == "Harry Lord"]["3B"].values[0] == "150"