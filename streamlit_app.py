import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
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

# Custom CSS for better styling
st.markdown("""
<style>
    .main > div {
        padding-top: 1rem;
    }
    
    .game-card {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .game-header {
        font-size: 1.2em;
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    
    .game-info {
        text-align: center;
        color: #6c757d;
        margin-bottom: 1rem;
        font-size: 0.9em;
    }
    
    .line-section {
        background-color: white;
        border-radius: 6px;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-left: 4px solid #007bff;
    }
    
    .line-header {
        font-weight: bold;
        color: #495057;
        margin-bottom: 0.5rem;
    }
    
    .bet-column {
        text-align: center;
        padding: 0.5rem;
    }
    
    .bet-type-header {
        font-weight: bold;
        color: #6c757d;
        font-size: 0.9em;
        margin-bottom: 0.25rem;
    }
    
    .odds-value {
        font-size: 1.1em;
        font-weight: 500;
        color: #212529;
    }
    
    .unavailable {
        color: #868e96;
        font-style: italic;
    }
    
    .refresh-info {
        background-color: #e3f2fd;
        padding: 0.75rem;
        border-radius: 6px;
        margin-bottom: 1rem;
        border-left: 4px solid #2196f3;
        text-align: center;
    }
    
    .team-name {
        font-weight: 600;
        color: #495057;
    }
</style>
""", unsafe_allow_html=True)

