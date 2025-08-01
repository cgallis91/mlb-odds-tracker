import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests
import re
import json
from pytz import timezone
import time
import random

# Configure page
st.set_page_config(
    page_title="MLB FanDuel Odds Tracker",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def get_fanduel_mlb_data():
    # ...your existing scraping logic here...
    # (This function is unchanged from your original file)
    debug_log = []
    debug_log.append("🎯 Starting FanDuel MLB scraper for today and tomorrow...")
    session = requests.Session()
    session.headers.update({
        'Accept-Encoding': 'identity',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    })
    et = timezone('US/Eastern')
    now_et = datetime.now(et)
    today = now_et.strftime("%Y-%m-%d")
    tomorrow = (now_et + timedelta(days=1)).strftime("%Y-%m-%d")
    debug_log.append(f"📅 Today (ET): {today}")
    debug_log.append(f"📅 Tomorrow (ET): {tomorrow}")
    all_games = []
    # ...rest of your scraping logic...
    # (Copy your full get_fanduel_mlb_data function here)
    # For brevity, not repeated in this snippet

    # At the end, return as before:
    # return pd.DataFrame(all_games), debug_log, True/False

    # (Paste your full function here)

@st.cache_data(ttl=300)
def load_odds_data():
    real_data, debug_log, success = get_fanduel_mlb_data()
    if success and not real_data.empty:
        data_source = "SportsBookReview"
        final_data = real_data
    else:
        data_source = "No Data Found"
        final_data = pd.DataFrame()
    et = timezone('US/Eastern')
    now_et = datetime.now(et)
    today = now_et.strftime("%Y-%m-%d")
    tomorrow = (now_et + timedelta(days=1)).strftime("%Y-%m-%d")
    today_games = final_data[final_data['date'] == today] if not final_data.empty else pd.DataFrame()
    tomorrow_games = final_data[final_data['date'] == tomorrow] if not final_data.empty else pd.DataFrame()
    return {
        'today': today_games,
        'tomorrow': tomorrow_games,
        'today_date': today,
        'tomorrow_date': tomorrow,
        'last_update': now_et,
        'data_source': data_source,
        'debug_log': debug_log,
        'scraper_success': success
    }

def format_odds(odds_value):
    if pd.isna(odds_value) or odds_value is None:
        return ""
    try:
        odds = int(odds_value)
        return f"+{odds}" if odds > 0 else str(odds)
    except (ValueError, TypeError):
        return ""

def format_spread(spread_value):
    if pd.isna(spread_value) or spread_value is None:
        return ""
    try:
        spread = float(spread_value)
        return f"+{spread}" if spread > 0 else str(spread)
    except (ValueError, TypeError):
        return ""

def format_total(total_value):
    if pd.isna(total_value) or total_value is None:
        return ""
    try:
        return f"{float(total_value)}"
    except (ValueError, TypeError):
        return ""

def format_game_time(game_time_str):
    try:
        if 'T' in game_time_str:
            dt = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))
        else:
            return game_time_str
        et = timezone('US/Eastern')
        dt_et = dt.astimezone(et)
        return dt_et.strftime("%I:%M %p ET")
    except:
        return "TBD"

