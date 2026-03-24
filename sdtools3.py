import requests
import pandas as pd
import numpy as np
from datetime import time as dt_time
from datetime import datetime, time, date, timedelta
import os
from dotenv import load_dotenv
import pdb
from dhanhq import dhanhq

load_dotenv()
token_id2 = os.getenv("DHAN_ACCESS_TOKEN2")
token_id = os.getenv("DHAN_ACCESS_TOKEN")
client_code = os.getenv("DHAN_CLIENT_ID")
sdtoken_id = os.getenv("SD_ACCESS_TOKEN")
sdclient_code = os.getenv("SD_CLIENT_ID")

dhan        = dhanhq(client_code, token_id)

class SDTools3:

    def __init__(self):
        print("Sandbox Tools loaded in Mode 1")

    def send_telegram(self, message):
        try:
            import requests

            TELEGRAM_BOT_TOKEN = ""
            TELEGRAM_CHAT_ID = ""
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
            requests.post(url, data=data)
        except Exception as e:
            print(f"❌ Failed to send Telegram alert: {e}")

    def get_instrument_file(self) -> pd.DataFrame:
        """Loads today's Dhan instrument file, or downloads it if not present."""
        try:
            todays_date = datetime.now().date()
            current_date = todays_date.strftime("%Y-%m-%d")
            previous_date = todays_date - timedelta(days=1)
            yesterdays_date = previous_date.strftime("%Y-%m-%d")
            file_name = f"all_instruments_{current_date}.csv"
            file_path = os.path.join("Dependencies", file_name)
            file2_name = f"all_instruments_{yesterdays_date}.csv"
            file2_path = os.path.join("Dependencies", file2_name)
            # Make sure data/ directory exists
            os.makedirs("Dependencies", exist_ok=True)
            # If file already exists, load it
            if os.path.exists(file_path):
                df = pd.read_csv(file_path, low_memory=False)
            else:
                # Download fresh file from Dhan
                print("downloading file ")
                url = "https://images.dhan.co/api-data/api-scrip-master.csv"
                df = pd.read_csv(url, low_memory=False)
                df.to_csv(file_path, index=False)
                os.remove(file2_path)  # Remove previous day's file if it exists

            # Store as class attribute
            instrument_df = df
        except Exception as e:
            print(f"Error getting instrument file: {e}")

    def get_security_id_options(self, selected_opts):

        from datetime import datetime, timedelta

        todays_date = datetime.now().date()
        instrument_df = pd.read_csv(r"C:\Users\Infinity\OneDrive\डेस्कटॉप\Project Alpha\Alpha_pro\Alpha_v1_pro\Dependencies\all_instruments_{}.csv".format(todays_date), low_memory=False)

        selected_instruments = instrument_df[instrument_df['SEM_CUSTOM_SYMBOL'].isin(selected_opts)]
        instrument_details = {}
        for _, row in selected_instruments.iterrows():
            name = row['SEM_CUSTOM_SYMBOL']
            instrument_details[name] = {
                'stock_name': row.get('SEM_TRADING_SYMBOL'),
                'segment_id': row.get('SEM_SMST_SECURITY_ID'),
                'exchange_segment': row.get('SEM_EXM_EXCH_ID'),
                'instrument_type': row.get('SEM_INSTRUMENT_NAME'),
                'symbol': row.get('SEM_CUSTOM_SYMBOL'),
                'lot_size': int(row.get('SEM_LOT_UNITS', 0))
            }
        # print(f"Instrument Details: {instrument_details}")
        return instrument_details
    
    def get_atm_strike(self, ltp: float, strike_step: int = 50) -> int:
        """
        Rounds LTP to nearest ATM strike using given strike step (default 50).
        """
        return int(math.ceil(ltp / strike_step) * strike_step)

    def extract_strikes(self, option_chain_oc: dict, atm_strike: float, depth: int = 1, symbol="NIFTY"):
        strikes = {}
        try:
            all_strikes = sorted([float(k) for k in option_chain_oc.keys()])
            target_strikes = [atm_strike + i * 50 for i in range(-depth, depth + 1)]

            for strike in target_strikes:
                strike_key = f"{strike:.6f}"  # match Dhan's formatting
                data = option_chain_oc.get(strike_key, {})
                ce = data.get("ce")
                pe = data.get("pe")

                if ce:
                    strikes[f"{symbol}{int(strike)}CE"] = ce  # or ce['security_id'] if present
                if pe:
                    strikes[f"{symbol}{int(strike)}PE"] = pe  # or pe['security_id'] if present

            return strikes
        except Exception as e:
            print(f"❌ Error while filtering strikes: {e}")
            return {}

    def oc_to_df(self, strikes_dict):
        """
        Accepts a dict like: { 'NIFTY25500CE': ce_data, 'NIFTY25500PE': pe_data }
        Returns a combined DataFrame with each strike on one row (with both CE and PE).
        """
        combined = {}

        for key, data in strikes_dict.items():
            # Extract strike and type
            if 'CE' in key:
                strike = key.replace('NIFTY', '').replace('CE', '')
                if strike not in combined:
                    combined[strike] = {}
                combined[strike]['ce'] = data
            elif 'PE' in key:
                strike = key.replace('NIFTY', '').replace('PE', '')
                if strike not in combined:
                    combined[strike] = {}
                combined[strike]['pe'] = data

        # Now make DataFrame
        rows = []
        for strike, contracts in combined.items():
            ce = contracts.get('ce', {})
            pe = contracts.get('pe', {})

            row = {
                # CE
                'CE gamma': ce.get('greeks', {}).get('gamma'),
                'CE vega': ce.get('greeks', {}).get('vega'),
                'CE theta': ce.get('greeks', {}).get('theta'),
                'CE delta': ce.get('greeks', {}).get('delta'),
                'CE IV': ce.get('implied_volatility'),
                'CE OI': ce.get('oi'),
                'CE LTP': ce.get('last_price'),
                # strike
                'STRIKE': int(strike),
                # PE
                'PE LTP': pe.get('last_price'),
                'PE OI': pe.get('oi'),
                'PE IV': pe.get('implied_volatility'),
                'PE delta': pe.get('greeks', {}).get('delta'),
                'PE theta': pe.get('greeks', {}).get('theta'),
                'PE vega': pe.get('greeks', {}).get('vega'),
                'PE gamma': pe.get('greeks', {}).get('gamma'),
            }
            rows.append(row)

        return pd.DataFrame(rows).sort_values(by='STRIKE').reset_index(drop=True)

    def get_ce_pe(self):
        """ Fetches the latest option chain for NIFTY, extracts ATM strikes,
        and returns the nearest CE and PE option data. And from that option data Security IDS are patched.
        The function also fetches the latest LTP and expiry date for NIFTY options.

        3 seconds sleep
        """
        ltp_data = dhan.ohlc_data(securities = {"IDX_I":[13]})
        #print(ltp_data)
        ltp      = ltp_data['data']['data']['IDX_I']['13']['last_price']
        #print("Current Ltp:", ltp)
        #time.sleep(1)
        now = datetime.now()
        today = now.strftime('%A')
        # print(today)
        expiry_list = dhan.expiry_list(under_security_id=13, under_exchange_segment="IDX_I")
        # print(expiry_list)
        if today == "Tuesday":
            latest_expiry = expiry_list['data']['data'][1]
        else:
            latest_expiry = expiry_list['data']['data'][0]
        
        # print("✅ Latest Expiry:", latest_expiry)
        #time.sleep(1)
        option_response = dhan.option_chain(
            under_security_id=13,                      
            under_exchange_segment="IDX_I",
            expiry=latest_expiry)
        #print(option_response)
        #time.sleep(1)
        try:
            oc_data = option_response['data']['data']['oc']
            if not oc_data:
                print("⚠️ Option Chain not available or API limit hit.")
                return None
        except KeyError:
            print("❌ KeyError: Option chain data not available.")
            return None

        atm = self.get_atm_strike(ltp)
        # pdb.set_trace()
        if today == "Tuesday":
            filtered_strikes = self.extract_strikes(oc_data, atm, depth=6)
        else:
            filtered_strikes = self.extract_strikes(oc_data, atm, depth=3)
        
        oc_df = self.oc_to_df(filtered_strikes)
        # print(oc_df)
        
        # def get_nearest_filtered_option_loose(df, atm_strike):
        result = {}
        ce_choice = self.pick_option_pro(oc_df, "CE", atm, ltp_threshold=100, min_ltp=50)
        # Filter CE
        if ce_choice is None:
            # nothing matched threshold for CE -> raise (you asked no fallback)
            raise ValueError("No suitable CE option found by pick_option()")
        result["CE"] = {
            "name": f"NIFTY{int(ce_choice['strike'])}CE",
            "ltp": float(ce_choice['ltp']),
            "strike": int(ce_choice['strike'])
        }
        print("Selected CE:", result["CE"])
        '''
        ce_df = oc_df[oc_df['CE LTP'].between(75, 100)].copy()
        ce_df['distance'] = (ce_df['STRIKE'] - atm).abs()
        if not ce_df.empty:
            ce_best = ce_df.sort_values(by='distance').iloc[0]
            result["CE"] = {
                "name": f"NIFTY{int(ce_best['STRIKE'])}CE",
                "ltp": float(ce_best['CE LTP']),
                "strike": int(ce_best['STRIKE'])
            }
        '''
        # Filter PE
        pe_choice = self.pick_option_pro(oc_df, "PE", atm, ltp_threshold=100, min_ltp=50)
        if pe_choice is None:
            raise ValueError("No suitable PE option found by pick_option()")
        result["PE"] = {
            "name": f"NIFTY{int(pe_choice['strike'])}PE",
            "ltp": float(pe_choice['ltp']),
            "strike": int(pe_choice['strike'])
        }
        print("Selected PE:", result["PE"])
        '''
        pe_df = oc_df[oc_df['PE LTP'].between(75, 100)].copy()
        pe_df['distance'] = (pe_df['STRIKE'] - atm).abs()
        if not pe_df.empty:
            pe_best = pe_df.sort_values(by='distance').iloc[0]
            result["PE"] = {
                "name": f"NIFTY{int(pe_best['STRIKE'])}PE",
                "ltp": float(pe_best['PE LTP']),
                "strike": int(pe_best['STRIKE'])
            }
        '''
        print(result)

        expiry_date_str = latest_expiry
        expiry_dt = datetime.strptime(expiry_date_str, "%Y-%m-%d")
        expiry_display = expiry_dt.strftime("%d %b").upper()

        if 'CE' not in result:
            raise ValueError("No suitable CE option found.")
        ce_strike = result['CE']['strike']
        selected_ce_name = f"NIFTY {expiry_display} {ce_strike} CALL"
        # print("Selected CE Option:", selected_ce_name)
        # pdb.set_trace()
        if 'PE' not in result:
            raise ValueError("No suitable PE option found.")
        pe_strike = result['PE']['strike']
        selected_pe_name = f"NIFTY {expiry_display} {pe_strike} PUT"
        # print("Selected PE Option:", selected_pe_name)
        selected_opts = [selected_ce_name, selected_pe_name]
        # print(selected_opts)
        instrument_details = self.get_security_id_options(selected_opts)
        
        # pdb.set_trace()
        security_id_ce = instrument_details[selected_ce_name]['segment_id']
        security_id_pe = instrument_details[selected_pe_name]['segment_id']
        
        
        # print("security Id CE:", security_id_ce)
        # print("security Id PE:", security_id_pe)

        return {
            "nifty": {
                "ltp": ltp
            },
            "ce": {
                "name": selected_ce_name,
                "security_id": security_id_ce,
                "ltp": result['CE']['ltp'],
                "strike": ce_strike,
            },
            "pe": {
                "name": selected_pe_name,
                "security_id": security_id_pe,
                "ltp": result['PE']['ltp'],
                "strike": pe_strike,
            }
        }

    def get_fib_levels(self, df: pd.DataFrame,
                    target_date: date = None,
                    base_time: time = dt_time(9, 15),
                    anchor: str = "low",
                    rounding: int = 2) -> dict:
        """
        Precise Fibonacci levels based on the day's 15-min reference candle.
        - df: 15-min OHLC DataFrame with a 'datetime' column.
        - target_date: date to compute for (default today).
        - base_time: time of the reference candle (default 09:15).
        - anchor: "low" (low + ratio*range) or "high" (high - ratio*range).
        - rounding: decimals to round final levels to (default 2).
        Returns dict with range_high, range_low, range, levels (dict), and df (DataFrame).
        """
        import pandas as pd
        from datetime import date as _date

        # default date
        if target_date is None:
            target_date = _date.today()

        df = df.copy()
        df['datetime'] = pd.to_datetime(df['datetime'])

        # Ensure times are in Asia/Kolkata to match broker charts (if timezone-naive, localize)
        try:
            if df['datetime'].dt.tz is None:
                df['datetime'] = df['datetime'].dt.tz_localize('Asia/Kolkata')
            else:
                df['datetime'] = df['datetime'].dt.tz_convert('Asia/Kolkata')
        except Exception:
            # if tz ops fail, continue with naive datetimes (still OK if your df already in IST)
            pass

        # Filter to the target date
        df_date = df[df['datetime'].dt.date == target_date].sort_values('datetime')
        if df_date.empty:
            raise ValueError(f"No data for date {target_date}")

        # Try to find exact base_time candle (09:15). If not found, fallback to first candle of the day.
        cand = df_date[df_date['datetime'].dt.time == base_time]
        if cand.empty:
            reference = df_date.iloc[0]   # fallback
        else:
            reference = cand.iloc[0]

        range_high = float(reference['high'])
        range_low = float(reference['low'])
        range_val = range_high - range_low

        # Ratios and labels requested
        fib_ratios = [
            (0.5, "Mid Level"),
            (0.726, "Resistance 1"),
            (0.786, "Resistance 2"),
            (1.218, "Extension 1"),
            (1.618, "Extension 2"),
            (2.618, "Extension 3"),
            (0.284, "Support 2"),
            (0.224, "Support 1"),
            (-0.218, "Deep Support 1"),
            (-0.618, "Deep Support 2"),
            (-1.618, "Deep Support 3"),
        ]

        levels = {}
        rows = []
        for ratio, label in fib_ratios:
            if anchor == "low":
                val = range_low + (range_val * ratio)
            elif anchor == "high":
                val = range_high - (range_val * ratio)
            else:
                raise ValueError("anchor must be 'low' or 'high'")

            # keep full precision until final rounding
            levels[ratio] = round(float(val), rounding)
            rows.append({'ratio': ratio, 'level': levels[ratio], 'type': label})

        levels_df = pd.DataFrame(sorted(rows, key=lambda r: r['ratio'], reverse=True))

        return {
            'range_high': round(range_high, rounding),
            'range_low': round(range_low, rounding),
            'range': round(range_val, rounding),
            'levels': levels,
            'df': levels_df,
            'anchor': anchor
        }

    def pick_option_pro(self, oc_df, option_type, atm_strike, ltp_threshold=90, min_ltp=60):
        """
        Pick CE/PE option based on LTP range.
        
        - Starts from ATM strike.
        - If ATM LTP < min_ltp => search ITM (toward higher LTP).
        - Otherwise => search OTM (toward lower LTP).
        
        Returns dict: {"strike": int, "ltp": float, "name": str} or None if nothing found.
        """
        # Determine strike column name
        if "STRIKE" in oc_df.columns:
            strike_col = "STRIKE"
        elif "Strike Price" in oc_df.columns:
            strike_col = "Strike Price"
        else:
            raise ValueError("Strike column not found in option chain DataFrame")

        # Select LTP column
        if option_type == 'CE':
            ltp_col = 'CE LTP'
        else:
            ltp_col = 'PE LTP'

        if ltp_col not in oc_df.columns:
            raise ValueError(f"{ltp_col} column not present in option chain DataFrame")

        # Get ATM row
        atm_row = oc_df[oc_df[strike_col] == atm_strike]
        if atm_row.empty:
            raise ValueError(f"ATM strike {atm_strike} not found in option chain")

        atm_ltp = float(atm_row.iloc[-1][ltp_col])

        # --- Decide Direction ---
        if atm_ltp < min_ltp:
            # go ITM (looking for higher LTP)
            if option_type == 'CE':
                strikes = sorted([s for s in oc_df[strike_col].unique() if s <= atm_strike], reverse=True)
            else:
                strikes = sorted([s for s in oc_df[strike_col].unique() if s >= atm_strike])
        else:
            # go OTM (looking for cheaper options)
            if option_type == 'CE':
                strikes = sorted([s for s in oc_df[strike_col].unique() if s >= atm_strike])
            else:
                strikes = sorted([s for s in oc_df[strike_col].unique() if s <= atm_strike], reverse=True)

        # --- Iterate and find suitable option ---
        for strike in strikes:
            rows = oc_df[oc_df[strike_col] == strike]
            if rows.empty:
                continue

            try:
                ltp = float(rows.iloc[-1][ltp_col])
            except Exception:
                continue

            # Check LTP range
            if min_ltp <= ltp <= ltp_threshold:
                return {
                    "strike": int(strike),
                    "ltp": ltp,
                    "name": f"NIFTY {int(strike)} {option_type}"
                }

        # nothing found
        return None
        
    def intra_data(self, security_id, interval):

        url = "https://sandbox.dhan.co/v2/charts/intraday"
        todays_date = datetime.now().date()
        previous_date = todays_date - timedelta(days=5)
        
        payload = {
            "securityId": str(security_id),
            "exchangeSegment": "NSE_EQ",
            "instrument": "EQUITY",
            "interval": str(interval),
            "fromDate": str(previous_date),
            "toDate": str(todays_date)
        }
        headers = {
            "access-token": sdtoken_id,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)
        json_data = response.json()
        #print(json_data)
        candles = json_data
        # --- Construct DataFrame ---
        stock_data = pd.DataFrame(candles, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume'
        ])
        # Convert UNIX timestamp to datetime
        stock_data['datetime'] = pd.to_datetime(stock_data['timestamp'], unit='s', utc=True)
        stock_data['datetime'] = stock_data['datetime'].dt.tz_convert('Asia/Kolkata')
        stock_data['time_only'] = stock_data['datetime'].dt.time
        # Filter for Indian market hours: 09:15 to 15:30
        market_start = dt_time(9, 15)
        market_end = dt_time(15, 30)
        stock_filtered = stock_data[
            (stock_data['time_only'] >= market_start) & (stock_data['time_only'] <= market_end)
        ].copy()
        stock_filtered.drop(columns=['time_only'], inplace=True)
        # Optional: Reset index
        stock_filtered.reset_index(drop=True, inplace=True)
        #print(stock_filtered)

        return stock_filtered

    def stock_data(self, security_Id, interval, todays_date):
        print(f"Fetching stock data for Security ID: {security_Id} with interval: {interval} minutes")
        
        current_dt = datetime.strptime(str(todays_date), "%Y-%m-%d")
        url = "https://sandbox.dhan.co/v2/charts/intraday"
        # todays_date = datetime.now().date()
        previous_date = todays_date - timedelta(days=5)
        payload = {
            "securityId": str(security_Id),
            "exchangeSegment": "NSE_EQ",
            "instrument": "EQUITY",
            "interval": str(interval),
            "oi": False,
            "fromDate": str(todays_date), # "2025-07-01"
            "toDate": str(todays_date) # "2025-07-18"
        }
        headers = {
            "access-token": sdtoken_id,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        time.sleep(1)
        # 
        response = requests.post(url, json=payload, headers=headers)
        json_stock_data = response.json()
        #print(json_stock_data)
        candles = json_stock_data
        # --- Construct DataFrame ---
        stock_data = pd.DataFrame(candles, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume'
        ])
        # Convert UNIX timestamp to datetime
        stock_data['datetime'] = pd.to_datetime(stock_data['timestamp'], unit='s', utc=True)
        stock_data['datetime'] = stock_data['datetime'].dt.tz_convert('Asia/Kolkata')
        stock_data['time_only'] = stock_data['datetime'].dt.time
        # Filter for Indian market hours: 09:15 to 15:30
        market_start = dt_time(9, 15)
        market_end = dt_time(15, 30)
        stock_filtered = stock_data[
            (stock_data['time_only'] >= market_start) & (stock_data['time_only'] <= market_end)
        ].copy()
        # print(json_stock_data)
        # pdb.set_trace()
        # stock_filtered.drop(columns=['time_only'], inplace=True)
        # stock_filtered.reset_index(drop=True, inplace=True)
        #print(stock_filtered)
        stock_915 = stock_filtered[stock_filtered['time_only'] == dt_time(9, 15)].copy()
        if stock_915.empty:
                return pd.DataFrame()
        stock_915['range_pct'] = (stock_915['high'] - stock_915['low']) / stock_915['open']
        final_df = stock_915[
            ((stock_915['open'] == stock_915['high']) | (stock_915['open'] == stock_915['low'])) &
            (stock_915['range_pct'] < 0.04)
        ].copy()
        final_df.reset_index(drop=True, inplace=True)
        #print(stock_915)
        # print(final_df)
        
        return final_df

    def get_nifty_data(self, interval=5, back_date=None):

        todays_date = datetime.now().date()
        current_dt = datetime.strptime(str(todays_date), "%Y-%m-%d")
        url = "https://sandbox.dhan.co/v2/charts/intraday"
        todays_date = datetime.now().date() # "2025-09-30"
        previous_date = back_date - timedelta(days=3) #"2025-09-01" 
        payload = {
            "securityId": "13",
            "exchangeSegment": "IDX_I",
            "instrument": "INDEX",
            "interval": str(interval),
            "oi": False,
            "fromDate": str(previous_date), # "2025-07-03"
            "toDate": str(back_date) # "2025-07-04"
        }
        headers = {
            "access-token": sdtoken_id,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)
        json_data = response.json()
        # print(json_data)
        candles = json_data
        # --- Construct DataFrame ---
        nifty_data = pd.DataFrame(candles, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume'
        ])
        # Convert UNIX timestamp to datetime
        nifty_data['datetime'] = pd.to_datetime(nifty_data['timestamp'], unit='s', utc=True)
        nifty_data['datetime'] = nifty_data['datetime'].dt.tz_convert('Asia/Kolkata')
        nifty_data['time_only'] = nifty_data['datetime'].dt.time
        # Filter for Indian market hours: 09:15 to 15:30
        market_start = dt_time(9, 15)
        market_end = dt_time(15, 30)
        nifty_filtered = nifty_data[
            (nifty_data['time_only'] >= market_start) & (nifty_data['time_only'] <= market_end)
        ].copy()
        nifty_filtered.drop(columns=['time_only'], inplace=True)
        # Optional: Reset index
        nifty_filtered.reset_index(drop=True, inplace=True)
        nifty_filtered['ema_9'] = (nifty_filtered['close'].ewm(span=9, adjust=False).mean())
        nifty_filtered = nifty_filtered.round(2)
        # print(nifty_filtered)

        return nifty_filtered

    def sd_security_id(self, selected_opts):

        from datetime import datetime, timedelta

        todays_date = datetime.now().date()
        # instrument_df = pd.read_csv(r"C:\Users\Infinity\OneDrive\डेस्कटॉप\Project Alpha\Alpha_pro\Alpha_v1_pro\Dependencies\all_instruments_{}.csv".format(todays_date), low_memory=False)
        instrument_df = pd.read_csv(r"C:\Users\Infinity\OneDrive\डेस्कटॉप\Project Alpha\Alpha_pro\Alpha_v1_pro\Dependencies\all_instruments_2025-12-03.csv", low_memory=False)

        selected_instruments = instrument_df[instrument_df['SEM_TRADING_SYMBOL'].isin(selected_opts)]
        instrument_details = {}
        for _, row in selected_instruments.iterrows():
            name = row['SEM_TRADING_SYMBOL']
            instrument_details[name] = {
                'stock_name': row.get('SEM_TRADING_SYMBOL'),
                'segment_id': row.get('SEM_SMST_SECURITY_ID'),
                'exchange_segment': row.get('SEM_EXM_EXCH_ID'),
                'instrument_type': row.get('SEM_INSTRUMENT_NAME'),
                'symbol': row.get('SEM_CUSTOM_SYMBOL'),
                'lot_size': int(row.get('SEM_LOT_UNITS', 0))
            }
        # print(f"Instrument Details: {instrument_details}")
        return instrument_details

    def compute_indicators(self, df,    
                        ema_periods=(9, 21),    
                        sma_periods=(9, 21),    
                        rsi_period=9,    
                        adx_period=9,    
                        fillna=False):    
        """
        Add EMA, SMA, RSI, and ADX indicators to a copy of dataframe.

        Args:
            df (pd.DataFrame): must contain columns: open, high, low, close, volume (case-insensitive)
            ema_periods (tuple): EMA periods to compute
            sma_periods (tuple): SMA periods to compute
            rsi_period (int): RSI lookback
            adx_period (int): ADX lookback (also used for DI length)
            fillna (bool): if True, fill initial NaNs (forward/backward fill)

        Returns:
            pd.DataFrame: copy of df with indicator columns added.
        """
        # defensive copy
        df = df.copy()

        # normalize column names
        df.columns = [c.lower() for c in df.columns]

        # required columns
        required = ['open', 'high', 'low', 'close', 'volume']
        for col in required:
            if col not in df.columns:
                raise ValueError(f"Missing required column '{col}' in dataframe")

        # convert to numeric (coerce bad values to NaN)
        for col in required:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        if len(df) == 0:
            return df

        # --- EMA ---
        for p in ema_periods:
            df[f'ema_{p}'] = df['close'].ewm(span=p, adjust=False).mean()

        # --- SMA ---
        for p in sma_periods:
            df[f'sma_{p}'] = df['close'].rolling(window=p, min_periods=1).mean()

        # --- RSI (Wilder's method) ---
        delta = df['close'].diff()
        up = delta.clip(lower=0.0)
        down = -delta.clip(upper=0.0)

        alpha = 1.0 / rsi_period
        avg_gain = up.ewm(alpha=alpha, adjust=False).mean()
        avg_loss = down.ewm(alpha=alpha, adjust=False).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.fillna(50)  # neutral when insufficient data
        df[f'rsi_{rsi_period}'] = rsi

        # --- ADX (Wilder's method) ---
        high = df['high']
        low = df['low']
        close = df['close']

        up_move = high - high.shift(1)
        down_move = low.shift(1) - low

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        alpha = 1.0 / adx_period
        atr = tr.ewm(alpha=alpha, adjust=False).mean()
        plus_dm_s = pd.Series(plus_dm, index=df.index).ewm(alpha=alpha, adjust=False).mean()
        minus_dm_s = pd.Series(minus_dm, index=df.index).ewm(alpha=alpha, adjust=False).mean()

        plus_di = 100 * (plus_dm_s / atr)
        minus_di = 100 * (minus_dm_s / atr)

        dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di))
        adx = dx.ewm(alpha=alpha, adjust=False).mean()

        df[f'plus_di_{adx_period}'] = plus_di.fillna(0)
        df[f'minus_di_{adx_period}'] = minus_di.fillna(0)
        df[f'adx_{adx_period}'] = adx.fillna(0)

        # Optional: fill missing values
        if fillna:
            df.fillna(method='ffill', inplace=True)
            df.fillna(method='bfill', inplace=True)

        return df

    def sd_open_high_low_dicts(self, stock_list, todays_date):
        """
        Scans 160 stocks for Open=High / Open=Low at 9:15 candle.
        Returns: open_high_dict, open_low_dict
        """
        open_high_dict = {}
        open_low_dict = {}

        instrument_data = self.sd_security_id(stock_list)
        # print(instrument_data)
        for stock_name, details in instrument_data.items():
            try:
                stock_id = details['segment_id']
                ohlc_df = self.stock_data(security_Id=stock_id, interval=15, todays_date=todays_date)
                # print(ohlc_df)
                # pdb.set_trace()
                if ohlc_df.empty:
                    continue

                row = ohlc_df.iloc[0]  # 9:15 candle
                o, h, l, c = row['open'], row['high'], row['low'], row['close']

                if o == h:
                    open_high_dict[stock_name] = {
                        "security_id": stock_id,
                        "open": o,
                        "high": h,
                        "low": l,
                        "close": c
                    }

                elif o == l:
                    open_low_dict[stock_name] = {
                        "security_id": stock_id,
                        "open": o,
                        "high": h,
                        "low": l,
                        "close": c
                    }

            except Exception as e:
                print(f"❌ Error for {stock_name}: {e}")
                continue
        if not open_high_dict:
            print("📭 open_high_dict is empty!")
        else:
            print("✅ Open High Stocks found.")
            print(open_high_dict)
            self.send_telegram(f"Open High Stocks to be traded today : {open_high_dict}")

        if not open_low_dict:
            print("📭 open_low_dict is empty!")
        else:
            print("✅ Open Low Stocks found.")
            print(open_low_dict)
            self.send_telegram(f"Open Low Stocks to be traded today : {open_low_dict}")
        # pdb.set_trace()
        return open_high_dict, open_low_dict
    
    def sd_check_call_entry1(self, stock_name, stock_id):
        """
        Check if a CALL entry is valid for the given stock.
        """
        current_time = datetime.now().time()
        print(f"🔍 Checking entry for {stock_name} | Security ID: {stock_id}")
        ohlc_df = self.intra_data(security_id=stock_id, interval=5)
        # print(ohlc_df)
        if ohlc_df.empty:
            print(f"❌ No data available for {stock_name}. Skipping entry check.")
            return False
        # Calculate values
        out = self.compute_indicators(ohlc_df, ema_periods=(9,21), sma_periods=(9,21), rsi_period=9, adx_period=9, fillna=False)
        for col in ['ema_9', 'ema_21', 'sma_9', 'sma_21', 'rsi_9', 'adx_9']:
            if col in out.columns:
                out[col] = out[col].round(2)
        latest_data = out.iloc[-1]
        previous_data = out.iloc[-2]
        prepre_data = out.iloc[-3]
        #print(latest_data)
        #print(previous_data)
        # print(out)
        prepre_adx = prepre_data['adx_9']
        latest_close = latest_data['close']
        previous_high  = previous_data['high']
        previous_low   = previous_data['low']
        latest_open  = latest_data['open']
        latest_ema9   = latest_data['ema_9']
        latest_ema21  = latest_data['ema_21']
        # latest_rsi   = out['rsi_9'].iloc[-1]
        latest_adx   = latest_data['adx_9']
        previous_adx = previous_data['adx_9']
        previous_open = previous_data['open']
        previous_close = previous_data['close']
        latest_high = latest_data['high']
        latest_low = latest_data['low']
        previous_ema9 = previous_data['ema_9']
        previous_ema21 = previous_data['ema_21']

        C1 = bool(previous_close > previous_ema9) and (previous_close > previous_ema21)
        C2 = bool(latest_ema9 > latest_ema21)
        C3 = bool((latest_adx > 20) and (latest_close > latest_open) and (latest_adx < 45))
        C4 = bool((previous_high - previous_low) < (0.002 * previous_open))  # 0.2% of the open price
        C5 = bool((previous_close - previous_open) < (0.0004 * previous_open))  # 0.04% of the open price
        C6 = bool((previous_close - previous_ema9) < (0.003 * previous_open))  # 0.3% of the open price
        C7 = bool((previous_open != previous_low) or (previous_open != previous_high))
        C8 = bool((latest_open > previous_open) and (latest_close > previous_close))
        C9 = bool(latest_ema9 > previous_ema9)
        C10 = bool((previous_high != previous_close) or (previous_low != previous_close) or (latest_open != latest_high) or (latest_open != latest_low))
        C11 = bool((latest_adx > previous_adx) or (latest_adx > prepre_adx))

        call_entry = bool(C1 and C2 and C3 and C4 and C5 and C6 and C7 and C8 and C9 and C10 and C11)
        #print(f"✅ Entry CONFIRMED in Bot1 for {stock_name} [CALL] at {latest_close} on {current_time} \n Conditions Satisfied : \n latest OHLC valus: {latest_open}, {latest_high}, {latest_low}, {latest_close} \n latest EMA9: {latest_ema9} \n latest EMA21: {latest_ema21} \n latest ADX: {latest_adx} \n Call_entry: {call_entry}")
        #pdb.set_trace()
        # Check conditions
        if call_entry == True:
            print(f"✅ Bot1 Entry CONFIRMED for {stock_name} [CALL] at {latest_close}")
            msg1 = f"✅ Entry CONFIRMED in Bot1 for {stock_name} [CALL] at {latest_close} on {current_time} \n Conditions Satisfied : \n previous OHLC valus: {previous_open}, {previous_high}, {previous_low}, {previous_close} \n latest EMA9: {latest_ema9} and previous EMA9: {previous_ema9} \n latest EMA21: {latest_ema21} and previous ema21 {previous_ema21}\n latest ADX: {latest_adx} previous adx: {previous_adx}\n C7 check: {C7}, Call_entry: {call_entry}"
            self.send_telegram(msg1)
            return True
        else:
            print(f"❌ Entry NOT CONFIRMED for {stock_name} at [CALL] side direction at {latest_close}")
            # print(f"Latest Close: {latest_close}, Latest MA: {latest_ma}, Latest RSI: {latest_rsi}, Latest ADX: {latest_adx}")
            # print(f"Conditions not met for {stock_name}.")
        return False
    
    def sd_check_put_entry1(self, stock_name, stock_id):
        """
        Check if a PUT entry is valid for the given stock.
        """

        print(f"🔍 Checking entry for {stock_name} | Security ID: {stock_id}")
        ohlc_df = self.intra_data(security_id=stock_id, interval=5)
        current_time = datetime.now().time()
        # print(ohlc_df)
        if ohlc_df.empty:
            print(f"❌ No data available for {stock_name}. Skipping entry check.")
            return False
        # Calculate values
        out = self.compute_indicators(ohlc_df, ema_periods=(9,21), sma_periods=(9,21), rsi_period=9, adx_period=9, fillna=False)
        for col in ['ema_9', 'ema_21', 'sma_9', 'sma_21', 'rsi_9', 'adx_9']:
            if col in out.columns:
                out[col] = out[col].round(2)
        latest_data = out.iloc[-1]
        previous_data = out.iloc[-2]
        prepre_data = out.iloc[-3]
        
        prepre_adx = prepre_data['adx_9']
        latest_close = latest_data['close']
        previous_high  = previous_data['high']
        previous_low   = previous_data['low']
        latest_open  = latest_data['open']

        latest_high  = latest_data['high']
        latest_low   = latest_data['low']
        latest_ema9   = latest_data['ema_9']
        latest_ema21  = latest_data['ema_21']
        # latest_rsi   = out['rsi_9'].iloc[-1]
        latest_adx   = latest_data['adx_9']
        previous_adx = previous_data['adx_9']
        previous_open = previous_data['open']
        previous_close = previous_data['close']
        previous_ema9 = previous_data['ema_9']
        previous_ema21 = previous_data['ema_21']

        C1  = bool(previous_close < previous_ema9) and (previous_close < previous_ema21)
        C2  = bool(latest_ema9 < latest_ema21)
        C3  = bool((latest_adx > 20) and (latest_close < latest_open) and (latest_adx < 45))
        C4  = bool((previous_high - previous_low) < (0.002 * previous_open))  # 0.2% of the open price
        C5  = bool((previous_open - previous_close) < (0.0004 * previous_open))  # 0.04% of the open price
        C6  = bool((previous_ema9 - previous_close) < (0.003 * previous_open))  # 0.3% of the open price
        C7  = bool((previous_open != previous_low) or (previous_open != previous_high))
        C8  = bool((latest_open < previous_open) and (latest_close < previous_close))
        C9  = bool(latest_ema9 < previous_ema9)
        C10 = bool((previous_high != previous_close) or (previous_low != previous_close) or (latest_open != latest_high) or (latest_open != latest_low))
        C11 = bool((latest_adx > previous_adx) or (latest_adx > prepre_adx))

        put_entry = bool(C1 and C2 and C3 and C4 and C5 and C6 and C7 and C8 and C9 and C10 and C11)

        if put_entry == True:
            print(f"✅Bot1  Entry CONFIRMED for {stock_name} [PUT] at {latest_close}")
            #msg2 = f"✅ Entry CONFIRMED in Bot1 for {stock_name} at [PUT] side direction at {latest_close} on {current_time} \n Conditions Satisfied : \n latest OHLC valus: {latest_open}, {latest_high}, {latest_low}, {latest_close} \n latest EMA9: {latest_ema9} \n latest EMA21: {latest_ema21} \n latest ADX: {latest_adx} \n Call_entry: {put_entry}"
            msg2 = f"✅ Entry CONFIRMED in Bot1 for {stock_name} [PUT] at {latest_close} on {current_time} \n Conditions Satisfied : \n previous OHLC valus: {previous_open}, {previous_high}, {previous_low}, {previous_close} \n latest EMA9: {latest_ema9} and previous EMA9: {previous_ema9} \n latest EMA21: {latest_ema21} and previous ema21 {previous_ema21}\n latest ADX: {latest_adx} previous adx: {previous_adx}\n Put_entry: {put_entry}"
            self.send_telegram(msg2)
            return True
        else:
            print(f"❌ Entry NOT CONFIRMED for {stock_name} [PUT] at {latest_close}")
            return False

    def Call_entry_check(self, df, fib_data):
        """
        Backtest CALL entries on given OHLC dataframe.
        It computes indicators if not already present and checks each candle
        starting from the 3rd row (since we need prepre, previous, latest).
        """
        df = df.copy()
        print(df)
        fib_data = fib_data.copy()
        mid_level      = fib_data['df'].loc[fib_data['df']['ratio'] == 0.500, 'level'].iloc[0]
        Resistance_1   = fib_data['df'].loc[fib_data['df']['ratio'] == 0.726, 'level'].iloc[0]
        Resistance_2   = fib_data['df'].loc[fib_data['df']['ratio'] == 0.786, 'level'].iloc[0]
        Extension_1    = fib_data['df'].loc[fib_data['df']['ratio'] == 1.218, 'level'].iloc[0]
        Extension_2    = fib_data['df'].loc[fib_data['df']['ratio'] == 1.618, 'level'].iloc[0]
        Extension_3    = fib_data['df'].loc[fib_data['df']['ratio'] == 2.618, 'level'].iloc[0]
        Support_2      = fib_data['df'].loc[fib_data['df']['ratio'] == 0.284, 'level'].iloc[0]
        Support_1      = fib_data['df'].loc[fib_data['df']['ratio'] == 0.224, 'level'].iloc[0]                
        Deep_Support_1 = fib_data['df'].loc[fib_data['df']['ratio'] == -0.218, 'level'].iloc[0]
        Deep_Support_2 = fib_data['df'].loc[fib_data['df']['ratio'] == -0.618, 'level'].iloc[0]
        Deep_Support_3 = fib_data['df'].loc[fib_data['df']['ratio'] == -1.618, 'level'].iloc[0]
        fib_range      = fib_data['range']
        fib_range_high = fib_data['range_high']
        fib_range_low  = fib_data['range_low']
        print(f"Fibonacci Levels: Mid: {mid_level}")
    # Step 1: Add result columns
        df['call_entry'] = False

    # Step 2: Loop through candles from index 2 onwards
        for i in range(2, len(df)):
            prepre = df.iloc[i-2]
            prev = df.iloc[i-1]
            curr = df.iloc[i]

        # Extract required values
            prepre_high = prepre['high']
            prepre_low = prepre['low']
            prepre_open = prepre['open']
            prepre_close = prepre['close']

            previous_high = prev['high']
            previous_low = prev['low']
            previous_open = prev['open']
            previous_close = prev['close']
            previous_ema9 = prev['ema_9']

            latest_open = curr['open']
            latest_high = curr['high']
            latest_low = curr['low']
            latest_close = curr['close']
            latest_ema9 = curr['ema_9']

        # --- CALL ENTRY CONDITIONS ---

        # --- Mid level ENTRY CONDITIONS ---
            A1  = ((previous_close > previous_open) and (latest_close > previous_open) and (latest_close > previous_ema9))
            A2  = ((latest_close > mid_level) and (previous_close > mid_level) and (previous_open < mid_level))
            A3  = (((previous_high - previous_low) < 30) and ((previous_close - previous_open) < 20)) 
            A4  = (previous_high != previous_close) 
            A5  = (previous_open != previous_high)
            A6  = (previous_open != previous_low)
            A7  = (previous_low != previous_close)

            mid_level_ce = all([A1, A2, A3, A4, A5, A6, A7])

        # --- Upper_golden_ce ENTRY CONDITIONS ---   
            B1  = ((previous_close > previous_open) and (latest_close > previous_open) and (latest_close > previous_ema9))
            B2  = ((latest_close > Resistance_2) and (previous_close > Resistance_2) and (previous_open < Resistance_2))
            B3  = (((previous_high - previous_low) < 30) and ((previous_close - previous_open) < 20))
            B4  = (previous_high != previous_close) 
            B5  = (previous_open != previous_high)
            B6  = (previous_open != previous_low)
            B7  = (previous_low != previous_close)

            upper_golden_ce = all([B1, B2, B3, B4, B5, B6, B7])

        # --- Lower_golden_ce ENTRY CONDITIONS ---   
            C1  = ((previous_close > previous_open) and (latest_close > previous_open) and (latest_close > previous_ema9))
            C2  = ((latest_close > Support_2) and (previous_close > Support_2) and (previous_open < Support_2))
            C3  = (((previous_high - previous_low) < 30) and ((previous_close - previous_open) < 20))
            C4  = (previous_high != previous_close) 
            C5  = (previous_open != previous_high)
            C6  = (previous_open != previous_low)
            C7  = (previous_low != previous_close)

            lower_golden_ce = all([C1, C2, C3, C4, C5, C6, C7])

        # --- Extension_1 ENTRY CONDITIONS ---   
            D1  = ((previous_close > previous_open) and (latest_close > previous_open) and (latest_close > previous_ema9))
            D2  = ((latest_close > Extension_1) and (previous_close > Extension_1) and (previous_open < Extension_1))
            D3  = (((previous_high - previous_low) < 30) and ((previous_close - previous_open) < 20))
            D4  = (previous_high != previous_close) 
            D5  = (previous_open != previous_high)
            D6  = (previous_open != previous_low)
            D7  = (previous_low != previous_close)

            Extension_1_ce = all([D1, D2, D3, D4, D5, D6, D7])

        # --- Deep_Support_1 ENTRY CONDITIONS ---   
            E1  = ((previous_close > previous_open) and (latest_close > previous_open) and (latest_close > previous_ema9))
            E2  = ((latest_close > Deep_Support_1) and (previous_close > Deep_Support_1) and (previous_open < Deep_Support_1))
            E3  = (((previous_high - previous_low) < 30) and ((previous_close - previous_open) < 20))
            E4  = (previous_high != previous_close) 
            E5  = (previous_open != previous_high)
            E6  = (previous_open != previous_low)
            E7  = (previous_low != previous_close)

            Deep_Support_1_ce = all([E1, E2, E3, E4, E5, E6, E7])

        # --- Golden Zone reversal ENTRY CONDITIONS ---
            K1  = ((previous_close < previous_open) and (latest_close > previous_close) and (latest_close > previous_ema9))
            K2  = ((latest_close > Resistance_2) and (previous_open > Resistance_2) and (previous_low < Resistance_2))
            K3  = (((previous_high - previous_low) < 30) and ((previous_open - previous_close) < 20))
            K4  = (previous_high != previous_close) 
            K5  = (previous_open != previous_high)
            K6  = (previous_open != previous_low)
            K7  = (previous_low != previous_close)

            Reverse_golden_zone_ce = all([K1, K2, K3, K4, K5, K6, K7])

            if mid_level_ce or upper_golden_ce or lower_golden_ce or Extension_1_ce or Deep_Support_1_ce or Reverse_golden_zone_ce:
                call_entry = True
                print(call_entry)
            else:
                call_entry = False


        # Step 3: Assign to the current row
            df.at[i, 'call_entry'] = call_entry

        return df
    
    def Put_entry_check(self, df, fib_data):
        """
        Backtest PUT entries on given OHLC dataframe.
        It computes indicators if not already present and checks each candle
        starting from the 3rd row (since we need prepre, previous, latest).
        """
        df = df.copy()
        fib_data = fib_data.copy()
        mid_level      = fib_data['df'].loc[fib_data['df']['ratio'] == 0.500, 'level'].iloc[0]
        Resistance_1   = fib_data['df'].loc[fib_data['df']['ratio'] == 0.726, 'level'].iloc[0]
        Resistance_2   = fib_data['df'].loc[fib_data['df']['ratio'] == 0.786, 'level'].iloc[0]
        Extension_1    = fib_data['df'].loc[fib_data['df']['ratio'] == 1.218, 'level'].iloc[0]
        Extension_2    = fib_data['df'].loc[fib_data['df']['ratio'] == 1.618, 'level'].iloc[0]
        Extension_3    = fib_data['df'].loc[fib_data['df']['ratio'] == 2.618, 'level'].iloc[0]
        Support_2      = fib_data['df'].loc[fib_data['df']['ratio'] == 0.284, 'level'].iloc[0]
        Support_1      = fib_data['df'].loc[fib_data['df']['ratio'] == 0.224, 'level'].iloc[0]                
        Deep_Support_1 = fib_data['df'].loc[fib_data['df']['ratio'] == -0.218, 'level'].iloc[0]
        Deep_Support_2 = fib_data['df'].loc[fib_data['df']['ratio'] == -0.618, 'level'].iloc[0]
        Deep_Support_3 = fib_data['df'].loc[fib_data['df']['ratio'] == -1.618, 'level'].iloc[0]
        fib_range      = fib_data['range']
        fib_range_high = fib_data['range_high']
        fib_range_low  = fib_data['range_low']

    # Step 1: Add result columns
        df['put_entry'] = False

    # Step 2: Loop through candles from index 2 onwards
        for i in range(2, len(df)):
            prepre = df.iloc[i-2]
            prev = df.iloc[i-1]
            curr = df.iloc[i]

        # Extract required values
            prepre_high = prepre['high']
            prepre_low = prepre['low']
            prepre_open = prepre['open']
            prepre_close = prepre['close']
            previous_high = prev['high']
            previous_low = prev['low']
            previous_open = prev['open']
            previous_close = prev['close']
            previous_ema9 = prev['ema_9']

            latest_open = curr['open']
            latest_high = curr['high']
            latest_low = curr['low']
            latest_close = curr['close']

        # --- Put ENTRY CONDITIONS ---

        # --- Mid level ENTRY CONDITIONS ---
            F1  = ((previous_close < previous_open) and (latest_close < previous_open) and (latest_close < previous_ema9))
            F2  = ((latest_close < mid_level) and (previous_close < mid_level) and (previous_open > mid_level))
            F3  = (((previous_high - previous_low) < 30) and ((previous_open - previous_close) < 20))
            F4  = (previous_high != previous_close) 
            F5  = (previous_open != previous_high)
            F6  = (previous_open != previous_low)
            F7  = (previous_low != previous_close)

            mid_level_pe = all([F1, F2, F3, F4, F5, F6, F7])

        # --- Upper_golden_ce ENTRY CONDITIONS ---   
            G1  = ((previous_close < previous_open) and (latest_close < previous_open) and (latest_close < previous_ema9))
            G2  = ((latest_close < Resistance_2) and (previous_close < Resistance_2) and (previous_open > Resistance_1))
            G3  = (((previous_high - previous_low) < 30) and ((previous_open - previous_close) < 20))
            G4  = (previous_high != previous_close) 
            G5  = (previous_open != previous_high)
            G6  = (previous_open != previous_low)
            G7  = (previous_low != previous_close)

            upper_golden_pe = all([G1, G2, G3, G4, G5, G6, G7])

        # --- Lower_golden_ce ENTRY CONDITIONS ---   
            H1  = ((previous_close < previous_open) and (latest_close < previous_open) and (latest_close < previous_ema9))
            H2  = ((latest_close < Support_2) and (previous_close < Support_2) and (previous_open > Support_1))
            H3  = (((previous_high - previous_low) < 30) and ((previous_open - previous_close) < 20))
            H4  = (previous_high != previous_close) 
            H5  = (previous_open != previous_high)
            H6  = (previous_open != previous_low)
            H7  = (previous_low != previous_close)

            lower_golden_pe = all([H1, H2, H3, H4, H5, H6, H7])

        # --- Extension_1 ENTRY CONDITIONS ---   
            I1  = ((previous_close < previous_open) and (latest_close < previous_open) and (latest_close < previous_ema9))
            I2  = ((latest_close < Extension_1) and (previous_close < Extension_1) and (previous_open > Extension_1))
            I3  = (((previous_high - previous_low) < 30) and ((previous_open - previous_close) < 20))
            I4  = (previous_high != previous_close) 
            I5  = (previous_open != previous_high)
            I6  = (previous_open != previous_low)
            I7  = (previous_low != previous_close)

            Extension_1_pe = all([I1, I2, I3, I4, I5, I6, I7])

        # --- Deep_Support_1 ENTRY CONDITIONS ---   
            J1  = ((previous_close < previous_open) and (latest_close < previous_open) and (latest_close < previous_ema9))
            J2  = ((latest_close < Deep_Support_1) and (previous_close < Deep_Support_1) and (previous_open > Deep_Support_1))
            J3  = (((previous_high - previous_low) < 30) and ((previous_open - previous_close) < 20))
            J4  = (previous_high != previous_close) 
            J5  = (previous_open != previous_high)
            J6  = (previous_open != previous_low)
            J7  = (previous_low != previous_close)

            Deep_Support_1_pe = all([J1, J2, J3, J4, J5, J6, J7])

        # --- Golden Zone Reversal ENTRY CONDITIONS ---   
            I1  = ((previous_close > previous_open) and (latest_close > previous_open) and (latest_close > previous_ema9))
            I2  = ((latest_close < Support_2) and (previous_open < Support_2) and (previous_high > Support_2))
            I3  = (((previous_high - previous_low) < 30) and ((previous_close - previous_open) < 20))
            I4  = (previous_high != previous_close) 
            I5  = (previous_open != previous_high)
            I6  = (previous_open != previous_low)
            I7  = (previous_low != previous_close)

            Reverse_golden_zone_pe = all([I1, I2, I3, I4, I5, I6, I7])

            if mid_level_pe or upper_golden_pe or lower_golden_pe or Extension_1_pe or Deep_Support_1_pe or Reverse_golden_zone_pe:
                put_entry = True
                print(put_entry)
            else:
                put_entry = False

        # Step 3: Assign to the current row
            df.at[i, 'put_entry'] = put_entry

        return df

    def get_fib_levels(self, df: pd.DataFrame,
                    target_date: date = None,
                    base_time: time = time(9, 15),
                    anchor: str = "low",
                    rounding: int = 2) -> dict:
        """
        Precise Fibonacci levels based on the day's 15-min reference candle.
        - df: 15-min OHLC DataFrame with a 'datetime' column.
        - target_date: date to compute for (default today).
        - base_time: time of the reference candle (default 09:15).
        - anchor: "low" (low + ratio*range) or "high" (high - ratio*range).
        - rounding: decimals to round final levels to (default 2).
        Returns dict with range_high, range_low, range, levels (dict), and df (DataFrame).
        """
        import pandas as pd
        from datetime import date as _date
        # default date
        if target_date is None:
            target_date = _date.today()

        df = df.copy()
        df['datetime'] = pd.to_datetime(df['datetime'])

        # Ensure times are in Asia/Kolkata to match broker charts (if timezone-naive, localize)
        try:
            if df['datetime'].dt.tz is None:
                df['datetime'] = df['datetime'].dt.tz_localize('Asia/Kolkata')
            else:
                df['datetime'] = df['datetime'].dt.tz_convert('Asia/Kolkata')
        except Exception:
            # if tz ops fail, continue with naive datetimes (still OK if your df already in IST)
            pass

        # Filter to the target date
        df_date = df[df['datetime'].dt.date == target_date].sort_values('datetime')
        if df_date.empty:
            raise ValueError(f"No data for date {target_date}")

        # Try to find exact base_time candle (09:15). If not found, fallback to first candle of the day.
        cand = df_date[df_date['datetime'].dt.time == base_time]
        if cand.empty:
            reference = df_date.iloc[0]   # fallback
        else:
            reference = cand.iloc[0]

        range_high = float(reference['high'])
        range_low = float(reference['low'])
        range_val = range_high - range_low

        # Ratios and labels requested
        fib_ratios = [
            (0.5, "Mid Level"),
            (0.726, "Resistance 1"),
            (0.786, "Resistance 2"),
            (1.218, "Extension 1"),
            (1.618, "Extension 2"),
            (2.618, "Extension 3"),
            (0.284, "Support 2"),
            (0.224, "Support 1"),
            (-0.218, "Deep Support 1"),
            (-0.618, "Deep Support 2"),
            (-1.618, "Deep Support 3"),
        ]

        levels = {}
        rows = []
        for ratio, label in fib_ratios:
            if anchor == "low":
                val = range_low + (range_val * ratio)
            elif anchor == "high":
                val = range_high - (range_val * ratio)
            else:
                raise ValueError("anchor must be 'low' or 'high'")

            # keep full precision until final rounding
            levels[ratio] = round(float(val), rounding)
            rows.append({'ratio': ratio, 'level': levels[ratio], 'type': label})

        levels_df = pd.DataFrame(sorted(rows, key=lambda r: r['ratio'], reverse=True))

        return {
            'range_high': round(range_high, rounding),
            'range_low': round(range_low, rounding),
            'range': round(range_val, rounding),
            'levels': levels,
            'df': levels_df,
            'anchor': anchor
        }

    def back_data(self, security_id, interval, todays_date):

        url = "https://sandbox.dhan.co/v2/charts/intraday"
        # todays_date = datetime.now().date()
        # previous_date = todays_date - timedelta(days=5)
        
        payload = {
            "securityId": str(security_id),
            "exchangeSegment": "NSE_EQ",
            "instrument": "EQUITY",
            "interval": str(interval),
            "fromDate": str(todays_date),
            "toDate": str(todays_date)
        }
        headers = {
            "access-token": sdtoken_id,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)
        json_data = response.json()
        #print(json_data)
        candles = json_data
        # --- Construct DataFrame ---
        stock_data = pd.DataFrame(candles, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume'
        ])
        # Convert UNIX timestamp to datetime
        stock_data['datetime'] = pd.to_datetime(stock_data['timestamp'], unit='s', utc=True)
        stock_data['datetime'] = stock_data['datetime'].dt.tz_convert('Asia/Kolkata')
        stock_data['time_only'] = stock_data['datetime'].dt.time
        # Filter for Indian market hours: 09:15 to 15:30
        market_start = dt_time(9, 15)
        market_end = dt_time(15, 30)
        stock_filtered = stock_data[
            (stock_data['time_only'] >= market_start) & (stock_data['time_only'] <= market_end)
        ].copy()
        stock_filtered.drop(columns=['time_only'], inplace=True)
        # Optional: Reset index
        stock_filtered.reset_index(drop=True, inplace=True)
        #print(stock_filtered)

        return stock_filtered

# Usage example:
# df = pd.read_csv("SBILIFE_15min.csv")
# result = backtest_entries(df)
# print(result[['datetime','close','call_entry','put_entry']].tail(10))