class ComprehensiveMLBScraper:
    """
    Comprehensive MLB scraper that gets moneyline, run line, and totals
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://www.sportsbookreview.com/betting-odds/mlb-baseball"
        self.setup_working_headers()
    
    def setup_working_headers(self):
        """Setup headers that work (no compression)"""
        self.session.headers.update({
            'Accept-Encoding': 'identity',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache'
        })
    
    def scrape_bet_type(self, date_str, bet_type):
        """Scrape specific bet type (moneyline, pointspread, totals)"""
        
        bet_type_urls = {
            'moneyline': f"{self.base_url}/?date={date_str}",
            'pointspread': f"{self.base_url}/pointspread/full-game/?date={date_str}",
            'totals': f"{self.base_url}/totals/full-game/?date={date_str}"
        }
        
        url = bet_type_urls.get(bet_type, bet_type_urls['moneyline'])
        
        try:
            response = self.session.get(url, timeout=30)
            
            if response.status_code != 200:
                return None
            
            # Extract __NEXT_DATA__
            pattern = r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'
            match = re.search(pattern, response.text, re.DOTALL)
            
            if not match:
                return None
            
            json_data = json.loads(match.group(1))
            
            # Extract odds data
            try:
                odds_tables = json_data['props']['pageProps']['oddsTables']
                if not odds_tables:
                    return None
                
                odds_table_model = odds_tables[0]['oddsTableModel']
                game_rows = odds_table_model.get('gameRows', [])
                
                return game_rows
                
            except KeyError:
                return None
                
        except Exception:
            return None
    
    def extract_fanduel_odds_from_game(self, game, bet_type):
        """Extract FanDuel odds from a game for specific bet type"""
        
        opening_line_views = game.get('openingLineViews', [])
        
        odds_data = {
            'opening': {},
            'current': {}
        }
        
        # Find FanDuel data
        for odds_view in opening_line_views:
            if odds_view.get('sportsbook', '').lower() == 'fanduel':
                opening_line = odds_view.get('openingLine', {})
                current_line = odds_view.get('currentLine', {})
                
                if bet_type == 'moneyline':
                    odds_data['opening'] = {
                        'away_odds': opening_line.get('awayOdds'),
                        'home_odds': opening_line.get('homeOdds')
                    }
                    odds_data['current'] = {
                        'away_odds': current_line.get('awayOdds'),
                        'home_odds': current_line.get('homeOdds')
                    }
                
                elif bet_type == 'pointspread':
                    odds_data['opening'] = {
                        'away_odds': opening_line.get('awayOdds'),
                        'home_odds': opening_line.get('homeOdds'),
                        'away_spread': opening_line.get('awaySpread'),
                        'home_spread': opening_line.get('homeSpread')
                    }
                    odds_data['current'] = {
                        'away_odds': current_line.get('awayOdds'),
                        'home_odds': current_line.get('homeOdds'),
                        'away_spread': current_line.get('awaySpread'),
                        'home_spread': current_line.get('homeSpread')
                    }
                
                elif bet_type == 'totals':
                    odds_data['opening'] = {
                        'over_odds': opening_line.get('overOdds'),
                        'under_odds': opening_line.get('underOdds'),
                        'total': opening_line.get('total')
                    }
                    odds_data['current'] = {
                        'over_odds': current_line.get('overOdds'),
                        'under_odds': current_line.get('underOdds'),
                        'total': current_line.get('total')
                    }
                
                break
        
        return odds_data
    
    def scrape_date_all_bet_types(self, date_str):
        """Scrape all bet types for a specific date"""
        
        # Get data for all bet types
        moneyline_games = self.scrape_bet_type(date_str, 'moneyline')
        pointspread_games = self.scrape_bet_type(date_str, 'pointspread')
        totals_games = self.scrape_bet_type(date_str, 'totals')
        
        if not moneyline_games:
            return []
        
        processed_games = []
        
        for i, ml_game in enumerate(moneyline_games):
            try:
                # Extract basic game info from moneyline data
                game_view = ml_game.get('gameView', {})
                
                away_team = game_view.get('awayTeam', {})
                home_team = game_view.get('homeTeam', {})
                
                game_info = {
                    'date': date_str,
                    'game_id': game_view.get('gameId', f'game_{i}'),
                    'game_time': game_view.get('startDate', 'TBD'),
                    'away_team': away_team.get('name', 'Unknown'),
                    'home_team': home_team.get('name', 'Unknown'),
                    'status': game_view.get('status', 'Scheduled'),
                    'venue': game_view.get('venueName', 'Unknown')
                }
                
                # Extract moneyline odds
                ml_odds = self.extract_fanduel_odds_from_game(ml_game, 'moneyline')
                game_info.update({
                    'ml_opening_away': ml_odds['opening'].get('away_odds'),
                    'ml_opening_home': ml_odds['opening'].get('home_odds'),
                    'ml_current_away': ml_odds['current'].get('away_odds'),
                    'ml_current_home': ml_odds['current'].get('home_odds')
                })
                
                # Extract pointspread (run line) odds
                if pointspread_games and i < len(pointspread_games):
                    ps_odds = self.extract_fanduel_odds_from_game(pointspread_games[i], 'pointspread')
                    game_info.update({
                        'rl_opening_away_odds': ps_odds['opening'].get('away_odds'),
                        'rl_opening_home_odds': ps_odds['opening'].get('home_odds'),
                        'rl_opening_away_spread': ps_odds['opening'].get('away_spread'),
                        'rl_opening_home_spread': ps_odds['opening'].get('home_spread'),
                        'rl_current_away_odds': ps_odds['current'].get('away_odds'),
                        'rl_current_home_odds': ps_odds['current'].get('home_odds'),
                        'rl_current_away_spread': ps_odds['current'].get('away_spread'),
                        'rl_current_home_spread': ps_odds['current'].get('home_spread')
                    })
                else:
                    game_info.update({
                        'rl_opening_away_odds': None, 'rl_opening_home_odds': None,
                        'rl_opening_away_spread': None, 'rl_opening_home_spread': None,
                        'rl_current_away_odds': None, 'rl_current_home_odds': None,
                        'rl_current_away_spread': None, 'rl_current_home_spread': None
                    })
                
                # Extract totals odds
                if totals_games and i < len(totals_games):
                    total_odds = self.extract_fanduel_odds_from_game(totals_games[i], 'totals')
                    game_info.update({
                        'total_opening_line': total_odds['opening'].get('total'),
                        'total_opening_over_odds': total_odds['opening'].get('over_odds'),
                        'total_opening_under_odds': total_odds['opening'].get('under_odds'),
                        'total_current_line': total_odds['current'].get('total'),
                        'total_current_over_odds': total_odds['current'].get('over_odds'),
                        'total_current_under_odds': total_odds['current'].get('under_odds')
                    })
                else:
                    game_info.update({
                        'total_opening_line': None, 'total_opening_over_odds': None, 'total_opening_under_odds': None,
                        'total_current_line': None, 'total_current_over_odds': None, 'total_current_under_odds': None
                    })
                
                processed_games.append(game_info)
                
            except Exception:
                continue
        
        return processed_games
    
    def get_games_for_date(self, date_str):
        """Get games for a specific date"""
        return self.scrape_date_all_bet_types(date_str)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_odds_data():
    """Load fresh odds data with caching"""
    try:
        scraper = ComprehensiveMLBScraper()
        
        today = datetime.now().strftime("%Y-%m-%d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        today_games = scraper.get_games_for_date(today)
        tomorrow_games = scraper.get_games_for_date(tomorrow)
        
        return {
            'today': pd.DataFrame(today_games) if today_games else pd.DataFrame(),
            'tomorrow': pd.DataFrame(tomorrow_games) if tomorrow_games else pd.DataFrame(),
            'last_update': datetime.now()
        }
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return {
            'today': pd.DataFrame(),
            'tomorrow': pd.DataFrame(),
            'last_update': datetime.now()
        }

def format_odds(odds_value):
    """Format odds for display"""
    if pd.isna(odds_value) or odds_value is None:
        return "Unavailable"
    
    try:
        odds = int(odds_value)
        if odds > 0:
            return f"+{odds}"
        else:
            return str(odds)
    except (ValueError, TypeError):
        return "Unavailable"

def format_spread(spread_value):
    """Format spread for display"""
    if pd.isna(spread_value) or spread_value is None:
        return "Unavailable"
    
    try:
        spread = float(spread_value)
        if spread > 0:
            return f"+{spread}"
        else:
            return str(spread)
    except (ValueError, TypeError):
        return "Unavailable"

def format_total(total_value):
    """Format total for display"""
    if pd.isna(total_value) or total_value is None:
        return "Unavailable"
    
    try:
        return f"{float(total_value)}"
    except (ValueError, TypeError):
        return "Unavailable"

def format_game_time(game_time_str):
    """Format game time to ET"""
    try:
        # Parse the ISO datetime
        dt = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))
        
        # Convert to Eastern Time
        et = timezone('US/Eastern')
        dt_et = dt.astimezone(et)
        
        # Format as time only
        return dt_et.strftime("%I:%M %p ET")
    except:
        return "TBD"

def format_date(date_str):
    """Format date for display"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%B %d, %Y")
    except:
        return date_str