def format_date(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%A, %B %d, %Y")
    except:
        return date_str

def display_game_card(game):
    border_color = "#1f77b4"
    away_team = game.get('away_team', 'Away')
    home_team = game.get('home_team', 'Home')
    venue = game.get('venue', '')
    city = ""  # Add city if available
    game_time = format_game_time(game.get('game_time', 'TBD'))

    def fmt(val, fn=str):
        return "" if pd.isna(val) or val is None else fn(val)

    def run_line(spread, odds):
        s = fmt(spread, format_spread)
        o = fmt(odds, format_odds)
        return f"{s} ({o})" if s and o else ""

    def total_line(total, odds, over=True):
        t = fmt(total, format_total)
        o = fmt(odds, format_odds)
        if not t or not o:
            return ""
        return f"{'Over' if over else 'Under'} {t} ({o})"

    table_html = f"""
    <style>
    .odds-card-table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
        margin-bottom: 0;
        font-size: 1em;
    }}
    .odds-card-table th, .odds-card-table td {{
        border: 1px solid #dee2e6;
        padding: 8px 10px;
        text-align: center;
    }}
    .odds-card-table th {{
        background: #f1f3f4;
        font-weight: bold;
    }}
    .odds-card-table .subcol {{
        font-size: 0.95em;
        color: #888;
        background: #f9f9fa;
    }}
    .odds-card-table tr.team-row td:first-child {{
        font-weight: bold;
        background: #f8fafc;
    }}
    </style>
    <table class="odds-card-table">
        <tr>
            <th rowspan="2">Team</th>
            <th colspan="2">Moneyline</th>
            <th colspan="2">Run Line</th>
            <th colspan="2">Total</th>
        </tr>
        <tr>
            <th class="subcol">Open</th>
            <th class="subcol">Current</th>
            <th class="subcol">Open</th>
            <th class="subcol">Current</th>
            <th class="subcol">Open</th>
            <th class="subcol">Current</th>
        </tr>
        <tr class="team-row">
            <td>{away_team}</td>
            <td>{fmt(game.get('ml_opening_away'), format_odds)}</td>
            <td>{fmt(game.get('ml_current_away'), format_odds)}</td>
            <td>{run_line(game.get('rl_opening_away_spread'), game.get('rl_opening_away_odds'))}</td>
            <td>{run_line(game.get('rl_current_away_spread'), game.get('rl_current_away_odds'))}</td>
            <td>{total_line(game.get('total_opening_line'), game.get('total_opening_over_odds'), over=True)}</td>
            <td>{total_line(game.get('total_current_line'), game.get('total_current_over_odds'), over=True)}</td>
        </tr>
        <tr class="team-row">
            <td>{home_team}</td>
            <td>{fmt(game.get('ml_opening_home'), format_odds)}</td>
            <td>{fmt(game.get('ml_current_home'), format_odds)}</td>
            <td>{run_line(game.get('rl_opening_home_spread'), game.get('rl_opening_home_odds'))}</td>
            <td>{run_line(game.get('rl_current_home_spread'), game.get('rl_current_home_odds'))}</td>
            <td>{total_line(game.get('total_opening_line'), game.get('total_opening_under_odds'), over=False)}</td>
            <td>{total_line(game.get('total_current_line'), game.get('total_current_under_odds'), over=False)}</td>
        </tr>
    </table>
    """

    st.markdown(
        f"""
        <div style="border: 2px solid {border_color}; border-radius: 14px; padding: 22px 24px 18px 24px; margin-bottom: 28px; background: #f8fafc;">
            <div style="font-size: 1.25em; font-weight: bold; margin-bottom: 2px;">
                {away_team} at {home_team}
            </div>
            <div style="color: #444; font-size: 1em; margin-bottom: 10px;">
                {game_time} &nbsp;|&nbsp; {venue}{' | ' + city if city else ''}
            </div>
            {table_html}
        </div>
        """,
        unsafe_allow_html=True
    )

def main():
    st.title("⚾ MLB FanDuel Odds Tracker")

    # Refresh Data button at the top
    if st.button("Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    # Load data with spinner
    with st.spinner("Loading MLB odds..."):
        data = load_odds_data()

    # --- Defensive check for data ---
    if not data or not isinstance(data, dict):
        st.error("Failed to load odds data. Please try refreshing.")
        return

    today_df = data['today']
    tomorrow_df = data['tomorrow']
    today_date = data['today_date']
    tomorrow_date = data['tomorrow_date']
    last_update = data['last_update']

    # Last Update and Source info
    st.markdown(
        f"""
        <div style="background: #f1f3f4; border-radius: 8px; padding: 0.7em 1em; margin-bottom: 1.2em; font-size: 1.05em;">
            <strong>Last Update:</strong> {last_update.strftime('%I:%M %p ET, %B %d, %Y')} &nbsp; | &nbsp;
            <strong>Source:</strong> SportsBookReview
        </div>
        """,
        unsafe_allow_html=True
    )

    # Tabs for today/tomorrow
    tab1, tab2 = st.tabs([
        f"Today's Games - {format_date(today_date)}",
        f"Tomorrow's Games - {format_date(tomorrow_date)}"
    ])

    # Today's games
    with tab1:
        if not today_df.empty:
            for _, game in today_df.iterrows():
                display_game_card(game)
        else:
            st.markdown(
                "<div style='margin: 2em 0; text-align: center; color: #888;'>No games found for today.</div>",
                unsafe_allow_html=True
            )

    # Tomorrow's games
    with tab2:
        if not tomorrow_df.empty:
            for _, game in tomorrow_df.iterrows():
                display_game_card(game)
        else:
            st.markdown(
                "<div style='margin: 2em 0; text-align: center; color: #888;'>No games found for tomorrow.</div>",
                unsafe_allow_html=True
            )

if __name__ == "__main__":
    main()
