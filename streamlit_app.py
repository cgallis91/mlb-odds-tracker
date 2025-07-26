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
    """Get MLB data with FanDuel odds for today and tomorrow"""
    
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
    
    # Get today and tomorrow in ET timezone
    et = timezone('US/Eastern')
    now_et = datetime.now(et)
    today = now_et.strftime("%Y-%m-%d")
    tomorrow = (now_et + timedelta(days=1)).strftime("%Y-%m-%d")
    
    debug_log.append(f"📅 Today (ET): {today}")
    debug_log.append(f"📅 Tomorrow (ET): {tomorrow}")
    
    all_games = []
    
    # Process both today and tomorrow
    for date_str in [today, tomorrow]:
        debug_log.append(f"\n{'='*50}")
        debug_log.append(f"📅 PROCESSING DATE: {date_str}")
        debug_log.append(f"{'='*50}")
        
        try:
            # Step 1: Get list of games for this date
            main_url = f"https://www.sportsbookreview.com/betting-odds/mlb-baseball/?date={date_str}"
            debug_log.append(f"📡 Main page URL: {main_url}")
            
            response = session.get(main_url, timeout=15)
            debug_log.append(f"📊 Response status: {response.status_code}")
            
            if response.status_code == 200:
                # Extract JSON data
                pattern = r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'
                match = re.search(pattern, response.text, re.DOTALL)
                
                if match:
                    json_data = json.loads(match.group(1))
                    debug_log.append("✅ Found JSON data in main page")
                    
                    # Navigate to games
                    try:
                        odds_tables = json_data['props']['pageProps']['oddsTables']
                        if odds_tables and len(odds_tables) > 0:
                            odds_table_model = odds_tables[0]['oddsTableModel']
                            game_rows = odds_table_model.get('gameRows', [])
                            
                            debug_log.append(f"🎮 Found {len(game_rows)} games for {date_str}")
                            
                            if len(game_rows) == 0:
                                debug_log.append(f"⚠️  No games scheduled for {date_str}")
                                continue
                            
                            # Step 2: Get FanDuel data for each game
                            for i, game in enumerate(game_rows):
                                try:
                                    game_view = game.get('gameView', {})
                                    away_team = game_view.get('awayTeam', {})
                                    home_team = game_view.get('homeTeam', {})
                                    
                                    away_name = away_team.get('name', 'Unknown')
                                    home_name = home_team.get('name', 'Unknown')
                                    game_id = game_view.get('gameId')
                                    start_date = game_view.get('startDate', 'TBD')
                                    venue = game_view.get('venueName', 'Unknown')
                                    
                                    debug_log.append(f"\n🏟️  Game {i+1}/{len(game_rows)}: {away_name} @ {home_name}")
                                    debug_log.append(f"   🆔 Game ID: {game_id}")
                                    debug_log.append(f"   🕐 Start: {start_date}")
                                    debug_log.append(f"   🏟️  Venue: {venue}")
                                    
                                    if game_id:
                                        # Get FanDuel data from line history page
                                        line_history_url = f"https://www.sportsbookreview.com/betting-odds/mlb-baseball/line-history/{game_id}/"
                                        debug_log.append(f"   📈 Fetching: {line_history_url}")
                                        
                                        # Add delay to be respectful
                                        time.sleep(random.uniform(0.2, 0.5))
                                        
                                        line_response = session.get(line_history_url, timeout=10)
                                        debug_log.append(f"   📊 Line history response: {line_response.status_code}")
                                        
                                        if line_response.status_code == 200:
                                            line_match = re.search(pattern, line_response.text, re.DOTALL)
                                            
                                            if line_match:
                                                line_json = json.loads(line_match.group(1))
                                                debug_log.append("   ✅ Found JSON in line history page")
                                                
                                                # Navigate to FanDuel data using the CORRECT structure from the source view
                                                try:
                                                    page_props = line_json['props']['pageProps']
                                                    debug_log.append(f"      🔍 Page props keys: {list(page_props.keys())}")
                                                    
                                                    line_history_model = page_props.get('lineHistoryModel', {})
                                                    debug_log.append(f"      🔍 Line history model keys: {list(line_history_model.keys())}")
                                                    
                                                    # The structure doesn't have oddsViews at the top level - let's search deeper
                                                    odds_views = []
                                                    
                                                    # First try the expected location
                                                    top_level_odds_views = line_history_model.get('oddsViews', [])
                                                    
                                                    # Then try looking in lineHistory
                                                    line_history = line_history_model.get('lineHistory', {})
                                                    line_history_odds_views = line_history.get('oddsViews', []) if line_history else []
                                                    
                                                    # Use whichever one has data
                                                    if top_level_odds_views:
                                                        odds_views = top_level_odds_views
                                                        debug_log.append(f"      🎯 Found oddsViews at top level with {len(odds_views)} sportsbooks")
                                                    elif line_history_odds_views:
                                                        odds_views = line_history_odds_views  
                                                        debug_log.append(f"      🎯 Found oddsViews in lineHistory with {len(odds_views)} sportsbooks")
                                                    else:
                                                        # If neither location has it, do a recursive search
                                                        debug_log.append(f"      🔍 No oddsViews found in expected locations, searching recursively...")
                                                        
                                                        def find_odds_views_recursive(obj, path=""):
                                                            if isinstance(obj, dict):
                                                                if 'oddsViews' in obj and isinstance(obj['oddsViews'], list):
                                                                    return obj['oddsViews'], path + ".oddsViews"
                                                                for key, value in obj.items():
                                                                    result, found_path = find_odds_views_recursive(value, path + f".{key}")
                                                                    if result:
                                                                        return result, found_path
                                                            elif isinstance(obj, list):
                                                                for i, item in enumerate(obj):
                                                                    result, found_path = find_odds_views_recursive(item, path + f"[{i}]")
                                                                    if result:
                                                                        return result, found_path
                                                            return None, ""
                                                        
                                                        found_odds_views, found_path = find_odds_views_recursive(line_json)
                                                        if found_odds_views:
                                                            odds_views = found_odds_views
                                                            debug_log.append(f"      🎯 Found oddsViews via recursive search at: {found_path}")
                                                            debug_log.append(f"      🎯 Contains {len(odds_views)} sportsbooks!")
                                                        else:
                                                            debug_log.append(f"      ❌ No oddsViews found anywhere in JSON")
                                                    
                                                    debug_log.append(f"      🔍 Final odds_views length: {len(odds_views)}")
                                                    
                                                    # Debug: show first few sportsbooks if found
                                                    if odds_views:
                                                        for i, view in enumerate(odds_views[:3]):  # Show first 3
                                                            sb_name = view.get('sportsbook', 'Unknown')
                                                            debug_log.append(f"      📖 Sportsbook {i}: {sb_name}")
                                                    
                                                    # Find FanDuel data
                                                    fanduel_data = None
                                                    available_books = []
                                                    
                                                    for j, view in enumerate(odds_views):
                                                        sportsbook = view.get('sportsbook', '').lower()
                                                        available_books.append(sportsbook)
                                                        
                                                        if sportsbook == 'fanduel':
                                                            fanduel_data = view
                                                            debug_log.append(f"      🎯 FOUND FANDUEL DATA!")
                                                            
                                                            # Show what data we found
                                                            ml_history = fanduel_data.get('moneyLineHistory', [])
                                                            spread_history = fanduel_data.get('spreadHistory', [])
                                                            total_history = fanduel_data.get('totalHistory', [])
                                                            
                                                            debug_log.append(f"      📊 ML history: {len(ml_history)} entries")
                                                            debug_log.append(f"      📊 Spread history: {len(spread_history)} entries")
                                                            debug_log.append(f"      📊 Total history: {len(total_history)} entries")
                                                            
                                                            if ml_history:
                                                                debug_log.append(f"      📊 Sample ML data: {ml_history[0]}")
                                                            if spread_history:
                                                                debug_log.append(f"      📊 Sample spread data: {spread_history[0]}")
                                                            if total_history:
                                                                debug_log.append(f"      📊 Sample total data: {total_history[0]}")
                                                            break
                                                    
                                                    debug_log.append(f"   📚 Available sportsbooks: {available_books}")
                                                    
                                                    if not fanduel_data and odds_views:
                                                        debug_log.append(f"      ❌ FanDuel not found in available sportsbooks: {available_books}")
                                                    elif not odds_views:
                                                        debug_log.append(f"      ❌ No oddsViews found at all in this game's JSON")
                                                    
                                                    if fanduel_data:
                                                        # Extract odds histories
                                                        ml_history = fanduel_data.get('moneyLineHistory', [])
                                                        spread_history = fanduel_data.get('spreadHistory', [])
                                                        total_history = fanduel_data.get('totalHistory', [])
                                                        
                                                        debug_log.append(f"      💰 Moneyline entries: {len(ml_history)}")
                                                        debug_log.append(f"      💨 Spread entries: {len(spread_history)}")
                                                        debug_log.append(f"      🎯 Total entries: {len(total_history)}")
                                                        
                                                        # Extract the opening and current (last) odds for moneyline
                                                        def get_open_current(history, team_key):
                                                            # history is list of dicts with 'moneyLine' key and 'team'
                                                            # We want the earliest and latest moneyline for the given team_key
                                                            filtered = [h for h in history if h.get('team') == team_key]
                                                            if not filtered:
                                                                return None, None
                                                            # Sort by timestamp
                                                            filtered = sorted(filtered, key=lambda x: x.get('timeStamp', 0))
                                                            open_val = filtered[0].get('moneyLine')
                                                            current_val = filtered[-1].get('moneyLine')
                                                            return open_val, current_val
                                                        
                                                        ml_open_away, ml_current_away = get_open_current(ml_history, 'away')
                                                        ml_open_home, ml_current_home = get_open_current(ml_history, 'home')
                                                        
                                                        # Extract opening and current run line spreads and odds
                                                        def get_spread_open_current(history, team_key):
                                                            filtered = [h for h in history if h.get('team') == team_key]
                                                            if not filtered:
                                                                return (None, None), (None, None)
                                                            filtered = sorted(filtered, key=lambda x: x.get('timeStamp', 0))
                                                            open_spread = filtered[0].get('spread')
                                                            open_odds = filtered[0].get('moneyLine')
                                                            current_spread = filtered[-1].get('spread')
                                                            current_odds = filtered[-1].get('moneyLine')
                                                            return (open_spread, open_odds), (current_spread, current_odds)
                                                        
                                                        rl_open_away, rl_current_away = get_spread_open_current(spread_history, 'away')
                                                        rl_open_home, rl_current_home = get_spread_open_current(spread_history, 'home')
                                                        
                                                        # Extract totals open/current
                                                        def get_total_open_current(history):
                                                            if not history:
                                                                return (None, None, None, None)
                                                            history = sorted(history, key=lambda x: x.get('timeStamp', 0))
                                                            open_line = history[0].get('totalLine')
                                                            open_over_odds = history[0].get('overOdds')
                                                            open_under_odds = history[0].get('underOdds')
                                                            current_line = history[-1].get('totalLine')
                                                            current_over_odds = history[-1].get('overOdds')
                                                            current_under_odds = history[-1].get('underOdds')
                                                            return (open_line, open_over_odds, open_under_odds, current_line, current_over_odds, current_under_odds)
                                                        
                                                        (total_open_line, total_open_over_odds, total_open_under_odds,
                                                         total_current_line, total_current_over_odds, total_current_under_odds) = get_total_open_current(total_history)
                                                        
                                                        # Store all extracted info for display
                                                        game_entry = {
                                                            'away_team': away_name,
                                                            'home_team': home_name,
                                                            'venue': venue,
                                                            'game_time': start_date,
                                                            'ml_opening_away': ml_open_away,
                                                            'ml_current_away': ml_current_away,
                                                            'ml_opening_home': ml_open_home,
                                                            'ml_current_home': ml_current_home,
                                                            'rl_opening_away_spread': rl_open_away[0],
                                                            'rl_opening_away_odds': rl_open_away[1],
                                                            'rl_current_away_spread': rl_current_away[0],
                                                            'rl_current_away_odds': rl_current_away[1],
                                                            'rl_opening_home_spread': rl_open_home[0],
                                                            'rl_opening_home_odds': rl_open_home[1],
                                                            'rl_current_home_spread': rl_current_home[0],
                                                            'rl_current_home_odds': rl_current_home[1],
                                                            'total_opening_line': total_open_line,
                                                            'total_opening_over_odds': total_open_over_odds,
                                                            'total_opening_under_odds': total_open_under_odds,
                                                            'total_current_line': total_current_line,
                                                            'total_current_over_odds': total_current_over_odds,
                                                            'total_current_under_odds': total_current_under_odds,
                                                        }
                                                        
                                                        all_games.append(game_entry)
                                                    else:
                                                        debug_log.append(f"   ⚠️ No FanDuel data for this game.")
                                                except Exception as e:
                                                    debug_log.append(f"   ❌ Error processing JSON: {e}")
                                            else:
                                                debug_log.append(f"   ❌ No JSON found on line history page")
                                        else:
                                            debug_log.append(f"   ❌ Failed to fetch line history page.")
                                    else:
                                        debug_log.append(f"   ❌ No game ID available.")
                                except Exception as e:
                                    debug_log.append(f"   ❌ Error processing game: {e}")
                        else:
                            debug_log.append("⚠️ No oddsTables or gameRows data found.")
                    except Exception as e:
                        debug_log.append(f"❌ Error parsing main JSON: {e}")
                else:
                    debug_log.append("❌ No JSON data found on main page.")
            else:
                debug_log.append(f"❌ Failed to fetch main page.")
        except Exception as e:
            debug_log.append(f"❌ Exception during data retrieval: {e}")
    
    # Return all games and debug log
    return all_games, debug_log

