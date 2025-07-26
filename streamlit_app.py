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
                                                        debug_log.append(f"      🏃 Spread entries: {len(spread_history)}")
                                                        debug_log.append(f"      🎯 Total entries: {len(total_history)}")
                                                        
                                                        # Get opening (first) and current (last) lines
                                                        ml_opening = ml_history[0] if ml_history else {}
                                                        ml_current = ml_history[-1] if ml_history else {}
                                                        
                                                        spread_opening = spread_history[0] if spread_history else {}
                                                        spread_current = spread_history[-1] if spread_history else {}
                                                        
                                                        total_opening = total_history[0] if total_history else {}
                                                        total_current = total_history[-1] if total_history else {}
                                                        
                                                        # Log sample data for debugging
                                                        if ml_opening:
                                                            debug_log.append(f"      📊 ML Opening: Away {ml_opening.get('awayOdds')} | Home {ml_opening.get('homeOdds')}")
                                                        if ml_current:
                                                            debug_log.append(f"      📊 ML Current: Away {ml_current.get('awayOdds')} | Home {ml_current.get('homeOdds')}")
                                                        if spread_opening:
                                                            debug_log.append(f"      📊 Spread Opening: Away {spread_opening.get('awaySpread')} ({spread_opening.get('awayOdds')}) | Home {spread_opening.get('homeSpread')} ({spread_opening.get('homeOdds')})")
                                                        if total_opening:
                                                            debug_log.append(f"      📊 Total Opening: {total_opening.get('total')} - Over {total_opening.get('overOdds')} | Under {total_opening.get('underOdds')}")
                                                        
                                                        # Create game record with sportsbook identifier
                                                        game_info = {
                                                            'date': date_str,
                                                            'away_team': away_name,
                                                            'home_team': home_name,
                                                            'game_time': start_date,
                                                            'venue': venue,
                                                            'game_id': game_id,
                                                            'sportsbook': 'FanDuel',  # Add this to identify source
                                                            
                                                            # Moneyline
                                                            'ml_opening_away': ml_opening.get('awayOdds'),
                                                            'ml_opening_home': ml_opening.get('homeOdds'),
                                                            'ml_current_away': ml_current.get('awayOdds'),
                                                            'ml_current_home': ml_current.get('homeOdds'),
                                                            
                                                            # Run Line (Spread)
                                                            'rl_opening_away_odds': spread_opening.get('awayOdds'),
                                                            'rl_opening_home_odds': spread_opening.get('homeOdds'),
                                                            'rl_opening_away_spread': spread_opening.get('awaySpread'),
                                                            'rl_opening_home_spread': spread_opening.get('homeSpread'),
                                                            'rl_current_away_odds': spread_current.get('awayOdds'),
                                                            'rl_current_home_odds': spread_current.get('homeOdds'),
                                                            'rl_current_away_spread': spread_current.get('awaySpread'),
                                                            'rl_current_home_spread': spread_current.get('homeSpread'),
                                                            
                                                            # Totals
                                                            'total_opening_line': total_opening.get('total'),
                                                            'total_opening_over_odds': total_opening.get('overOdds'),
                                                            'total_opening_under_odds': total_opening.get('underOdds'),
                                                            'total_current_line': total_current.get('total'),
                                                            'total_current_over_odds': total_current.get('overOdds'),
                                                            'total_current_under_odds': total_current.get('underOdds')
                                                        }
                                                        
                                                        debug_log.append(f"      ✅ Successfully extracted FanDuel data for {away_name} @ {home_name}")
                                                        debug_log.append(f"         - Moneyline: {ml_opening.get('awayOdds')}/{ml_opening.get('homeOdds')} → {ml_current.get('awayOdds')}/{ml_current.get('homeOdds')}")
                                                        debug_log.append(f"         - Spread: {spread_opening.get('awaySpread')}/{spread_opening.get('homeSpread')} → {spread_current.get('awaySpread')}/{spread_current.get('homeSpread')}")
                                                        debug_log.append(f"         - Total: {total_opening.get('total')} → {total_current.get('total')}")
                                                        
                                                        all_games.append(game_info)
                                                        
                                                except KeyError as e:
                                                    debug_log.append(f"   ❌ KeyError in line history navigation: {str(e)}")
                                            else:
                                                debug_log.append(f"   ❌ No JSON found in line history page")
                                        else:
                                            debug_log.append(f"   ❌ Bad response for line history: {line_response.status_code}")
                                    else:
                                        debug_log.append(f"   ❌ No game ID found for {away_name} @ {home_name}")
                                        
                                except Exception as e:
                                    debug_log.append(f"   💥 Error processing game {i+1}: {str(e)}")
                                    continue
                        else:
                            debug_log.append(f"❌ No odds tables found for {date_str}")
                    except KeyError as e:
                        debug_log.append(f"❌ KeyError in main page navigation: {str(e)}")
                else:
                    debug_log.append(f"❌ No JSON data found in main page for {date_str}")
            else:
                debug_log.append(f"❌ Bad response for main page {date_str}: {response.status_code}")
                
        except Exception as e:
            debug_log.append(f"❌ Error processing date {date_str}: {str(e)}")
    
    # Final summary
    debug_log.append(f"\n🎉 SCRAPING COMPLETE!")
    debug_log.append(f"📊 Total games found with FanDuel data: {len(all_games)}")
    
    if all_games:
        games_by_date = {}
        for game in all_games:
            date = game['date']
            if date not in games_by_date:
                games_by_date[date] = 0
            games_by_date[date] += 1
        
        for date, count in games_by_date.items():
            debug_log.append(f"   📅 {date}: {count} games")
            
        return pd.DataFrame(all_games), debug_log, True
    else:
        debug_log.append(f"❌ No FanDuel data found for any games")
        return pd.DataFrame(), debug_log, False

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_odds_data():
    """Load FanDuel odds data for today and tomorrow"""
    
    # Try to get real FanDuel data
    real_data, debug_log, success = get_fanduel_mlb_data()
    
    if success and not real_data.empty:
        fanduel_count = len(real_data[real_data.get('sportsbook', '') == 'FanDuel']) if 'sportsbook' in real_data.columns else 0
        total_count = len(real_data)
        
        if fanduel_count > 0:
            data_source = f"🏆 SportsbookReview ({fanduel_count} FanDuel Games Found!)"
        else:
            data_source = f"📊 SportsbookReview ({total_count} Games - No FanDuel Data Yet)"
        
        final_data = real_data
    else:
        data_source = "❌ No Data Found"
        final_data = pd.DataFrame()
    
    # Get current ET time and dates
    et = timezone('US/Eastern')
    now_et = datetime.now(et)
    today = now_et.strftime("%Y-%m-%d")
    tomorrow = (now_et + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Filter data by date
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
    """Format odds with proper +/- signs"""
    if pd.isna(odds_value) or odds_value is None:
        return "N/A"
    try:
        odds = int(odds_value)
        return f"+{odds}" if odds > 0 else str(odds)
    except (ValueError, TypeError):
        return "N/A"

def format_spread(spread_value):
    """Format spread with proper +/- signs"""
    if pd.isna(spread_value) or spread_value is None:
        return "N/A"
    try:
        spread = float(spread_value)
        return f"+{spread}" if spread > 0 else str(spread)
    except (ValueError, TypeError):
        return "N/A"

def format_total(total_value):
    """Format total line"""
    if pd.isna(total_value) or total_value is None:
        return "N/A"
    try:
        # Check if total is an integer or float
        if total_value == int(total_value):
            return f"{int(total_value)}"
        else:
            return f"{float(total_value)}"
    except (ValueError, TypeError):
        return "N/A"

def format_game_time(game_time_str):
    """Format game time to ET"""
    try:
        # Handle various datetime formats
        if 'T' in game_time_str:
            # ISO format
            dt = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))
        else:
            # Fallback for other potential formats if needed, or just return as is if not parseable
            return game_time_str
            
        et = timezone('US/Eastern')
        dt_et = dt.astimezone(et)
        return dt_et.strftime("%I:%M %p ET")
    except:
        return "TBD"

