import re

import pandas as pd
from bs4 import BeautifulSoup, Tag

from . import cache
from .enums.enum_base import EnumBase
from .utils import ACTIVE_TEAMS_MAPPING, ACTIVE_TEAMS, get_bref_table, get_mlbam_id_from_player_link
from .datasources.bref import BRefSession

session = BRefSession()

# level column heading in bref table
LEVEL_HEADING = 'Lev'
NAME_HEADING = 'Name'

# default minimum level for results
DEFAULT_LEVEL = 'MAJ'

# position summary header, with NBSP
POSITION_SUMMARY_NBSP = 'Pos Summary'
POSITION_SUMMARY = 'Pos_Summary'

# ids of tables used on bref
BATTING_TABLE_IDS = ['Catcher', 'Infielder2BSS3B', 'Outfield', 'FirstBaseDesignatedHitterorPinchHitter', 'Utility']
PITCHING_TABLE_IDS = ['Right-HandedStarters', 'Left-HandedStarters', 'Right-HandedRelievers',
                          'Left-HandedRelievers', 'OtherPitcher', 'Closers']

# heading for mlb ID
MLB_ID = 'mlb_ID'

# status constants
STRONG_TAG = 'strong'
SMALL_TAG = 'small'
ACTIVE_ROSTER = '26-man'
FORTY_MAN = '40-man'
IL_60 = 'IL-60'
IL_15 = 'IL-15'
IL_10 = 'IL-10'
IL_7 = 'IL-7'

URL = 'https://www.baseball-reference.com/teams/{team_abbrev}/{team_dashes}-organization-{player_type}.shtml'

# enum representing levels of organized baseball
class Level(EnumBase):
    MAJ = 1
    AAA = 2
    AA = 3
    HIGH_A = 4
    LOW_A = 5
    ROK = 6

# enum name can't have a hyphen in it, so translate here
def level_name(name: str) -> str:
    if name == 'H-A':
        return 'HIGH_A'

    if name == 'L-A':
        return 'LOW_A'

    return name

# get a status string from the player link. indicates 26-man roster, 40-man, or IL
def get_player_status(player_link: Tag) -> str:
    # <strong> parent means on the 26-man roster
    if player_link.parent.name == STRONG_TAG:
        return ACTIVE_ROSTER

    # find the small tag that contains the status
    small_tag = player_link.parent.find(SMALL_TAG)

    if not small_tag:
        return ''

    if '(40-man)' in small_tag.text:
        return FORTY_MAN

    if '(60-day IL)' in small_tag.text:
        return IL_60

    if '(15-day IL)' in small_tag.text:
        return IL_15

    if '(10-day IL)' in small_tag.text:
        return IL_10

    if '(7-day IL)' in small_tag.text:
        return IL_7

    return ''

def get_soup(team: str, player_type: str) -> BeautifulSoup:
    url = URL.format(team_abbrev=team, team_dashes=ACTIVE_TEAMS_MAPPING[team], player_type=player_type)
    s = session.get(url).content
    return BeautifulSoup(s, "lxml")

def get_highest_level(level: str) -> Level:
    # if no comma, we don't need to split
    if ',' not in level:
        return Level.parse(level_name(level))

    levels = [Level.parse(level_name(l)) for l in level.split(',')]

    # sort on numerical value, highest level will be first
    levels.sort(key=lambda x: x.value)

    return levels[0]

def sanitize_player_name(player_name: str) -> str:
    # remove parens and their contents
    player_name = re.sub(r' \(.*\)', '', player_name)

    # remove asterisk
    player_name = player_name.replace('*', '')

    # remove #
    player_name = player_name.replace('#', '')

    # remove comma and render name as First Last
    names = player_name.split(', ')

    return f'{names[1]} {names[0]}'

def process_tables(soup: BeautifulSoup, table_ids: [str], min_level: Level) -> pd.DataFrame:
    data = []

    headings = []

    # index of level and name columns
    lev_index = 0
    name_index = 0

    for table_id in table_ids:

        # get depth chart table
        table = get_bref_table(table_id, soup)

        # skip table if it's not found
        if not table:
            continue

        # headings are always the same, only need to set them once
        if not headings:
            headings = [th.get_text() for th in table.find("tr").find_all("th")]

            # remove the Rk header, it's unnecessary
            headings.pop(0)

            # add column indicating 40-man roster or IL
            headings.append('status')

            # add ID column name and alt url for players that don't have an ID
            headings.append(MLB_ID)

            lev_index = headings.index(LEVEL_HEADING)
            name_index = headings.index(NAME_HEADING)

        # pull in data rows
        table_body = table.find('tbody')
        rows = table_body.find_all('tr')
        for row in rows:
            player_link = row.find('a')
            if not player_link:
                continue

            cols = row.find_all('td')
            cols = [ele.text.strip() for ele in cols]

            # get status string and add to data
            cols.append(get_player_status(player_link))

            # skip if level is not in requested range
            level_str = cols[lev_index]

            # sanitize name and rearrange to fit other bref results
            cols[name_index] = sanitize_player_name(cols[name_index])

            # highest level the player has reached this season
            level = get_highest_level(level_str)
            if level.value > min_level.value:
                continue

            # find mlbam ID in player link and add to data
            cols.append(get_mlbam_id_from_player_link(player_link.get('href')))

            data.append(cols)

    # use headings for column names
    df = pd.DataFrame(data, columns=headings)

    # rename position summary field to use underscore
    df = df.rename(columns={POSITION_SUMMARY_NBSP: POSITION_SUMMARY})

    # remove any duplicates, can happen if a pitcher is listed under relievers and closers for example
    df = df.drop_duplicates(MLB_ID)

    return df

@cache.df_cache()
def depth_chart_batting(team: str, min_level: str = DEFAULT_LEVEL) -> pd.DataFrame:
    """
    Returns a pandas DataFrame of the position players in the system of the specified team. Players returned will
    play at level specified in min_level or above.

    ARGUMENTS
        team (str): the three letter abbreviation of an active MLB team
        min_level (str): minimum level for players to be returned. For example a min_level of 'AA' means major league
            players, AAA players, and AA players will be returned. Default is MAJ, or majors only.
    """

    if not team in ACTIVE_TEAMS:
        raise ValueError(
            "Supplied team must be an active MLB team."
        )

    # retrieve html from baseball reference
    soup = get_soup(team, 'batting')
    df = process_tables(soup, BATTING_TABLE_IDS, Level.parse(level_name(min_level)))
    return df

@cache.df_cache()
def depth_chart_pitching(team: str, min_level: str = DEFAULT_LEVEL) -> pd.DataFrame:
    """
    Returns a pandas DataFrame of the pitchers in the system of the specified team. Players returned will
    play at level specified in min_level or above.

    ARGUMENTS
        team (str): the three letter abbreviation of an active MLB team
        min_level (str): minimum level for players to be returned. For example a min_level of 'AA' means major league
            players, AAA players, and AA players will be returned. Default is MAJ, or majors only.
    """

    if not team in ACTIVE_TEAMS:
        raise ValueError(
            "Supplied team must be an active MLB team."
        )

    # retrieve html from baseball reference
    soup = get_soup(team, 'pitching')
    df = process_tables(soup, PITCHING_TABLE_IDS, Level.parse(level_name(min_level)))
    return df
