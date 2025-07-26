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

def get_real_mlb_data_with_debug():
    """Try to get real MLB data and return debug info for display"""
    
    debug_log = []
    debug_log.append("🧪 Attempting to scrape real MLB data...")
    
    session = requests.Session()
    session.headers.update({
        'Accept-Encoding': 'identity',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    # Try multiple dates to find FanDuel data
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    dates_to_try = [today, yesterday, tomorrow]
    
    all_games = []
    
    for date_str in dates_to_try:
        debug_log.append(f"\n📅 Trying date: {date_str}")
        
        try:
            # Test moneyline URL
            url = f"https://www.sportsbookreview.com/betting-odds/mlb-baseball/?date={date_str}"
            debug_log.append(f"📡 Trying: {url}")
            
            response = session.get(url, timeout=30)
            debug_log.append(f"📊 Response status: {response.status_code}")
            
            if response.status_code == 200:
                # Extract JSON
                pattern = r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'
                match = re.search(pattern, response.text, re.DOTALL)
                
                if match:
                    debug_log.append("✅ Found __NEXT_DATA__ script")
                    json_data = json.loads(match.group(1))
                    
                    # Navigate to games
                    odds_tables = json_data['props']['pageProps']['oddsTables']
                    if odds_tables:
                        odds_table_model = odds_tables[0]['oddsTableModel']
                        game_rows = odds_table_model.get('gameRows', [])
                        
                        debug_log.append(f"✅ Found {len(game_rows)} games for {date_str}")
                        
                        # Check what sportsbooks are available
                        sportsbooks = odds_table_model.get('sportsbooks', [])
                        debug_log.append(f"📚 Available sportsbooks for {date_str}:")
                        for sb in sportsbooks:
                            debug_log.append(f"   - {sb.get('name', 'Unknown')} (ID: {sb.get('sportsbookId', 'Unknown')})")
                        
                        if game_rows:
                            # Check first game for FanDuel data
                            first_game = game_rows[0]
                            opening_line_views = first_game.get('openingLineViews', [])
                            
                            debug_log.append(f"🔍 Checking first game for FanDuel...")
                            fanduel_found_in_date = False
                            
                            for view in opening_line_views:
                                sportsbook = view.get('sportsbook', 'Unknown')
                                if sportsbook.lower() == 'fanduel':
                                    fanduel_found_in_date = True
                                    debug_log.append(f"✅ FanDuel found for {date_str}!")
                                    break
                                else:
                                    debug_log.append(f"   Found: {sportsbook}")
                            
                            if fanduel_found_in_date:
                                # Process all games for this date
                                debug_log.append(f"🎯 Processing all games for {date_str} (FanDuel available)")
                                
                                for i, game in enumerate(game_rows):
                                    try:
                                        game_view = game.get('gameView', {})
                                        opening_line_views = game.get('openingLineViews', [])
                                        
                                        away_team = game_view.get('awayTeam', {})
                                        home_team = game_view.get('homeTeam', {})
                                        
                                        away_name = away_team.get('name', 'Unknown')
                                        home_name = home_team.get('name', 'Unknown')
                                        
                                        game_info = {
                                            'date': date_str,
                                            'away_team': away_name,
                                            'home_team': home_name,
                                            'game_time': game_view.get('startDate', 'TBD'),
                                            'venue': game_view.get('venueName', 'Unknown'),
                                        }
                                        
                                        # Initialize all odds as None
                                        for field in ['ml_opening_away', 'ml_opening_home', 'ml_current_away', 'ml_current_home',
                                                     'rl_opening_away_odds', 'rl_opening_home_odds', 'rl_opening_away_spread', 'rl_opening_home_spread',
                                                     'rl_current_away_odds', 'rl_current_home_odds', 'rl_current_away_spread', 'rl_current_home_spread',
                                                     'total_opening_line', 'total_opening_over_odds', 'total_opening_under_odds',
                                                     'total_current_line', 'total_current_over_odds', 'total_current_under_odds']:
                                            game_info[field] = None
                                        
                                        # Extract FanDuel data
                                        for view in opening_line_views:
                                            if view.get('sportsbook', '').lower() == 'fanduel':
                                                opening_line = view.get('openingLine', {})
                                                current_line = view.get('currentLine', {})
                                                
                                                # Moneyline data
                                                game_info['ml_opening_away'] = opening_line.get('awayOdds')
                                                game_info['ml_opening_home'] = opening_line.get('homeOdds')
                                                game_info['ml_current_away'] = current_line.get('awayOdds')
                                                game_info['ml_current_home'] = current_line.get('homeOdds')
                                                
                                                # Run line data (if available)
                                                game_info['rl_opening_away_spread'] = opening_line.get('awaySpread')
                                                game_info['rl_opening_home_spread'] = opening_line.get('homeSpread')
                                                if opening_line.get('awaySpread') is not None:
                                                    game_info['rl_opening_away_odds'] = opening_line.get('awayOdds')
                                                    game_info['rl_opening_home_odds'] = opening_line.get('homeOdds')
                                                
                                                game_info['rl_current_away_spread'] = current_line.get('awaySpread')
                                                game_info['rl_current_home_spread'] = current_line.get('homeSpread')
                                                if current_line.get('awaySpread') is not None:
                                                    game_info['rl_current_away_odds'] = current_line.get('awayOdds')
                                                    game_info['rl_current_home_odds'] = current_line.get('homeOdds')
                                                
                                                # Totals data (if available)
                                                game_info['total_opening_line'] = opening_line.get('total')
                                                game_info['total_opening_over_odds'] = opening_line.get('overOdds')
                                                game_info['total_opening_under_odds'] = opening_line.get('underOdds')
                                                
                                                game_info['total_current_line'] = current_line.get('total')
                                                game_info['total_current_over_odds'] = current_line.get('overOdds')
                                                game_info['total_current_under_odds'] = current_line.get('underOdds')
                                                
                                                break
                                        
                                        all_games.append(game_info)
                                        
                                    except Exception as e:
                                        debug_log.append(f"❌ Error processing game {i}: {str(e)}")
                                        continue
                                
                                debug_log.append(f"✅ Processed {len(game_rows)} games from {date_str}")
                                
                            else:
                                debug_log.append(f"❌ No FanDuel data found for {date_str}")
                    else:
                        debug_log.append(f"❌ No odds tables found for {date_str}")
                else:
                    debug_log.append(f"❌ No __NEXT_DATA__ script found for {date_str}")
            else:
                debug_log.append(f"❌ Bad response status for {date_str}: {response.status_code}")
                
        except Exception as e:
            debug_log.append(f"❌ Error scraping {date_str}: {str(e)}")
    
    if all_games:
        debug_log.append(f"\n🎉 SUCCESS: Found {len(all_games)} total games with FanDuel data")
        return pd.DataFrame(all_games), debug_log, True
    else:
        debug_log.append(f"\n❌ FAILED: No FanDuel data found on any date")
        return pd.DataFrame(), debug_log, False

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
        },
        {
            'date': '2025-07-25',
            'away_team': 'Arizona',
            'home_team': 'Pittsburgh',
            'game_time': '2025-07-25T22:40:00+00:00',
            'venue': 'PNC Park',
            'ml_opening_away': -136, 'ml_opening_home': 116,
            'ml_current_away': -118, 'ml_current_home': -108,
            'rl_opening_away_odds': 122, 'rl_opening_home_odds': -146,
            'rl_opening_away_spread': -1.5, 'rl_opening_home_spread': 1.5,
            'rl_current_away_odds': 142, 'rl_current_home_odds': -192,
            'rl_current_away_spread': -1.5, 'rl_current_home_spread': 1.5,
            'total_opening_line': 9.0, 'total_opening_over_odds': -110, 'total_opening_under_odds': -110,
            'total_current_line': 8.5, 'total_current_over_odds': -132, 'total_current_under_odds': 100
        }
    ]
    
    return pd.DataFrame(fallback_games)

@st.cache_data(ttl=300)
def load_odds_data():
    """Load odds data with debug info"""
    
    # Try real data first
    real_data, debug_log, success = get_real_mlb_data_with_debug()
    
    if success and not real_data.empty:
        data_source = "🏆 SportsbookReview (FanDuel Live)"
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
    st.markdown("*Real-time opening vs current odds*")
    
    # Refresh button
    if st.button("🔄 Refresh Data", type="primary"):
        st.cache_data.clear()
        st.rerun()
    
    # Load data
    with st.spinner("Loading latest odds..."):
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
    with st.expander("🔍 Debug Information (Click to see what's happening)"):
        st.markdown("**Scraper Debug Log:**")
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