def calculate_line_movement(opening, current):
    """Calculate line movement with color coding"""
    if pd.isna(opening) or opening is None or pd.isna(current) or current is None:
        return "N/A", "#666666" # Grey for N/A
    try:
        opening_val = float(opening)
        current_val = float(current)
        
        diff = current_val - opening_val
        
        # Use a small epsilon for floating point comparisons
        if abs(diff) < 0.001: 
            return "No Change", "#666666" # Grey
        elif diff > 0:
            return f"+{diff:.0f}", "#28a745"  # Green
        else:
            return f"{diff:.0f}", "#dc3545"   # Red
    except (ValueError, TypeError):
        return "N/A", "#666666"

def get_movement_class(opening, current):
    """Returns CSS class based on line movement."""
    _, color_hex = calculate_line_movement(opening, current)
    if color_hex == "#28a745": # Green
        return "movement-positive"
    elif color_hex == "#dc3545": # Red
        return "movement-negative"
    else: # Grey
        return "movement-neutral"

def display_game_card(game):
    """Display a single game with odds (FanDuel preferred) in a structured card format."""
    
    sportsbook = game.get('sportsbook', 'FanDuel')
    border_color = "#1f77b4" if sportsbook == 'FanDuel' else "#ff6b35"
    
    game_time_formatted = format_game_time(game['game_time'])
    venue = game['venue']

    card_html = f"""
    <div style="border: 2px solid {border_color}; border-radius: 12px; padding: 24px; margin-bottom: 24px; 
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h3 style="margin-top: 0; color: {border_color}; font-weight: bold; font-size: 1.5em;">
            {game['away_team']} @ {game['home_team']}
        </h3>
        <p style="color: #666; margin-bottom: 20px; font-size: 16px;">
            <strong>🏟️ {venue}</strong> • <strong>⏰ {game_time_formatted}</strong>
        </p>

        <style>
            .odds-table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
                font-size: 0.9em; /* Slightly smaller font for table content */
            }}
            .odds-table th, .odds-table td {{
                border: 1px solid #e0e0e0; /* Lighter border for inner table */
                padding: 8px 6px;
                text-align: center;
                vertical-align: top;
            }}
            .odds-table th {{
                background-color: #f2f2f2;
                font-weight: bold;
                color: #333;
                position: sticky;
                top: 0;
                z-index: 1; /* Stay on top when scrolling within the card */
            }}
            .odds-table thead th:first-child {{
                text-align: left; /* Align Team heading left */
            }}
            .odds-table tbody td:first-child {{
                text-align: left; /* Align team names left */
                font-weight: bold;
                color: #444;
            }}
            .odds-table .odds-pair {{
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 2px; /* Smaller gap for compact display */
            }}
            .odds-table .line-value {{
                font-weight: bold;
                color: #1f77b4; /* FanDuel blue */
                font-size: 1.1em;
            }}
            .movement-positive {{ color: #28a745; font-weight: bold; font-size: 0.8em; }} /* Green */
            .movement-negative {{ color: #dc3545; font-weight: bold; font-size: 0.8em; }} /* Red */
            .movement-neutral {{ color: #666666; font-size: 0.8em; }} /* Grey */
            @media (max-width: 768px) {{
                .odds-table {{
                    font-size: 0.75em; /* Even smaller font on mobile */
                }}
                .odds-table th, .odds-table td {{
                    padding: 6px 4px;
                }}
            }}
        </style>

        <table class="odds-table">
            <thead>
                <tr>
                    <th rowspan="2">Team</th>
                    <th colspan="2">Moneyline</th>
                    <th colspan="2">Run Line</th>
                    <th colspan="2">Total</th>
                </tr>
                <tr>
                    <th>Opening</th>
                    <th>Current</th>
                    <th>Opening</th>
                    <th>Current</th>
                    <th>Opening</th>
                    <th>Current</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>{game['away_team']}</td>
                    <td>
                        <div class="odds-pair">
                            <span>{format_odds(game['ml_opening_away'])}</span>
                        </div>
                    </td>
                    <td>
                        <div class="odds-pair">
                            <span>{format_odds(game['ml_current_away'])}</span>
                            <span class="{get_movement_class(game['ml_opening_away'], game['ml_current_away'])}">{calculate_line_movement(game['ml_opening_away'], game['ml_current_away'])[0]}</span>
                        </div>
                    </td>
                    <td>
                        <div class="odds-pair">
                            <span>{format_spread(game['rl_opening_away_spread'])}</span>
                            <span>({format_odds(game['rl_opening_away_odds'])})</span>
                        </div>
                    </td>
                    <td>
                        <div class="odds-pair">
                            <span>{format_spread(game['rl_current_away_spread'])}</span>
                            <span>({format_odds(game['rl_current_away_odds'])})</span>
                            <span class="{get_movement_class(game['rl_opening_away_odds'], game['rl_current_away_odds'])}">{calculate_line_movement(game['rl_opening_away_odds'], game['rl_current_away_odds'])[0]}</span>
                        </div>
                    </td>
                    <td>
                        <div class="odds-pair">
                            <span class="line-value">O/U {format_total(game['total_opening_line'])}</span>
                            <span>O: {format_odds(game['total_opening_over_odds'])}</span>
                            <span>U: {format_odds(game['total_opening_under_odds'])}</span>
                        </div>
                    </td>
                    <td>
                        <div class="odds-pair">
                            <span class="line-value">O/U {format_total(game['total_current_line'])}</span>
                            <span>O: {format_odds(game['total_current_over_odds'])}</span>
                            <span>U: {format_odds(game['total_current_under_odds'])}</span>
                            <span class="{get_movement_class(game['total_opening_line'], game['total_current_line'])}">{calculate_line_movement(game['total_opening_line'], game['total_current_line'])[0]} (Line)</span>
                            <span class="{get_movement_class(game['total_opening_over_odds'], game['total_current_over_odds'])}">{calculate_line_movement(game['total_opening_over_odds'], game['total_current_over_odds'])[0]} (O Odds)</span>
                            <span class="{get_movement_class(game['total_opening_under_odds'], game['total_current_under_odds'])}">{calculate_line_movement(game['total_opening_under_odds'], game['total_current_under_odds'])[0]} (U Odds)</span>
                        </div>
                    </td>
                </tr>
                <tr>
                    <td>{game['home_team']}</td>
                    <td>
                        <div class="odds-pair">
                            <span>{format_odds(game['ml_opening_home'])}</span>
                        </div>
                    </td>
                    <td>
                        <div class="odds-pair">
                            <span>{format_odds(game['ml_current_home'])}</span>
                            <span class="{get_movement_class(game['ml_opening_home'], game['ml_current_home'])}">{calculate_line_movement(game['ml_opening_home'], game['ml_current_home'])[0]}</span>
                        </div>
                    </td>
                    <td>
                        <div class="odds-pair">
                            <span>{format_spread(game['rl_opening_home_spread'])}</span>
                            <span>({format_odds(game['rl_opening_home_odds'])})</span>
                        </div>
                    </td>
                    <td>
                        <div class="odds-pair">
                            <span>{format_spread(game['rl_current_home_spread'])}</span>
                            <span>({format_odds(game['rl_current_home_odds'])})</span>
                            <span class="{get_movement_class(game['rl_opening_home_odds'], game['rl_current_home_odds'])}">{calculate_line_movement(game['rl_opening_home_odds'], game['rl_current_home_odds'])[0]}</span>
                        </div>
                    </td>
                     <td>
                        <div class="odds-pair">
                            <span class="line-value">O/U {format_total(game['total_opening_line'])}</span>
                            <span>O: {format_odds(game['total_opening_over_odds'])}</span>
                            <span>U: {format_odds(game['total_opening_under_odds'])}</span>
                        </div>
                    </td>
                    <td>
                        <div class="odds-pair">
                            <span class="line-value">O/U {format_total(game['total_current_line'])}</span>
                            <span>O: {format_odds(game['total_current_over_odds'])}</span>
                            <span>U: {format_odds(game['total_current_under_odds'])}</span>
                            <span class="{get_movement_class(game['total_opening_line'], game['total_current_line'])}">{calculate_line_movement(game['total_opening_line'], game['total_current_line'])[0]} (Line)</span>
                            <span class="{get_movement_class(game['total_opening_over_odds'], game['total_current_over_odds'])}">{calculate_line_movement(game['total_opening_over_odds'], game['total_current_over_odds'])[0]} (O Odds)</span>
                            <span class="{get_movement_class(game['total_opening_under_odds'], game['total_current_under_odds'])}">{calculate_line_movement(game['total_opening_under_odds'], game['total_current_under_odds'])[0]} (U Odds)</span>
                        </div>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

def main():
    """Main Streamlit application"""
    
    st.title("⚾ MLB FanDuel Odds Tracker")
    st.markdown("*Live opening vs current FanDuel odds from SportsbookReview*")
    
    # Header with refresh button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Refresh Data", type="primary"):
            st.cache_data.clear()
            st.rerun()
    
    with col2:
        st.markdown("*Data updates every 5 minutes*")
    
    # Load data with spinner
    with st.spinner("🔍 Scraping FanDuel odds for today and tomorrow..."):
        data = load_odds_data()
    
    # Extract data
    today_df = data['today']
    tomorrow_df = data['tomorrow']
    today_date = data['today_date']
    tomorrow_date = data['tomorrow_date']
    last_update = data['last_update']
    data_source = data['data_source']
    debug_log = data['debug_log']
    scraper_success = data['scraper_success']
    
    # Status banner
    status_color = "#28a745" if scraper_success else "#dc3545"
    status_text_color = "white"
    
    st.markdown(f"""
    <div style="background-color: {status_color}; color: {status_text_color}; padding: 1rem; 
                border-radius: 8px; margin-bottom: 1.5rem; text-align: center; font-weight: bold;">
    📊 <strong>Last Updated:</strong> {last_update.strftime('%I:%M:%S %p ET')} | 
    <strong>Source:</strong> {data_source} | 
    <strong>Today:</strong> {len(today_df)} games | 
    <strong>Tomorrow:</strong> {len(tomorrow_df)} games
    </div>
    """, unsafe_allow_html=True)
    
    # Debug information (collapsible)
    with st.expander("🔍 Scraper Debug Log"):
        st.markdown("**Detailed scraping process:**")
        for log_entry in debug_log:
            st.text(log_entry)
    
    # Create tabs for today and tomorrow
    tab1, tab2 = st.tabs([
        f"📅 Today - {format_date(today_date)}", 
        f"📅 Tomorrow - {format_date(tomorrow_date)}"
    ])
    
    # Today's games
    with tab1:
        if not today_df.empty:
            st.markdown(f"### {len(today_df)} Games Today with FanDuel Odds")
            for _, game in today_df.iterrows():
                display_game_card(game)
        else:
            st.info("📅 No games with FanDuel odds found for today")
    
    # Tomorrow's games  
    with tab2:
        if not tomorrow_df.empty:
            st.markdown(f"### {len(tomorrow_df)} Games Tomorrow with FanDuel Odds")
            for _, game in tomorrow_df.iterrows():
                display_game_card(game)
        else:
            st.info("📅 No games with FanDuel odds found for tomorrow")

if __name__ == "__main__":
    main()
