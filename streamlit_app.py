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
            
            response = session.get(main_url, timeout=15)  # Reduced timeout
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
                                        time.sleep(random.uniform(1.0, 2.0))
                                        
                                        line_response = session.get(line_history_url, timeout=10)  # Reduced timeout
                                        debug_log.append(f"   📊 Line history response: {line_response.status_code}")
                                        
                                        if line_response.status_code == 200:
                                            line_match = re.search(pattern, line_response.text, re.DOTALL)
                                            
                                            if line_match:
                                                line_json = json.loads(line_match.group(1))
                                                debug_log.append("   ✅ Found JSON in line history page")
                                                
                                                # Navigate to FanDuel data - handle the ACTUAL structure we're seeing
                                                try:
                                                    page_props = line_json['props']['pageProps']
                                                    debug_log.append(f"      🔍 Page props keys: {list(page_props.keys())}")
                                                    
                                                    line_history_model = page_props.get('lineHistoryModel', {})
                                                    debug_log.append(f"      🔍 Line history model keys: {list(line_history_model.keys())}")
                                                    
                                                    # Check for the expected 'oddsViews' structure first
                                                    odds_views = line_history_model.get('oddsViews', [])
                                                    debug_log.append(f"      🔍 oddsViews length: {len(odds_views)}")
                                                    
                                                    # If no oddsViews, try the actual structure we're seeing
                                                    if not odds_views:
                                                        debug_log.append(f"      🔍 No oddsViews found, trying alternative structure...")
                                                        
                                                        # Try getting sportsbooks data
                                                        sportsbooks = line_history_model.get('sportsbooks', [])
                                                        debug_log.append(f"      🔍 Sportsbooks array length: {len(sportsbooks)}")
                                                        
                                                        if sportsbooks:
                                                            sportsbook_names = [sb.get('slug', '').lower() if isinstance(sb, dict) else str(sb).lower() for sb in sportsbooks]
                                                            debug_log.append(f"      🔍 Available sportsbook names: {sportsbook_names}")
                                                            
                                                            # Check if FanDuel is in the sportsbooks list
                                                            if 'fanduel' in sportsbook_names:
                                                                debug_log.append(f"      ✅ FanDuel found in sportsbooks list!")
                                                                
                                                                # Try to find odds data in lineHistory
                                                                line_history = line_history_model.get('lineHistory', {})
                                                                debug_log.append(f"      🔍 lineHistory keys: {list(line_history.keys())}")
                                                                
                                                                # Check if there's an oddsViews in lineHistory (different from top level)
                                                                line_odds_views = line_history.get('oddsViews', [])
                                                                if line_odds_views:
                                                                    debug_log.append(f"      🎯 Found oddsViews in lineHistory with {len(line_odds_views)} items")
                                                                    
                                                                    # Look for FanDuel in line history odds views
                                                                    for odds_view in line_odds_views:
                                                                        sportsbook_name = odds_view.get('sportsbook', '').lower()
                                                                        if sportsbook_name == 'fanduel':
                                                                            debug_log.append(f"      🎯 FOUND FANDUEL ODDS DATA!")
                                                                            debug_log.append(f"      📊 FanDuel data: {str(odds_view)[:300]}...")
                                                                            break
                                                                else:
                                                                    debug_log.append(f"      ❌ No oddsViews in lineHistory - odds not posted yet")
                                                            else:
                                                                debug_log.append(f"      ❌ FanDuel not in sportsbooks list")
                                                        else:
                                                            debug_log.append(f"      ❌ No sportsbooks data found")
                                                            
                                                            # Let's also check the full lineHistory structure for any odds
                                                            line_history = line_history_model.get('lineHistory', {})
                                                            if line_history:
                                                                debug_log.append(f"      🔍 Full lineHistory keys: {list(line_history.keys())}")
                                                                
                                                                # Look for any data that might contain odds
                                                                for key, value in line_history.items():
                                                                    if isinstance(value, list) and len(value) > 0:
                                                                        debug_log.append(f"      🔍 {key} is a list with {len(value)} items")
                                                                        if len(value) > 0 and isinstance(value[0], dict):
                                                                            debug_log.append(f"      🔍 {key}[0] keys: {list(value[0].keys())}")
                                                    
                                                    # If still no usable data, this game doesn't have odds yet
                                                    if not odds_views and not sportsbooks:
                                                        debug_log.append(f"      ❌ No odds data available for this game yet")
                                                    
                                                    debug_log.append(f"   📋 Found {len(odds_views)} sportsbooks in line history")
                                                    
                                                    # List all available sportsbooks
                                                    available_books = [view.get('sportsbook', 'Unknown') for view in odds_views]
                                                    debug_log.append(f"   📚 Available sportsbooks: {available_books}")
                                                    
                                                    # Find FanDuel data
                                                    fanduel_data = None
                                                    for j, view in enumerate(odds_views):
                                                        sportsbook = view.get('sportsbook', '').lower()
                                                        debug_log.append(f"      📖 Sportsbook {j}: '{sportsbook}'")
                                                        
                                                        if sportsbook == 'fanduel':
                                                            fanduel_data = view
                                                            debug_log.append(f"      🎯 FOUND FANDUEL DATA!")
                                                            break
                                                    
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
                                                        
                                                        # Log sample data
                                                        if ml_opening:
                                                            debug_log.append(f"      📊 ML Opening: Away {ml_opening.get('awayOdds')} | Home {ml_opening.get('homeOdds')}")
                                                        if ml_current:
                                                            debug_log.append(f"      📊 ML Current: Away {ml_current.get('awayOdds')} | Home {ml_current.get('homeOdds')}")
                                                        
                                                        # Create game record
                                                        game_info = {
                                                            'date': date_str,
                                                            'away_team': away_name,
                                                            'home_team': home_name,
                                                            'game_time': start_date,
                                                            'venue': venue,
                                                            'game_id': game_id,
                                                            
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
                                                        all_games.append(game_info)
                                                    else:
                                                        debug_log.append(f"      ❌ FanDuel not found in available sportsbooks")
                                                        
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

def create_fallback_data():
    """Create realistic fallback data for today and tomorrow"""
    
    et = timezone('US/Eastern')
    now_et = datetime.now(et)
    today = now_et.strftime("%Y-%m-%d")
    tomorrow = (now_et + timedelta(days=1)).strftime("%Y-%m-%d")
    
    fallback_games = [
        # Today's games
        {
            'date': today,
            'away_team': 'Philadelphia',
            'home_team': 'NY Yankees',
            'game_time': f'{today}T17:05:00-04:00',
            'venue': 'Yankee Stadium',
            'game_id': 342809,
            'ml_opening_away': 168, 'ml_opening_home': -200,
            'ml_current_away': 185, 'ml_current_home': -225,
            'rl_opening_away_odds': -125, 'rl_opening_home_odds': 104,
            'rl_opening_away_spread': 1.5, 'rl_opening_home_spread': -1.5,
            'rl_current_away_odds': -118, 'rl_current_home_odds': -102,
            'rl_current_away_spread': 1.5, 'rl_current_home_spread': -1.5,
            'total_opening_line': 9.0, 'total_opening_over_odds': -110, 'total_opening_under_odds': -110,
            'total_current_line': 8.5, 'total_current_over_odds': -105, 'total_current_under_odds': -115
        },
        {
            'date': today,
            'away_team': 'Miami',
            'home_team': 'Milwaukee',
            'game_time': f'{today}T20:10:00-04:00',
            'venue': 'American Family Field',
            'game_id': 342810,
            'ml_opening_away': 155, 'ml_opening_home': -185,
            'ml_current_away': 142, 'ml_current_home': -168,
            'rl_opening_away_odds': -130, 'rl_opening_home_odds': 110,
            'rl_opening_away_spread': 1.5, 'rl_opening_home_spread': -1.5,
            'rl_current_away_odds': -122, 'rl_current_home_odds': 102,
            'rl_current_away_spread': 1.5, 'rl_current_home_spread': -1.5,
            'total_opening_line': 8.0, 'total_opening_over_odds': -115, 'total_opening_under_odds': -105,
            'total_current_line': 7.5, 'total_current_over_odds': -108, 'total_current_under_odds': -112
        },
        # Tomorrow's games
        {
            'date': tomorrow,
            'away_team': 'Boston',
            'home_team': 'Toronto',
            'game_time': f'{tomorrow}T15:07:00-04:00',
            'venue': 'Rogers Centre',
            'game_id': 342815,
            'ml_opening_away': -145, 'ml_opening_home': 125,
            'ml_current_away': -132, 'ml_current_home': 112,
            'rl_opening_away_odds': 125, 'rl_opening_home_odds': -145,
            'rl_opening_away_spread': -1.5, 'rl_opening_home_spread': 1.5,
            'rl_current_away_odds': 115, 'rl_current_home_odds': -135,
            'rl_current_away_spread': -1.5, 'rl_current_home_spread': 1.5,
            'total_opening_line': 9.5, 'total_opening_over_odds': -110, 'total_opening_under_odds': -110,
            'total_current_line': 9.0, 'total_current_over_odds': -115, 'total_current_under_odds': -105
        }
    ]
    
    return pd.DataFrame(fallback_games)

@st.cache_data(ttl=600)  # Cache for 10 minutes instead of 5
def load_odds_data():
    """Load FanDuel odds data for today and tomorrow"""
    
    # Try to get real FanDuel data
    real_data, debug_log, success = get_fanduel_mlb_data()
    
    if success and not real_data.empty:
        fanduel_count = len(real_data[real_data['sportsbook'] == 'FanDuel'])
        backup_count = len(real_data[real_data['sportsbook'] != 'FanDuel'])
        
        if fanduel_count > 0 and backup_count > 0:
            data_source = f"🏆 Mixed: {fanduel_count} FanDuel + {backup_count} Other Sportsbooks"
        elif fanduel_count > 0:
            data_source = f"🏆 SportsbookReview ({fanduel_count} FanDuel Games)"
        else:
            data_source = f"📊 SportsbookReview ({backup_count} Games - No FanDuel Yet)"
        
        final_data = real_data
    else:
        data_source = "🎲 Fallback Data (Demo Mode)"
        final_data = create_fallback_data()
    
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
            # Fallback
            return game_time_str
            
        et = timezone('US/Eastern')
        dt_et = dt.astimezone(et)
        return dt_et.strftime("%I:%M %p ET")
    except:
        return "TBD"

def format_date(date_str):
    """Format date for display"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%A, %B %d, %Y")
    except:
        return date_str

def calculate_line_movement(opening, current):
    """Calculate line movement with color coding"""
    try:
        opening_val = float(opening) if opening is not None and not pd.isna(opening) else None
        current_val = float(current) if current is not None and not pd.isna(current) else None
        
        if opening_val is None or current_val is None:
            return "N/A", "#666666"
        
        diff = current_val - opening_val
        
        if abs(diff) < 1:
            return "No Change", "#666666"
        elif diff > 0:
            return f"+{diff:.0f}", "#28a745"  # Green
        else:
            return f"{diff:.0f}", "#dc3545"   # Red
    except:
        return "N/A", "#666666"

def display_game_card(game):
    """Display a single game with odds (FanDuel preferred, backup if needed)"""
    
    sportsbook = game.get('sportsbook', 'FanDuel')
    border_color = "#1f77b4" if sportsbook == 'FanDuel' else "#ff6b35"
    
    with st.container():
        st.markdown(f"""
        <div style="border: 2px solid {border_color}; border-radius: 12px; padding: 24px; margin-bottom: 24px; 
                    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h3 style="margin-top: 0; color: {border_color}; font-weight: bold; font-size: 1.5em;">
                {game['away_team']} @ {game['home_team']}
            </h3>
            <p style="color: #666; margin-bottom: 20px; font-size: 16px;">
                <strong>🏟️ {game['venue']}</strong> • <strong>⏰ {format_game_time(game['game_time'])}</strong>
            </p>
        """, unsafe_allow_html=True)
        
        st.markdown(f"### 📊 {sportsbook} Odds - Opening vs Current")
        
        # Create three columns for different bet types
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### 💰 Moneyline")
            
            # Away team moneyline
            away_ml_move, away_ml_color = calculate_line_movement(game['ml_opening_away'], game['ml_current_away'])
            st.markdown(f"""
            **{game['away_team']}:**  
            Opening: {format_odds(game['ml_opening_away'])}  
            Current: {format_odds(game['ml_current_away'])} 
            <span style="color: {away_ml_color}; font-weight: bold;">({away_ml_move})</span>
            """, unsafe_allow_html=True)
            
            # Home team moneyline
            home_ml_move, home_ml_color = calculate_line_movement(game['ml_opening_home'], game['ml_current_home'])
            st.markdown(f"""
            **{game['home_team']}:**  
            Opening: {format_odds(game['ml_opening_home'])}  
            Current: {format_odds(game['ml_current_home'])} 
            <span style="color: {home_ml_color}; font-weight: bold;">({home_ml_move})</span>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("#### 🏃 Run Line")
            
            # Away team run line
            st.markdown(f"""
            **{game['away_team']} {format_spread(game['rl_opening_away_spread'])}:**  
            Opening: {format_odds(game['rl_opening_away_odds'])}  
            Current: {format_odds(game['rl_current_away_odds'])}
            """, unsafe_allow_html=True)
            
            # Home team run line
            st.markdown(f"""
            **{game['home_team']} {format_spread(game['rl_opening_home_spread'])}:**  
            Opening: {format_odds(game['rl_opening_home_odds'])}  
            Current: {format_odds(game['rl_current_home_odds'])}
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("#### 🎯 Total")
            
            opening_total = format_total(game['total_opening_line'])
            current_total = format_total(game['total_current_line'])
            
            # Over
            st.markdown(f"""
            **Over {opening_total} → {current_total}:**  
            Opening: {format_odds(game['total_opening_over_odds'])}  
            Current: {format_odds(game['total_current_over_odds'])}
            """, unsafe_allow_html=True)
            
            # Under
            st.markdown(f"""
            **Under {opening_total} → {current_total}:**  
            Opening: {format_odds(game['total_opening_under_odds'])}  
            Current: {format_odds(game['total_current_under_odds'])}
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

def main():
    """Main Streamlit application"""
    
    st.title("⚾ MLB Odds Tracker (FanDuel Preferred)")
    st.markdown("*Live opening vs current odds from SportsbookReview - FanDuel preferred, other sportsbooks as backup*")
    
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
    status_color = "#28a745" if scraper_success else "#ffc107"
    status_text_color = "white" if scraper_success else "black"
    
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
            st.markdown("*This could mean no games are scheduled or FanDuel odds aren't available yet.*")
    
    # Tomorrow's games  
    with tab2:
        if not tomorrow_df.empty:
            st.markdown(f"### {len(tomorrow_df)} Games Tomorrow with FanDuel Odds")
            for _, game in tomorrow_df.iterrows():
                display_game_card(game)
        else:
            st.info("📅 No games with FanDuel odds found for tomorrow")
            st.markdown("*Tomorrow's odds may not be posted yet.*")

if __name__ == "__main__":
    main()