def format_odds(value):
    """Format moneyline odds integer to string with sign"""
    if value is None:
        return "-"
    try:
        iv = int(value)
        return f"{iv:+d}"
    except:
        return str(value)

def format_spread(value):
    """Format spread float or int to string with sign"""
    if value is None:
        return "-"
    try:
        fv = float(value)
        if fv == 0:
            return "PK"
        else:
            return f"{fv:+g}"
    except:
        return str(value)

def format_total(value):
    """Format total line float or int to string"""
    if value is None:
        return "-"
    try:
        fv = float(value)
        if fv.is_integer():
            return f"{int(fv)}"
        else:
            return f"{fv:g}"
    except:
        return str(value)

def format_game_time(time_str):
    """Convert ISO time string to readable ET time"""
    try:
        dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        et = dt.astimezone(timezone('US/Eastern'))
        return et.strftime("%I:%M %p ET")
    except:
        return time_str

def display_game_card(game):
    """Display a single game with odds in a styled card"""
    away = game['away_team']
    home = game['home_team']
    venue = game['venue']
    game_time = format_game_time(game['game_time'])

    # Totals: Over and Under line/odds (open and current)
    total_open_over = f"Over {format_total(game['total_opening_line'])} ({format_odds(game['total_opening_over_odds'])})"
    total_current_over = f"Over {format_total(game['total_current_line'])} ({format_odds(game['total_current_over_odds'])})"
    total_open_under = f"Under {format_total(game['total_opening_line'])} ({format_odds(game['total_opening_under_odds'])})"
    total_current_under = f"Under {format_total(game['total_current_line'])} ({format_odds(game['total_current_under_odds'])})"

    # Run line formatting for away and home (spread + odds)
    rl_open_away = f"{format_spread(game['rl_opening_away_spread'])} ({format_odds(game['rl_opening_away_odds'])})"
    rl_current_away = f"{format_spread(game['rl_current_away_spread'])} ({format_odds(game['rl_current_away_odds'])})"
    rl_open_home = f"{format_spread(game['rl_opening_home_spread'])} ({format_odds(game['rl_opening_home_odds'])})"
    rl_current_home = f"{format_spread(game['rl_current_home_spread'])} ({format_odds(game['rl_current_home_odds'])})"

    # Moneyline open/current for away and home
    ml_open_away = format_odds(game['ml_opening_away'])
    ml_current_away = format_odds(game['ml_current_away'])
    ml_open_home = format_odds(game['ml_opening_home'])
    ml_current_home = format_odds(game['ml_current_home'])

    card_md = f"""
<div style="
    border: 2px solid #1f77b4; 
    border-radius: 12px; 
    padding: 16px; 
    margin-bottom: 24px;
    background: #f8f9fa;
    max-width: 720px;
    font-family: Arial, sans-serif;
">

  <h2 style="margin-bottom: 4px; color: #1f77b4; font-weight: bold;">
    {away} at {home}
  </h2>

  <p style="margin-top: 0; margin-bottom: 16px; font-style: italic; color: #555;">
    {venue} &nbsp;&nbsp;&nbsp; {game_time}
  </p>

  <table style="width: 100%; border-collapse: collapse; text-align: center; font-size: 14px;">
    <thead style="background-color: #e9ecef;">
      <tr>
        <th rowspan="2" style="border: 1px solid #ccc; padding: 8px;">Team</th>
        <th colspan="2" style="border: 1px solid #ccc; padding: 8px;">Moneyline</th>
        <th colspan="2" style="border: 1px solid #ccc; padding: 8px;">Run Line</th>
        <th colspan="2" style="border: 1px solid #ccc; padding: 8px;">Total</th>
      </tr>
      <tr>
        <th style="border: 1px solid #ccc; padding: 6px;">Open</th>
        <th style="border: 1px solid #ccc; padding: 6px;">Current</th>
        <th style="border: 1px solid #ccc; padding: 6px;">Open</th>
        <th style="border: 1px solid #ccc; padding: 6px;">Current</th>
        <th style="border: 1px solid #ccc; padding: 6px;">Open</th>
        <th style="border: 1px solid #ccc; padding: 6px;">Current</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td style="border: 1px solid #ccc; padding: 8px; font-weight: bold;">{away}</td>
        <td style="border: 1px solid #ccc; padding: 8px;">{ml_open_away}</td>
        <td style="border: 1px solid #ccc; padding: 8px;">{ml_current_away}</td>
        <td style="border: 1px solid #ccc; padding: 8px;">{rl_open_away}</td>
        <td style="border: 1px solid #ccc; padding: 8px;">{rl_current_away}</td>
        <td rowspan="2" style="border: 1px solid #ccc; padding: 8px; vertical-align: middle; font-size: 13px;">
          {total_open_over}<br>
          {total_open_under}
        </td>
        <td rowspan="2" style="border: 1px solid #ccc; padding: 8px; vertical-align: middle; font-size: 13px;">
          {total_current_over}<br>
          {total_current_under}
        </td>
      </tr>
      <tr>
        <td style="border: 1px solid #ccc; padding: 8px; font-weight: bold;">{home}</td>
        <td style="border: 1px solid #ccc; padding: 8px;">{ml_open_home}</td>
        <td style="border: 1px solid #ccc; padding: 8px;">{ml_current_home}</td>
        <td style="border: 1px solid #ccc; padding: 8px;">{rl_open_home}</td>
        <td style="border: 1px solid #ccc; padding: 8px;">{rl_current_home}</td>
      </tr>
    </tbody>
  </table>
</div>
"""

    st.markdown(card_md, unsafe_allow_html=True)

def main():
    st.title("⚾ MLB FanDuel Odds Tracker")

    with st.spinner("Fetching FanDuel MLB odds..."):
        games, debug_log = get_fanduel_mlb_data()

    if not games:
        st.warning("No games or odds data found.")
    else:
        for game in games:
            display_game_card(game)

    if st.checkbox("Show Debug Log"):
        st.text("\n".join(debug_log))

if __name__ == "__main__":
    main()
