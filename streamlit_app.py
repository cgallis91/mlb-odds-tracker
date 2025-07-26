import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests
import re
import json
from pytz import timezone

# Configure page
st.set_page_config(
    page_title="MLB Odds Tracker",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def get_game_line_history(game_id, session):
    """Get line history for a specific game"""
    
    url = f"https://www.sportsbookreview.com/betting-odds/mlb-baseball/line-history/{game_id}/"
    
    try:
        response = session.get(url, timeout=30)
        if response.status_code == 200:
            # Extract JSON from line history page
            pattern = r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'
            match = re.search(pattern, response.text, re.DOTALL)
            
            if match:
                json_data = json.loads(match.group(1))
                return json_data
        
        return None
    except:
        return None

def get_real_mlb_data_with_line_history():
    """Get MLB data using line history approach for FanDuel data"""
    
    debug_log = []
    debug_log.append("🧪 Attempting to scrape MLB data with line history approach...")
    
    session = requests.Session()
    session.headers.update({
        'Accept-Encoding': 'identity',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    all_games = []
    
    for date_str in [today, tomorrow]:
        debug_log.append(f"\n📅 Processing date: {date_str}")
        
        try:
            # Get main games list first
            url = f"https://www.sportsbookreview.com/betting-odds/mlb-baseball/?date={date_str}"
            debug_log.append(f"📡 Getting games list: {url}")
            
            response = session.get(url, timeout=30)
            
            if response.status_code == 200:
                pattern = r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'
                match = re.search(pattern, response.text, re.DOTALL)
                
                if match:
                    json_data = json.loads(match.group(1))
                    
                    odds_tables = json_data['props']['pageProps']['oddsTables']
                    if odds_tables:
                        odds_table_model = odds_tables[0]['oddsTableModel']
                        game_rows = odds_table_model.get('gameRows', [])
                        
                        debug_log.append(f"✅ Found {len(game_rows)} games for {date_str}")
                        
                        # Process first few games to test line history approach
                        for i, game in enumerate(game_rows[:3]):  # Test with first 3 games
                            try:
                                game_view = game.get('gameView', {})
                                game_id = game_view.get('gameId')
                                
                                away_team = game_view.get('awayTeam', {})
                                home_team = game_view.get('homeTeam', {})
                                
                                away_name = away_team.get('name', 'Unknown')
                                home_name = home_team.get('name', 'Unknown')
                                
                                debug_log.append(f"\n🎮 Game {i+1}: {away_name} @ {home_name} (ID: {game_id})")
                                
                                if game_id:
                                    # Try to get line history for this game
                                    debug_log.append(f"   📈 Getting line history for game {game_id}...")
                                    
                                    line_history_data = get_game_line_history(game_id, session)
                                    
                                    if line_history_data:
                                        debug_log.append(f"   ✅ Got line history data")
                                        
                                        # Try to extract FanDuel data from line history
                                        fanduel_data = extract_fanduel_from_line_history(line_history_data, debug_log)
                                        
                                        if fanduel_data:
                                            game_info = {
                                                'date': date_str,
                                                'away_team': away_name,
                                                'home_team': home_name,
                                                'game_time': game_view.get('startDate', 'TBD'),
                                                'venue': game_view.get('venueName', 'Unknown'),
                                                'game_id': game_id
                                            }
                                            
                                            # Add FanDuel odds
                                            game_info.update(fanduel_data)
                                            
                                            debug_log.append(f"   💰 FanDuel ML: {fanduel_data.get('ml_opening_away')}/{fanduel_data.get('ml_opening_home')} → {fanduel_data.get('ml_current_away')}/{fanduel_data.get('ml_current_home')}")
                                            
                                            all_games.append(game_info)
                                        else:
                                            debug_log.append(f"   ❌ No FanDuel data in line history")
                                    else:
                                        debug_log.append(f"   ❌ Could not get line history")
                                else:
                                    debug_log.append(f"   ❌ No game ID found")
                                    
                            except Exception as e:
                                debug_log.append(f"   💥 Error processing game {i}: {str(e)}")
                                continue
                    else:
                        debug_log.append(f"❌ No odds tables for {date_str}")
                else:
                    debug_log.append(f"❌ No JSON data for {date_str}")
            else:
                debug_log.append(f"❌ Bad response for {date_str}: {response.status_code}")
                
        except Exception as e:
            debug_log.append(f"❌ Error processing {date_str}: {str(e)}")
    
    if all_games:
        debug_log.append(f"\n🎉 SUCCESS: Found {len(all_games)} games with FanDuel data using line history")
        return pd.DataFrame(all_games), debug_log, True
    else:
        debug_log.append(f"\n❌ FAILED: No FanDuel data found using line history approach")
        return pd.DataFrame(), debug_log, False

def extract_fanduel_from_line_history(line_history_data, debug_log):
    """Extract FanDuel data from line history JSON"""
    
    try:
        # Navigate through line history structure
        page_props = line_history_data.get('props', {}).get('pageProps', {})
        
        debug_log.append(f"     📊 Line history keys: {list(page_props.keys())}")
        
        # Look for different possible structures
        if 'lineHistory' in page_props:
            line_history = page_props['lineHistory']
            debug_log.append(f"     📈 Found lineHistory section")
            
            # Look for FanDuel in the line history
            if isinstance(line_history, dict):
                for key, value in line_history.items():
                    if 'fanduel' in key.lower():
                        debug_log.append(f"     ✅ Found FanDuel section: {key}")
                        return process_fanduel_line_data(value, debug_log)
            
        # Look for odds data
        if 'oddsData' in page_props:
            odds_data = page_props['oddsData']
            debug_log.append(f"     📊 Found oddsData section")
            
            # Search for FanDuel in odds data
            return search_for_fanduel_in_data(odds_data, debug_log)
        
        # Look for any other structure that might contain sportsbook data
        for key, value in page_props.items():
            if isinstance(value, dict) or isinstance(value, list):
                fanduel_data = search_for_fanduel_in_data(value, debug_log, key)
                if fanduel_data:
                    return fanduel_data
        
        debug_log.append(f"     ❌ No FanDuel data structure found")
        return None
        
    except Exception as e:
        debug_log.append(f"     💥 Error extracting FanDuel data: {str(e)}")
        return None

def search_for_fanduel_in_data(data, debug_log, section_name="data"):
    """Recursively search for FanDuel data in any structure"""
    
    try:
        if isinstance(data, dict):
            # Check if this dict has FanDuel info
            for key, value in data.items():
                if 'fanduel' in str(key).lower():
                    debug_log.append(f"     ✅ Found FanDuel key in {section_name}: {key}")
                    return process_fanduel_line_data(value, debug_log)
                
                # Check if value contains sportsbook info
                if isinstance(value, dict) and 'sportsbook' in value:
                    if 'fanduel' in str(value.get('sportsbook', '')).lower():
                        debug_log.append(f"     ✅ Found FanDuel sportsbook in {section_name}")
                        return process_fanduel_line_data(value, debug_log)
                
                # Recurse into nested structures
                if isinstance(value, (dict, list)):
                    result = search_for_fanduel_in_data(value, debug_log, f"{section_name}.{key}")
                    if result:
                        return result
        
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    result = search_for_fanduel_in_data(item, debug_log, f"{section_name}[{i}]")
                    if result:
                        return result
        
        return None
        
    except:
        return None

def process_fanduel_line_data(fanduel_data, debug_log):
    """Process FanDuel data once found"""
    
    try:
        debug_log.append(f"     🔄 Processing FanDuel data structure...")
        
        # Initialize odds structure
        odds_data = {}
        for field in ['ml_opening_away', 'ml_opening_home', 'ml_current_away', 'ml_current_home',
                     'rl_opening_away_odds', 'rl_opening_home_odds', 'rl_opening_away_spread', 'rl_opening_home_spread',
                     'rl_current_away_odds', 'rl_current_home_odds', 'rl_current_away_spread', 'rl_current_home_spread',
                     'total_opening_line', 'total_opening_over_odds', 'total_opening_under_odds',
                     'total_current_line', 'total_current_over_odds', 'total_current_under_odds']:
            odds_data[field] = None
        
        # Try to extract odds from various possible structures
        if isinstance(fanduel_data, dict):
            # Look for opening and current line structures
            if 'openingLine' in fanduel_data and 'currentLine' in fanduel_data:
                opening = fanduel_data['openingLine']
                current = fanduel_data['currentLine']
                
                # Extract moneyline
                if 'awayOdds' in opening:
                    odds_data['ml_opening_away'] = opening.get('awayOdds')
                    odds_data['ml_opening_home'] = opening.get('homeOdds')
                    odds_data['ml_current_away'] = current.get('awayOdds')
                    odds_data['ml_current_home'] = current.get('homeOdds')
                
                # Extract run line
                if 'awaySpread' in opening:
                    odds_data['rl_opening_away_spread'] = opening.get('awaySpread')
                    odds_data['rl_opening_home_spread'] = opening.get('homeSpread')
                    odds_data['rl_current_away_spread'] = current.get('awaySpread')
                    odds_data['rl_current_home_spread'] = current.get('homeSpread')
                
                # Extract totals
                if 'total' in opening:
                    odds_data['total_opening_line'] = opening.get('total')
                    odds_data['total_opening_over_odds'] = opening.get('overOdds')
                    odds_data['total_opening_under_odds'] = opening.get('underOdds')
                    odds_data['total_current_line'] = current.get('total')
                    odds_data['total_current_over_odds'] = current.get('overOdds')
                    odds_data['total_current_under_odds'] = current.get('underOdds')
                
                debug_log.append(f"     ✅ Extracted FanDuel odds successfully")
                return odds_data
        
        debug_log.append(f"     ❌ Could not parse FanDuel data structure")
        return None
        
    except Exception as e:
        debug_log.append(f"     💥 Error processing FanDuel data: {str(e)}")
        return None

def create_fallback_data():
    """Create realistic fallback data"""
    
    fallback_games = [
        {
            'date': '2025-07-25',
            'away_team': 'Miami',
            'home_team': 'Milwaukee',
            'game_time': '2025-07-25T20:10:00+00:00',
            'venue': 'American Family Field',
            'ml_opening_away': 168, 'ml_opening_home': -200,
            'ml_current_away': 190, 'ml_current_home': -230,
            'rl_opening_away_odds': -125, 'rl_opening_home_odds': 104,
            'rl_opening_away_spread': 1.5, 'rl_opening_home_spread': -1.5,
            'rl_current_away_odds': -110, 'rl_current_home_odds': -110,
            'rl_current_away_spread': 1.5, 'rl_current_home_spread': -1.5,
            'total_opening_line': 8.0, 'total_opening_over_odds': -115, 'total_opening_under_odds': -105,
            'total_current_line': 8.0, 'total_current_over_odds': -102, 'total_current_under_odds': -120
        }
    ]
    
    return pd.DataFrame(fallback_games)

@st.cache_data(ttl=300)
def load_odds_data():
    """Load odds data with line history approach"""
    
    # Try line history approach
    real_data, debug_log, success = get_real_mlb_data_with_line_history()
    
    if success and not real_data.empty:
        data_source = "🏆 SportsbookReview Line History (FanDuel)"
        final_data = real_data
    else:
        data_source = "🎲 Fallback Data (Demo)"
        final_data = create_fallback_data()
    
    et = timezone('US/Eastern')
    now_et = datetime.now(et)
    today = now_et.strftime("%Y-%m-%d")
    tomorrow = (now_et + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Filter by date
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
        return "Unavailable"
    try:
        odds = int(odds_value)
        return f"+{odds}" if odds > 0 else str(odds)
    except (ValueError, TypeError):
        return "Unavailable"

def format_spread(spread_value):
    if pd.isna(spread_value) or spread_value is None:
        return "Unavailable"
    try:
        spread = float(spread_value)
        return f"+{spread}" if spread > 0 else str(spread)
    except (ValueError, TypeError):
        return "Unavailable"

def format_total(total_value):
    if pd.isna(total_value) or total_value is None:
        return "Unavailable"
    try:
        return f"{float(total_value)}"
    except (ValueError, TypeError):
        return "Unavailable"

def format_game_time(game_time_str):
    try:
        dt = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))
        et = timezone('US/Eastern')
        dt_et = dt.astimezone(et)
        return dt_et.strftime("%I:%M %p ET")
    except:
        return "TBD"

def format_date(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%B %d, %Y")
    except:
        return date_str

def display_game_card(game):
    st.markdown(f"### {game['away_team']} @ {game['home_team']}")
    st.markdown(f"**{game['venue']}** • {format_game_time(game['game_time'])}")
    
    # Opening Lines
    st.markdown("#### 📈 Opening Lines")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Moneyline**")
        st.write(f"{game['away_team']}: {format_odds(game['ml_opening_away'])}")
        st.write(f"{game['home_team']}: {format_odds(game['ml_opening_home'])}")
    
    with col2:
        st.markdown("**Run Line**")
        st.write(f"{game['away_team']} {format_spread(game['rl_opening_away_spread'])}: {format_odds(game['rl_opening_away_odds'])}")
        st.write(f"{game['home_team']} {format_spread(game['rl_opening_home_spread'])}: {format_odds(game['rl_opening_home_odds'])}")
    
    with col3:
        st.markdown("**Total**")
        total_line = format_total(game['total_opening_line'])
        st.write(f"O {total_line}: {format_odds(game['total_opening_over_odds'])}")
        st.write(f"U {total_line}: {format_odds(game['total_opening_under_odds'])}")
    
    # Current Lines
    st.markdown("#### 🔄 Current Lines")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Moneyline**")
        st.write(f"{game['away_team']}: {format_odds(game['ml_current_away'])}")
        st.write(f"{game['home_team']}: {format_odds(game['ml_current_home'])}")
    
    with col2:
        st.markdown("**Run Line**")
        st.write(f"{game['away_team']} {format_spread(game['rl_current_away_spread'])}: {format_odds(game['rl_current_away_odds'])}")
        st.write(f"{game['home_team']} {format_spread(game['rl_current_home_spread'])}: {format_odds(game['rl_current_home_odds'])}")
    
    with col3:
        st.markdown("**Total**")
        total_line = format_total(game['total_current_line'])
        st.write(f"O {total_line}: {format_odds(game['total_current_over_odds'])}")
        st.write(f"U {total_line}: {format_odds(game['total_current_under_odds'])}")
    
    st.divider()

def main():
    st.title("⚾ MLB Odds Tracker - FanDuel Lines")
    st.markdown("*Real-time opening vs current odds using line history*")
    
    # Refresh button
    if st.button("🔄 Refresh Data", type="primary"):
        st.cache_data.clear()
        st.rerun()
    
    # Load data
    with st.spinner("Loading latest odds using line history..."):
        data = load_odds_data()
    
    today_df = data['today']
    tomorrow_df = data['tomorrow']
    today_date = data['today_date']
    tomorrow_date = data['tomorrow_date']
    last_update = data['last_update']
    data_source = data['data_source']
    debug_log = data['debug_log']
    scraper_success = data['scraper_success']
    
    # Display status
    status_color = "#28a745" if scraper_success else "#ffc107"
    st.markdown(f"""
    <div style="background-color: {status_color}; color: white; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; text-align: center;">
    📊 <strong>Last Updated:</strong> {last_update.strftime('%I:%M:%S %p ET')} | 
    <strong>Source:</strong> {data_source} | 
    <strong>Today:</strong> {len(today_df)} games | 
    <strong>Tomorrow:</strong> {len(tomorrow_df)} games
    </div>
    """, unsafe_allow_html=True)
    
    # Show debug info in expandable section
    with st.expander("🔍 Debug Information (Line History Approach)"):
        st.markdown("**Line History Debug Log:**")
        for log_entry in debug_log:
            st.text(log_entry)
    
    # Create tabs
    tab1, tab2 = st.tabs([
        f"📅 Today - {format_date(today_date)}", 
        f"📅 Tomorrow - {format_date(tomorrow_date)}"
    ])
    
    with tab1:
        if not today_df.empty:
            st.markdown(f"### {len(today_df)} Games Today")
            for _, game in today_df.iterrows():
                display_game_card(game)
        else:
            st.info("📅 No games scheduled for today")
    
    with tab2:
        if not tomorrow_df.empty:
            st.markdown(f"### {len(tomorrow_df)} Games Tomorrow")
            for _, game in tomorrow_df.iterrows():
                display_game_card(game)
        else:
            st.info("📅 No games scheduled for tomorrow")

if __name__ == "__main__":
    main()
