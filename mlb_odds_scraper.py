import requests
import json
import re
import time
import random
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

class MLBOddsScraper:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://www.sportsbookreview.com/betting-odds/mlb-baseball"
        
        # Rotate user agents to avoid detection
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0'
        ]
        
        self.setup_logging()
        self.update_headers()
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def update_headers(self):
        """Update session headers with rotation"""
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none'
        }
        self.session.headers.update(headers)
    
    def safe_delay(self, min_delay=2, max_delay=5):
        """Add random delay between requests"""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
    
    def extract_next_data(self, html_content: str) -> Optional[Dict]:
        """Extract __NEXT_DATA__ JSON from HTML"""
        try:
            pattern = r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'
            match = re.search(pattern, html_content, re.DOTALL)
            
            if match:
                json_str = match.group(1)
                return json.loads(json_str)
            return None
        except Exception as e:
            self.logger.error(f"Error extracting JSON data: {e}")
            return None
    
    def fetch_odds_data(self, date_str: str, bet_type: str = 'moneyline') -> Optional[Dict]:
        """Fetch odds data for a specific date and bet type"""
        
        url_map = {
            'moneyline': f"{self.base_url}/?date={date_str}",
            'runline': f"{self.base_url}/pointspread/full-game/?date={date_str}",
            'totals': f"{self.base_url}/totals/full-game/?date={date_str}"
        }
        
        url = url_map.get(bet_type, url_map['moneyline'])
        
        try:
            self.logger.info(f"Fetching {bet_type} data for {date_str}")
            self.safe_delay()
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            json_data = self.extract_next_data(response.text)
            
            if not json_data:
                self.logger.warning(f"No JSON data found for {date_str}")
                return None
            
            # Extract odds tables
            try:
                odds_tables = json_data['props']['pageProps']['oddsTables']
                if not odds_tables:
                    self.logger.info(f"No games found for {date_str}")
                    return None
                
                return odds_tables[0]['oddsTableModel']
            
            except KeyError as e:
                self.logger.error(f"Invalid JSON structure: {e}")
                return None
                
        except requests.RequestException as e:
            self.logger.error(f"Request failed for {date_str}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return None
    
    def find_fanduel_sportsbook_id(self, sportsbooks: List[Dict]) -> Optional[str]:
        """Find FanDuel's sportsbook ID from the sportsbooks list"""
        for book in sportsbooks:
            if 'fanduel' in book.get('name', '').lower():
                return book.get('id')
        return None
    
    def extract_fanduel_odds(self, game_row: Dict, sportsbook_id: str, bet_type: str) -> Dict:
        """Extract FanDuel odds from game row"""
        odds_data = {
            'opening': {'team1': None, 'team2': None, 'total': None, 'spread': None},
            'current': {'team1': None, 'team2': None, 'total': None, 'spread': None}
        }
        
        try:
            sportsbook_data = game_row.get('sportsbookData', {}).get(sportsbook_id, {})
            
            if bet_type == 'moneyline':
                # Extract moneyline odds
                opening = sportsbook_data.get('ml', {}).get('opening', {})
                current = sportsbook_data.get('ml', {}).get('current', {})
                
                if opening:
                    odds_data['opening']['team1'] = opening.get('homeOdds')
                    odds_data['opening']['team2'] = opening.get('awayOdds')
                
                if current:
                    odds_data['current']['team1'] = current.get('homeOdds')
                    odds_data['current']['team2'] = current.get('awayOdds')
            
            elif bet_type == 'runline':
                # Extract runline odds
                opening = sportsbook_data.get('ps', {}).get('opening', {})
                current = sportsbook_data.get('ps', {}).get('current', {})
                
                if opening:
                    odds_data['opening']['team1'] = opening.get('homeOdds')
                    odds_data['opening']['team2'] = opening.get('awayOdds')
                    odds_data['opening']['spread'] = opening.get('homeSpread')
                
                if current:
                    odds_data['current']['team1'] = current.get('homeOdds')
                    odds_data['current']['team2'] = current.get('awayOdds')
                    odds_data['current']['spread'] = current.get('homeSpread')
            
            elif bet_type == 'totals':
                # Extract totals odds
                opening = sportsbook_data.get('total', {}).get('opening', {})
                current = sportsbook_data.get('total', {}).get('current', {})
                
                if opening:
                    odds_data['opening']['team1'] = opening.get('overOdds')
                    odds_data['opening']['team2'] = opening.get('underOdds')
                    odds_data['opening']['total'] = opening.get('total')
                
                if current:
                    odds_data['current']['team1'] = current.get('overOdds')
                    odds_data['current']['team2'] = current.get('underOdds')
                    odds_data['current']['total'] = current.get('total')
        
        except Exception as e:
            self.logger.error(f"Error extracting FanDuel odds: {e}")
        
        return odds_data
    
    def get_games_for_dates(self, dates: List[str]) -> pd.DataFrame:
        """Get all games data for specified dates"""
        
        all_games = []
        
        for date_str in dates:
            self.logger.info(f"Processing date: {date_str}")
            
            # Get moneyline data first (contains game info)
            moneyline_data = self.fetch_odds_data(date_str, 'moneyline')
            if not moneyline_data:
                continue
            
            # Get runline and totals data
            runline_data = self.fetch_odds_data(date_str, 'runline')
            totals_data = self.fetch_odds_data(date_str, 'totals')
            
            # Find FanDuel sportsbook ID
            sportsbooks = moneyline_data.get('sportsbooks', [])
            fanduel_id = self.find_fanduel_sportsbook_id(sportsbooks)
            
            if not fanduel_id:
                self.logger.warning(f"FanDuel not found in sportsbooks for {date_str}")
                continue
            
            # Process each game
            game_rows = moneyline_data.get('gameRows', [])
            
            for i, game_row in enumerate(game_rows):
                try:
                    # Basic game info
                    game_info = {
                        'date': date_str,
                        'game_time': game_row.get('startTime', ''),
                        'away_team': game_row.get('awayTeam', {}).get('name', ''),
                        'home_team': game_row.get('homeTeam', {}).get('name', ''),
                        'away_abbr': game_row.get('awayTeam', {}).get('abbreviation', ''),
                        'home_abbr': game_row.get('homeTeam', {}).get('abbreviation', '')
                    }
                    
                    # Extract FanDuel odds for all bet types
                    moneyline_odds = self.extract_fanduel_odds(game_row, fanduel_id, 'moneyline')
                    
                    # Get corresponding runline and totals data
                    runline_odds = {}
                    totals_odds = {}
                    
                    if runline_data and i < len(runline_data.get('gameRows', [])):
                        runline_game = runline_data['gameRows'][i]
                        runline_odds = self.extract_fanduel_odds(runline_game, fanduel_id, 'runline')
                    
                    if totals_data and i < len(totals_data.get('gameRows', [])):
                        totals_game = totals_data['gameRows'][i]
                        totals_odds = self.extract_fanduel_odds(totals_game, fanduel_id, 'totals')
                    
                    # Combine all data
                    game_data = {
                        **game_info,
                        'ml_opening_away': moneyline_odds.get('opening', {}).get('team2'),
                        'ml_opening_home': moneyline_odds.get('opening', {}).get('team1'),
                        'ml_current_away': moneyline_odds.get('current', {}).get('team2'),
                        'ml_current_home': moneyline_odds.get('current', {}).get('team1'),
                        'rl_opening_spread': runline_odds.get('opening', {}).get('spread'),
                        'rl_opening_away': runline_odds.get('opening', {}).get('team2'),
                        'rl_opening_home': runline_odds.get('opening', {}).get('team1'),
                        'rl_current_spread': runline_odds.get('current', {}).get('spread'),
                        'rl_current_away': runline_odds.get('current', {}).get('team2'),
                        'rl_current_home': runline_odds.get('current', {}).get('team1'),
                        'total_opening': totals_odds.get('opening', {}).get('total'),
                        'total_opening_over': totals_odds.get('opening', {}).get('team1'),
                        'total_opening_under': totals_odds.get('opening', {}).get('team2'),
                        'total_current': totals_odds.get('current', {}).get('total'),
                        'total_current_over': totals_odds.get('current', {}).get('team1'),
                        'total_current_under': totals_odds.get('current', {}).get('team2')
                    }
                    
                    all_games.append(game_data)
                    
                except Exception as e:
                    self.logger.error(f"Error processing game {i} for {date_str}: {e}")
                    continue
        
        return pd.DataFrame(all_games)
    
    def get_today_tomorrow_games(self) -> pd.DataFrame:
        """Get games for today and tomorrow"""
        today = datetime.now().strftime("%Y-%m-%d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        dates = [today, tomorrow]
        return self.get_games_for_dates(dates)

# Usage example
if __name__ == "__main__":
    scraper = MLBOddsScraper()
    games_df = scraper.get_today_tomorrow_games()
    
    if not games_df.empty:
        print(f"Found {len(games_df)} games")
        print(games_df.head())
        
        # Save to CSV for testing
        games_df.to_csv('mlb_odds.csv', index=False)
        print("Data saved to mlb_odds.csv")
    else:
        print("No games found")