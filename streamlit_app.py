import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging
from mlb_odds_scraper import MLBOddsScraper  # Import our scraper

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
        padding-top: 2rem;
    }
    .stDataFrame {
        width: 100%;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .positive-change {
        color: #28a745;
    }
    .negative-change {
        color: #dc3545;
    }
    .game-header {
        font-weight: bold;
        font-size: 1.1em;
        margin-bottom: 0.5rem;
    }
    .refresh-info {
        background-color: #e3f2fd;
        padding: 0.5rem;
        border-radius: 0.25rem;
        margin-bottom: 1rem;
        border-left: 4px solid #2196f3;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_odds_data():
    """Load fresh odds data with caching"""
    try:
        scraper = MLBOddsScraper()
        df = scraper.get_today_tomorrow_games()
        return df, datetime.now()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame(), datetime.now()

def format_odds(odds_value):
    """Format odds for display"""
    if pd.isna(odds_value) or odds_value is None:
        return "-"
    
    try:
        odds = int(odds_value)
        if odds > 0:
            return f"+{odds}"
        else:
            return str(odds)
    except (ValueError, TypeError):
        return "-"

def format_spread(spread_value):
    """Format spread for display"""
    if pd.isna(spread_value) or spread_value is None:
        return "-"
    
    try:
        spread = float(spread_value)
        if spread > 0:
            return f"+{spread}"
        else:
            return str(spread)
    except (ValueError, TypeError):
        return "-"

def format_total(total_value):
    """Format total for display"""
    if pd.isna(total_value) or total_value is None:
        return "-"
    
    try:
        return f"O/U {float(total_value)}"
    except (ValueError, TypeError):
        return "-"

def calculate_odds_movement(opening, current):
    """Calculate and format odds movement"""
    if pd.isna(opening) or pd.isna(current) or opening is None or current is None:
        return "", ""
    
    try:
        opening_val = int(opening)
        current_val = int(current)
        
        if opening_val == current_val:
            return "", ""
        
        # For American odds, movement direction
        movement = current_val - opening_val
        
        if movement > 0:
            return "↗️", "positive-change"
        else:
            return "↘️", "negative-change"
    
    except (ValueError, TypeError):
        return "", ""

def display_game_card(row):
    """Display a single game as a card"""
    
    with st.container():
        st.markdown(f"""
        <div class="game-header">
        {row['away_team']} @ {row['home_team']} - {row['game_time']}
        </div>
        """, unsafe_allow_html=True)
        
        # Create columns for different bet types
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            st.markdown("**Moneyline**")
            
            # Away team moneyline
            away_ml_movement, away_ml_class = calculate_odds_movement(
                row['ml_opening_away'], row['ml_current_away']
            )
            
            st.markdown(f"""
            **{row['away_abbr']}**: {format_odds(row['ml_opening_away'])} → 
            {format_odds(row['ml_current_away'])} {away_ml_movement}
            """)
            
            # Home team moneyline
            home_ml_movement, home_ml_class = calculate_odds_movement(
                row['ml_opening_home'], row['ml_current_home']
            )
            
            st.markdown(f"""
            **{row['home_abbr']}**: {format_odds(row['ml_opening_home'])} → 
            {format_odds(row['ml_current_home'])} {home_ml_movement}
            """)
        
        with col2:
            st.markdown("**Run Line**")
            
            # Display spread and odds
            spread_opening = format_spread(row['rl_opening_spread'])
            spread_current = format_spread(row['rl_current_spread'])
            
            st.markdown(f"""
            **Spread**: {spread_opening} → {spread_current}
            """)
            
            st.markdown(f"""
            **{row['away_abbr']}**: {format_odds(row['rl_opening_away'])} → {format_odds(row['rl_current_away'])}
            """)
            
            st.markdown(f"""
            **{row['home_abbr']}**: {format_odds(row['rl_opening_home'])} → {format_odds(row['rl_current_home'])}
            """)
        
        with col3:
            st.markdown("**Total**")
            
            # Display total
            total_opening = format_total(row['total_opening'])
            total_current = format_total(row['total_current'])
            
            st.markdown(f"""
            **Total**: {total_opening} → {total_current}
            """)
            
            st.markdown(f"""
            **Over**: {format_odds(row['total_opening_over'])} → {format_odds(row['total_current_over'])}
            """)
            
            st.markdown(f"""
            **Under**: {format_odds(row['total_opening_under'])} → {format_odds(row['total_current_under'])}
            """)
        
        st.divider()

def main():
    """Main Streamlit app"""
    
    # Header
    st.title("⚾ MLB Odds Tracker - FanDuel Lines")
    st.markdown("*Real-time opening vs current odds for today and tomorrow's games*")
    
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
        games_df, last_update = load_odds_data()
    
    # Display last update time
    st.markdown(f"""
    <div class="refresh-info">
    📊 <strong>Last Updated:</strong> {last_update.strftime('%I:%M:%S %p')} | 
    <strong>Games Found:</strong> {len(games_df)} | 
    <strong>Source:</strong> SportsbookReview.com (FanDuel)
    </div>
    """, unsafe_allow_html=True)
    
    if games_df.empty:
        st.warning("No games found for today or tomorrow. Check back later!")
        return
    
    # Group games by date
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    today_games = games_df[games_df['date'] == today]
    tomorrow_games = games_df[games_df['date'] == tomorrow]
    
    # Display today's games
    if not today_games.empty:
        st.header(f"🗓️ Today's Games ({today})")
        
        for _, game in today_games.iterrows():
            display_game_card(game)
    
    # Display tomorrow's games
    if not tomorrow_games.empty:
        st.header(f"🗓️ Tomorrow's Games ({tomorrow})")
        
        for _, game in tomorrow_games.iterrows():
            display_game_card(game)
    
    # Raw data section (collapsible)
    with st.expander("📋 View Raw Data"):
        st.dataframe(games_df, use_container_width=True)
    
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