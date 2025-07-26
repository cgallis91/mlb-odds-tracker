import requests
import re
import json
import pandas as pd
from datetime import datetime, timedelta

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
            'Accept-Encoding': 'identity',  # No compression - this is the key!
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
        
        print(f"🌐 Scraping {bet_type} for {date_str}: {url}")
        
        try:
            response = self.session.get(url, timeout=30)
            
            if response.status_code != 200:
                print(f"❌ Bad status code for {bet_type}: {response.status_code}")
                return None
            
            # Extract __NEXT_DATA__
            pattern = r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'
            match = re.search(pattern, response.text, re.DOTALL)
            
            if not match:
                print(f"❌ No __NEXT_DATA__ found for {bet_type}")
                return None
            
            json_data = json.loads(match.group(1))
            
            # Extract odds data
            try:
                odds_tables = json_data['props']['pageProps']['oddsTables']
                if not odds_tables:
                    return None
                
                odds_table_model = odds_tables[0]['oddsTableModel']
                game_rows = odds_table_model.get('gameRows', [])
                
                print(f"✅ Found {len(game_rows)} games for {bet_type}")
                return game_rows
                
            except KeyError as e:
                print(f"❌ JSON structure error for {bet_type}: {e}")
                return None
                
        except Exception as e:
            print(f"💥 Error scraping {bet_type}: {e}")
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
                    # Moneyline odds
                    odds_data['opening'] = {
                        'away_odds': opening_line.get('awayOdds'),
                        'home_odds': opening_line.get('homeOdds')
                    }
                    odds_data['current'] = {
                        'away_odds': current_line.get('awayOdds'),
                        'home_odds': current_line.get('homeOdds')
                    }
                
                elif bet_type == 'pointspread':
                    # Run line (point spread)
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
                    # Over/Under totals
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
        
        print(f"\n📅 Scraping all bet types for {date_str}")
        
        # Get data for all bet types
        moneyline_games = self.scrape_bet_type(date_str, 'moneyline')
        pointspread_games = self.scrape_bet_type(date_str, 'pointspread')
        totals_games = self.scrape_bet_type(date_str, 'totals')
        
        if not moneyline_games:
            print(f"❌ No moneyline data for {date_str}")
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
                
                print(f"🎮 Game {i+1}: {game_info['away_team']} @ {game_info['home_team']}")
                
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
                    # Initialize with None if no pointspread data
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
                    # Initialize with None if no totals data
                    game_info.update({
                        'total_opening_line': None, 'total_opening_over_odds': None, 'total_opening_under_odds': None,
                        'total_current_line': None, 'total_current_over_odds': None, 'total_current_under_odds': None
                    })
                
                # Show extracted data
                ml_opening = f"{game_info['ml_opening_away']}/{game_info['ml_opening_home']}"
                ml_current = f"{game_info['ml_current_away']}/{game_info['ml_current_home']}"
                
                rl_opening = f"{game_info['rl_opening_away_spread']} ({game_info['rl_opening_away_odds']}/{game_info['rl_opening_home_odds']})"
                rl_current = f"{game_info['rl_current_away_spread']} ({game_info['rl_current_away_odds']}/{game_info['rl_current_home_odds']})"
                
                total_opening = f"{game_info['total_opening_line']} (O:{game_info['total_opening_over_odds']}/U:{game_info['total_opening_under_odds']})"
                total_current = f"{game_info['total_current_line']} (O:{game_info['total_current_over_odds']}/U:{game_info['total_current_under_odds']})"
                
                print(f"   💰 ML: {ml_opening} → {ml_current}")
                print(f"   📈 RL: {rl_opening} → {rl_current}")
                print(f"   🎯 Total: {total_opening} → {total_current}")
                
                processed_games.append(game_info)
                
            except Exception as e:
                print(f"❌ Error processing game {i}: {e}")
                continue
        
        return processed_games
    
    def get_today_tomorrow_games(self):
        """Get complete data for today and tomorrow's games"""
        
        today = datetime.now().strftime("%Y-%m-%d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        print(f"🗓️ Scraping comprehensive MLB data for {today} and {tomorrow}")
        
        all_games = []
        
        for date_str in [today, tomorrow]:
            games = self.scrape_date_all_bet_types(date_str)
            all_games.extend(games)
        
        if all_games:
            df = pd.DataFrame(all_games)
            print(f"\n🎉 SUCCESS! Found {len(df)} games with comprehensive FanDuel data")
            
            # Show summary with real data
            if not df.empty:
                print(f"\n📊 Summary:")
                print(f"   Today ({today}): {len(df[df['date'] == today])} games")
                print(f"   Tomorrow ({tomorrow}): {len(df[df['date'] == tomorrow])} games")
                
                # Show sample games with all bet types
                print(f"\n📋 Sample games with all FanDuel bet types:")
                for _, game in df.head(3).iterrows():
                    ml = f"{game['ml_current_away']}/{game['ml_current_home']}"
                    rl = f"{game['rl_current_away_spread']} ({game['rl_current_away_odds']}/{game['rl_current_home_odds']})"
                    total = f"{game['total_current_line']} (O:{game['total_current_over_odds']}/U:{game['total_current_under_odds']})"
                    
                    print(f"   {game['away_team']} @ {game['home_team']}")
                    print(f"     ML: {ml} | RL: {rl} | Total: {total}")
            
            return df
        else:
            print("❌ No games found")
            return pd.DataFrame()

def main():
    print("🚀 COMPREHENSIVE MLB Scraper - All Bet Types")
    print("🎯 Moneyline, Run Line, and Totals with Opening/Current Lines")
    print("=" * 80)
    
    scraper = ComprehensiveMLBScraper()
    df = scraper.get_today_tomorrow_games()
    
    if not df.empty:
        print(f"\n✅ COMPLETE SUCCESS! Scraped {len(df)} games with all bet types")
        
        # Save to CSV
        filename = f"comprehensive_mlb_odds_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        df.to_csv(filename, index=False)
        print(f"💾 Saved comprehensive data to: {filename}")
        
        # Show detailed sample
        print(f"\n📊 Sample game with all bet types:")
        if len(df) > 0:
            first_game = df.iloc[0]
            print(f"   🎮 {first_game['away_team']} @ {first_game['home_team']}")
            print(f"   🏟️  {first_game['venue']} - {first_game['game_time']}")
            print(f"   💰 ML Opening: {first_game['ml_opening_away']}/{first_game['ml_opening_home']}")
            print(f"   💰 ML Current: {first_game['ml_current_away']}/{first_game['ml_current_home']}")
            print(f"   📈 RL Opening: {first_game['rl_opening_away_spread']} ({first_game['rl_opening_away_odds']}/{first_game['rl_opening_home_odds']})")
            print(f"   📈 RL Current: {first_game['rl_current_away_spread']} ({first_game['rl_current_away_odds']}/{first_game['rl_current_home_odds']})")
            print(f"   🎯 Total Opening: {first_game['total_opening_line']} (O:{first_game['total_opening_over_odds']}/U:{first_game['total_opening_under_odds']})")
            print(f"   🎯 Total Current: {first_game['total_current_line']} (O:{first_game['total_current_over_odds']}/U:{first_game['total_current_under_odds']})")
        
        print(f"\n🎉 READY FOR STREAMLIT WITH ALL BET TYPES!")
        print(f"📋 Available columns: {list(df.columns)}")
        
        return df
    else:
        print(f"\n❌ No games found")
        return pd.DataFrame()

if __name__ == "__main__":
    main()
