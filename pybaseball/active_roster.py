import pandas as pd
from bs4 import BeautifulSoup, Comment

from . import cache
from .utils import most_recent_season, ACTIVE_TEAMS, append_bref_id_or_mlb_id_from_link, get_bref_table
from .datasources.bref import BRefSession

FORTY_MAN_TABLE_ID = 'the40man'

session = BRefSession()

# pylint: disable=line-too-long
URL = "https://www.baseball-reference.com/teams/{team}/{year}.shtml"


def get_soup(team: str) -> BeautifulSoup:
    url = URL.format(team=team, year=most_recent_season())
    s = session.get(url, timeout=None).content
    return  BeautifulSoup(s, "lxml")

def get_tables(soup: BeautifulSoup) -> pd.DataFrame:
    data = []

    # find commented 40-man roster table and parse that
    table = get_bref_table(FORTY_MAN_TABLE_ID, soup)

    headings = [th.get_text() for th in table.find("tr").find_all("th")]

    # remove the Rk header, it's unnecessary
    headings.pop(0)

    # add ID column name
    headings.append('player_ID')
    headings.append('mlb_ID')

    # pull in data rows
    table_body = table.find('tbody')
    rows = table_body.find_all('tr')
    for row in rows:
        player_link = row.find('a')
        if not player_link:
            continue
        cols = row.find_all('td')
        cols = [ele.text.strip() for ele in cols]

        player_link = player_link.get('href')

        # determine whether the player has reached the majors and has a bref ID
        append_bref_id_or_mlb_id_from_link(player_link, cols)

        data.append([ele for ele in cols])

    # use headings for column names
    return pd.DataFrame(data, columns=headings)


@cache.df_cache()
def active_roster(team: str) -> pd.DataFrame:
    """
    Returns a pandas DataFrame of the 40-man roster for a given MLB team

    ARGUMENTS
        team (str): the three-letter bref abbreviation for an active MLB team
    """
    # make sure specified team is active
    if team not in ACTIVE_TEAMS:
        raise ValueError(
            "Team must be the three-letter abbreviation of an active MLB team."
        )

    # retrieve html from baseball reference
    soup = get_soup(team)

    df = get_tables(soup)
    return df
