import requests
import pandas as pd
import numpy as np
from datetime import timedelta, datetime
from datetime import time as dt_time
import time
import os
from dotenv import load_dotenv
import pdb
from dhanhq import dhanhq

load_dotenv()
token_id = os.getenv("DHAN_ACCESS_TOKEN")
token_id2 = os.getenv("DHAN_ACCESS_TOKEN2")
client_code = os.getenv("DHAN_CLIENT_ID")
sdtoken_id = os.getenv("SD_ACCESS_TOKEN")
sdclient_code = os.getenv("SD_CLIENT_ID")

dhan        = dhanhq(client_code, token_id)

class SDTools1:

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
        previous_date = todays_date - timedelta(days=2)
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

    def get_nifty_data(self, interval=5):

        todays_date = datetime.now().date()
        current_dt = datetime.strptime(str(todays_date), "%Y-%m-%d")
        url = "https://sandbox.dhan.co/v2/charts/intraday"
        todays_date = datetime.now().date() # "2025-09-30"
        previous_date = todays_date - timedelta(days=5) # "2025-09-01"
        payload = {
            "securityId": "13",
            "exchangeSegment": "IDX_I",
            "instrument": "INDEX",
            "interval": str(interval),
            "oi": False,
            "fromDate": str(previous_date), # "2025-07-03"
            "toDate": str(todays_date) # "2025-07-04"
        }
        headers = {
            "access-token": token_id2,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        time.sleep(1)

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
        # print(nifty_filtered)

        return nifty_filtered
    
    def sd_security_id(self, selected_opts):

        from datetime import datetime, timedelta

        todays_date = datetime.now().date()
        instrument_df = pd.read_csv(r"C:\Users\Infinity\OneDrive\डेस्कटॉप\Project Alpha\Alpha advanced\Dependencies\all_instruments_{}.csv".format(todays_date), low_memory=False)

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

    def call_backtest_entries(self, df):
        """
        Backtest CALL entries on given OHLC dataframe.
        It computes indicators if not already present and checks each candle
        starting from the 3rd row (since we need prepre, previous, latest).
        """
        df = df.copy()

    # Step 1: Compute indicators if missing
        required_cols = ['ema_9','ema_21','sma_9','sma_21','rsi_9','adx_9']
        if not all(col in df.columns for col in required_cols):
            df = self.compute_indicators(
                df,
                ema_periods=(9, 21),
                sma_periods=(9, 21),
                rsi_period=9,
                adx_period=9,
                fillna=False)

    # Step 2: Add result columns
        df['call_entry'] = False

    # Step 3: Loop through candles from index 2 onwards
        for i in range(2, len(df)):
            prepre = df.iloc[i-2]
            prev = df.iloc[i-1]
            curr = df.iloc[i]

        # Extract required values
            prepre_adx = prepre['adx_9']
            prepre_high = prepre['high']
            prepre_low = prepre['low']
            prepre_open = prepre['open']
            prepre_close = prepre['close']
            previous_high = prev['high']
            previous_low = prev['low']
            previous_open = prev['open']
            previous_close = prev['close']
            previous_ema9 = prev['ema_9']
            previous_ema21 = prev['ema_21']
            previous_adx = prev['adx_9']

            latest_open = curr['open']
            latest_high = curr['high']
            latest_low = curr['low']
            latest_close = curr['close']
            latest_ema9 = curr['ema_9']
            latest_ema21 = curr['ema_21']
            latest_adx = curr['adx_9']

        # --- CALL ENTRY CONDITIONS ---
            '''
            Stock Call Entries :
            C1 = (previous_close > previous_ema9) and (previous_close > previous_ema21)
            C2 = (latest_ema9 > latest_ema21)
            C3 = (20 < latest_adx < 45) and (latest_close > latest_open)
            C4 = (previous_high - previous_low) < (0.002 * previous_open)
            C5 = (previous_close - previous_open) < (0.0004 * previous_open)
            C6 = (previous_close - previous_ema9) < (0.003 * previous_open)
            C7 = (latest_adx > previous_adx) or (latest_adx > prepre_adx)
            C8 = (latest_open > previous_open) and (latest_close > previous_close)
            C9 = (latest_ema9 > previous_ema9)
            C10 = (previous_high != previous_close) 
            C11 = (previous_open != previous_high)
            C12 = (previous_open != previous_low)
            C13 = (previous_low != previous_close)
            C14 = (latest_high != latest_close) 
            C15 = (latest_open != latest_high)
            C16 = (latest_open != latest_low)
            C17 = (latest_low != latest_close)
            '''
            
            C1 = (previous_close > previous_ema9) and (previous_close > previous_ema21)
            C2 = (latest_ema9 > latest_ema21)
            C3 = (20 < latest_adx < 60) and (previous_close > previous_open)
            C4 = (previous_high - previous_low) < 30
            C5 = (previous_close - previous_open) < 25
            C6 = (previous_close - previous_ema9) < 20
            C7 = (latest_adx > previous_adx) or (latest_adx > prepre_adx)
            C8 = (latest_open > previous_open) 
            C9 = (latest_ema9 > previous_ema9)
            C10 = (previous_high != previous_close) 
            C11 = (previous_open != previous_high)
            C12 = (previous_open != previous_low)
            C13 = (previous_low != previous_close)
            C14 = (latest_high != latest_close) 
            C15 = (latest_open != latest_high)
            C16 = (latest_open != latest_low)
            C17 = (latest_low != latest_close)
            C18 = (prepre_high != prepre_close) 
            C19 = (prepre_open != prepre_high)
            C20 = (prepre_open != prepre_low)
            C21 = (prepre_low != prepre_close) 
            C22 = (prepre_open < prepre_close)

            call_entry = all([C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12, C13, C14, C15, C16, C17, C18, C19, C20, C21, C22])

        # Step 4: Assign to the current row
            df.at[i, 'call_entry'] = call_entry

        return df

    def put_backtest_entries(self, df):
        """
        Backtest PUT entries on given OHLC dataframe.
        It computes indicators if not already present and checks each candle
        starting from the 3rd row (since we need prepre, previous, latest).
        """
        df = df.copy()

    # Step 1: Compute indicators if missing
        required_cols = ['ema_9','ema_21','sma_9','sma_21','rsi_9','adx_9']
        if not all(col in df.columns for col in required_cols):
            df = self.compute_indicators(
                df,
                ema_periods=(9, 21),
                sma_periods=(9, 21),
                rsi_period=9,
                adx_period=9,
                fillna=False)

    # Step 2: Add result columns
        df['put_entry'] = False

    # Step 3: Loop through candles from index 2 onwards
        for i in range(2, len(df)):
            prepre = df.iloc[i-2]
            prev = df.iloc[i-1]
            curr = df.iloc[i]

        # Extract required values
            prepre_adx = prepre['adx_9']
            prepre_high = prepre['high']
            prepre_low = prepre['low']
            prepre_open = prepre['open']
            prepre_close = prepre['close']
            previous_high = prev['high']
            previous_low = prev['low']
            previous_open = prev['open']
            previous_close = prev['close']
            previous_ema9 = prev['ema_9']
            previous_ema21 = prev['ema_21']
            previous_adx = prev['adx_9']

            latest_open = curr['open']
            latest_high = curr['high']
            latest_low = curr['low']
            latest_close = curr['close']
            latest_ema9 = curr['ema_9']
            latest_ema21 = curr['ema_21']
            latest_adx = curr['adx_9']

        # --- PUT ENTRY CONDITIONS ---
            '''
            P1 = (previous_close < previous_ema9) and (previous_close < previous_ema21)
            P2 = (latest_ema9 < latest_ema21)
            P3 = (20 < latest_adx < 45) and (latest_close < latest_open)
            P4 = (previous_high - previous_low) < (0.002 * previous_open)
            P5 = (previous_open - previous_close) < (0.0004 * previous_open)
            P6 = (previous_ema9 - previous_close) < (0.003 * previous_open)
            P7 = (latest_adx > previous_adx) or (latest_adx > prepre_adx)
            P8 = (latest_open < previous_open) and (latest_close < previous_close)
            P9 = (latest_ema9 < previous_ema9)
            P10 = (previous_high != previous_close) 
            P11 = (previous_open != previous_high)
            P12 = (previous_open != previous_low)
            P13 = (previous_low != previous_close)
            P14 = (latest_high != latest_close) 
            P15 = (latest_open != latest_high)
            P16 = (latest_open != latest_low)
            P17 = (latest_low != latest_close)
            '''
            P1 = (previous_close < previous_ema9) and (previous_close < previous_ema21)
            P2 = (latest_ema9 < latest_ema21)
            P3 = (20 < latest_adx < 60) and (previous_close < previous_open)
            P4 = (previous_high - previous_low) < 30
            P5 = (previous_open - previous_close) < 25
            P6 = (previous_ema9 - previous_close) < 20
            P7 = (latest_adx > previous_adx) or (latest_adx > prepre_adx)
            P8 = (latest_open < previous_open) 
            P9 = (latest_ema9 < previous_ema9)
            P10 = (previous_high != previous_close) 
            P11 = (previous_open != previous_high)
            P12 = (previous_open != previous_low)
            P13 = (previous_low != previous_close)
            P14 = (latest_high != latest_close) 
            P15 = (latest_open != latest_high)
            P16 = (latest_open != latest_low)
            P17 = (latest_low != latest_close)  
            P18 = (prepre_high != prepre_close) 
            P19 = (prepre_open != prepre_high)
            P20 = (prepre_open != prepre_low)
            P21 = (prepre_low != prepre_close)     
            P22 = (prepre_open > prepre_close)      

            put_entry = all([P1, P2, P3, P4, P5, P6, P7, P8, P9, P10, P11, P12, P13, P14, P15, P16, P17, P18, P19, P20, P21, P22])
        # Step 4: Assign to the current row
            df.at[i, 'put_entry'] = put_entry

        return df
    
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