def display_game_card(game):
    """Display a single game card with opening and current lines"""
    
    st.markdown(f"""
    <div class="game-card">
        <div class="game-header">
            <span class="team-name">{game['away_team']}</span> @ <span class="team-name">{game['home_team']}</span>
        </div>
        <div class="game-info">
            {game['venue']} • {format_game_time(game['game_time'])}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Opening Lines Section
    st.markdown('<div class="line-section">', unsafe_allow_html=True)
    st.markdown('<div class="line-header">📈 Opening Lines</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="bet-type-header">Moneyline</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="odds-value">{game["away_team"]}: {format_odds(game["ml_opening_away"])}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="odds-value">{game["home_team"]}: {format_odds(game["ml_opening_home"])}</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="bet-type-header">Run Line</div>', unsafe_allow_html=True)
        away_spread = format_spread(game['rl_opening_away_spread'])
        home_spread = format_spread(game['rl_opening_home_spread'])
        st.markdown(f'<div class="odds-value">{game["away_team"]} {away_spread}: {format_odds(game["rl_opening_away_odds"])}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="odds-value">{game["home_team"]} {home_spread}: {format_odds(game["rl_opening_home_odds"])}</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="bet-type-header">Total</div>', unsafe_allow_html=True)
        total_line = format_total(game['total_opening_line'])
        st.markdown(f'<div class="odds-value">O {total_line}: {format_odds(game["total_opening_over_odds"])}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="odds-value">U {total_line}: {format_odds(game["total_opening_under_odds"])}</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Current Lines Section
    st.markdown('<div class="line-section">', unsafe_allow_html=True)
    st.markdown('<div class="line-header">🔄 Current Lines</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="bet-type-header">Moneyline</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="odds-value">{game["away_team"]}: {format_odds(game["ml_current_away"])}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="odds-value">{game["home_team"]}: {format_odds(game["ml_current_home"])}</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="bet-type-header">Run Line</div>', unsafe_allow_html=True)
        away_spread = format_spread(game['rl_current_away_spread'])
        home_spread = format_spread(game['rl_current_home_spread'])
        st.markdown(f'<div class="odds-value">{game["away_team"]} {away_spread}: {format_odds(game["rl_current_away_odds"])}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="odds-value">{game["home_team"]} {home_spread}: {format_odds(game["rl_current_home_odds"])}</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="bet-type-header">Total</div>', unsafe_allow_html=True)
        total_line = format_total(game['total_current_line'])
        st.markdown(f'<div class="odds-value">O {total_line}: {format_odds(game["total_current_over_odds"])}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="odds-value">U {total_line}: {format_odds(game["total_current_under_odds"])}</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def main():
    """Main Streamlit app"""
    
    # Header
    st.title("⚾ MLB Odds Tracker - FanDuel Lines")
    st.markdown("*Real-time opening vs current odds*")
    
    # Refresh button
    col1, col2, col3 = st.columns([1, 1, 4])
    
    with col1:
        if st.button("🔄 Refresh Data", type="primary"):
            st.cache_data.clear()
            st.rerun()
    
    with col2:
        auto_refresh = st.checkbox("Auto-refresh (5 min)", value=False)
    
    # Load data
    with st.spinner("Loading latest odds..."):
        data = load_odds_data()
    
    today_df = data['today']
    tomorrow_df = data['tomorrow']
    last_update = data['last_update']
    
    # Display last update info
    st.markdown(f"""
    <div class="refresh-info">
    📊 <strong>Last Updated:</strong> {last_update.strftime('%I:%M:%S %p ET')} | 
    <strong>Source:</strong> 🏆 SportsbookReview (FanDuel) | 
    <strong>Today:</strong> {len(today_df)} games | 
    <strong>Tomorrow:</strong> {len(tomorrow_df)} games
    </div>
    """, unsafe_allow_html=True)
    
    # Create tabs for today and tomorrow
    today_date = datetime.now().strftime("%Y-%m-%d")
    tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
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
    
    # Auto-refresh functionality
    if auto_refresh:
        time.sleep(300)  # Wait 5 minutes
        st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 1rem;'>
    <small>
    Data sourced from SportsbookReview.com • FanDuel odds only • 
    Updates every 5 minutes when refreshed • 
    For entertainment purposes only
    </small>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
