import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Test with hardcoded data first
def create_test_data():
    """Create test data to verify the app works"""
    
    test_games = [
        {
            'date': '2025-07-25',
            'away_team': 'Miami',
            'home_team': 'Milwaukee',
            'game_time': '2025-07-25T20:10:00+00:00',
            'venue': 'American Family Field',
            'ml_opening_away': 168,
            'ml_opening_home': -200,
            'ml_current_away': 190,
            'ml_current_home': -230,
            'rl_opening_away_odds': -125,
            'rl_opening_home_odds': 104,
            'rl_opening_away_spread': 1.5,
            'rl_opening_home_spread': -1.5,
            'rl_current_away_odds': -110,
            'rl_current_home_odds': -110,
            'rl_current_away_spread': 1.5,
            'rl_current_home_spread': -1.5,
            'total_opening_line': 8.0,
            'total_opening_over_odds': -115,
            'total_opening_under_odds': -105,
            'total_current_line': 8.0,
            'total_current_over_odds': -102,
            'total_current_under_odds': -120
        },
        {
            'date': '2025-07-26',
            'away_team': 'Arizona',
            'home_team': 'Pittsburgh',
            'game_time': '2025-07-26T19:00:00+00:00',
            'venue': 'PNC Park',
            'ml_opening_away': -136,
            'ml_opening_home': 116,
            'ml_current_away': -118,
            'ml_current_home': -108,
            'rl_opening_away_odds': 122,
            'rl_opening_home_odds': -146,
            'rl_opening_away_spread': -1.5,
            'rl_opening_home_spread': 1.5,
            'rl_current_away_odds': 142,
            'rl_current_home_odds': -192,
            'rl_current_away_spread': -1.5,
            'rl_current_home_spread': 1.5,
            'total_opening_line': 9.0,
            'total_opening_over_odds': -110,
            'total_opening_under_odds': -110,
            'total_current_line': 8.5,
            'total_current_over_odds': -132,
            'total_current_under_odds': 100
        }
    ]
    
    return pd.DataFrame(test_games)

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

def display_game_card(game):
    """Display a single game card"""
    
    st.markdown(f"""
    ### {game['away_team']} @ {game['home_team']}
    **{game['venue']}** • 8:10 PM ET
    """)
    
    # Opening Lines Section
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
    
    # Current Lines Section
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
    st.title("⚾ MLB Odds Tracker - Test Version")
    st.markdown("*Testing with known working data*")
    
    # Create test data
    df = create_test_data()
    
    st.write(f"**Data loaded:** {len(df)} test games")
    
    # Filter by date
    today_games = df[df['date'] == '2025-07-25']
    tomorrow_games = df[df['date'] == '2025-07-26']
    
    # Create tabs
    tab1, tab2 = st.tabs(["📅 Today - July 25, 2025", "📅 Tomorrow - July 26, 2025"])
    
    with tab1:
        st.markdown(f"### {len(today_games)} Games Today")
        for _, game in today_games.iterrows():
            display_game_card(game)
    
    with tab2:
        st.markdown(f"### {len(tomorrow_games)} Games Tomorrow")
        for _, game in tomorrow_games.iterrows():
            display_game_card(game)
    
    # Debug info
    st.markdown("---")
    st.markdown("### Debug Info")
    st.write("DataFrame columns:", list(df.columns))
    st.dataframe(df)

if __name__ == "__main__":
    main()
