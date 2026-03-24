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
client_code = os.getenv("DHAN_CLIENT_ID")
sdtoken_id = os.getenv("SD_ACCESS_TOKEN")
sdclient_code = os.getenv("SD_CLIENT_ID")

dhan        = dhanhq(client_code, token_id)

class SDTools2:

	def __init__(self):
		print("Sandbox Tools loaded in Mode 2")

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
		previous_date = todays_date - timedelta(days=3)
		
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
		# print(json_data)
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
		# print(stock_filtered)

		return stock_filtered

	def stock_data(self, security_Id, interval):
		print(f"Fetching stock data for Security ID: {security_Id} with interval: {interval} minutes")
		
		todays_date = datetime.now().date()
		current_dt = datetime.strptime(str(todays_date), "%Y-%m-%d")
		url = "https://sandbox.dhan.co/v2/charts/intraday"
		todays_date = datetime.now().date()
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
		# pdb.set_trace()
		response = requests.post(url, json=payload, headers=headers)
		json_stock_data = response.json()
		# print(json_options_data)
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
		# stock_filtered.drop(columns=['time_only'], inplace=True)
		# stock_filtered.reset_index(drop=True, inplace=True)
		  
		stock_915 = stock_filtered[stock_filtered['time_only'] == dt_time(9, 15)].copy()
		if stock_915.empty:
				return pd.DataFrame()
		stock_915['range_pct'] = (stock_915['high'] - stock_915['low']) / stock_915['open']
		final_df = stock_915[
			((stock_915['open'] == stock_915['high']) | (stock_915['open'] == stock_915['low'])) &
			(stock_915['range_pct'] < 0.01)
		].copy()
		final_df.reset_index(drop=True, inplace=True)
	  
		# print(final_df)
		
		return final_df
		
	def get_nifty_data(self, interval=5):

		todays_date = datetime.now().date()
		current_dt = datetime.strptime(str(todays_date), "%Y-%m-%d")
		url = "https://sandbox.dhan.co/v2/charts/intraday"
		todays_date = datetime.now().date()
		previous_date = todays_date - timedelta(days=3)
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
			"access-token": sdtoken_id,
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
	
	def compute_indicators(sel, df,
						ema_periods=(9,21),
						sma_periods=(9,21),
						rsi_period=9,
						adx_period=9,
						fillna=False):
		"""
		Add EMA, SMA, RSI and ADX indicators to a copy of dataframe.

		Args:
			df (pd.DataFrame): must contain columns: open, high, low, close, volume (case-insensitive)
			ema_periods (tuple): EMA periods to compute
			sma_periods (tuple): SMA periods to compute
			rsi_period (int): RSI lookback
			adx_period (int): ADX lookback
			fillna (bool): if True, fill initial NaNs (forward/backward fill)

		Returns:
			pd.DataFrame: copy of df with indicator columns added.
		"""
		# defensive copy
		df = df.copy()

		# normalize column names to lowercase
		df.columns = [c.lower() for c in df.columns]

		# required columns
		required = ['open', 'high', 'low', 'close', 'volume']
		for col in required:
			if col not in df.columns:
				raise ValueError(f"Missing required column '{col}' in dataframe")

		# convert to numeric (coerce bad values to NaN)
		for col in required:
			df[col] = pd.to_numeric(df[col], errors='coerce')

		# safety: if no rows return quickly
		if len(df) == 0:
			return df

		# --- EMA (exponential moving averages) ---
		for p in ema_periods:
			# ewm works from first value -> no division-by-zero
			df[f'ema_{p}'] = df['close'].ewm(span=p, adjust=False).mean()

		# --- SMA (simple moving averages) ---
		for p in sma_periods:
			df[f'sma_{p}'] = df['close'].rolling(window=p, min_periods=1).mean()

		# --- RSI (Wilder's smoothed RSI via EWM) ---
		delta = df['close'].diff()
		up = delta.clip(lower=0.0)
		down = -delta.clip(upper=0.0)

		# Wilder smoothing (use ewm with alpha = 1/period, adjust=False)
		ma_up = up.ewm(alpha=1.0/rsi_period, adjust=False).mean()
		ma_down = down.ewm(alpha=1.0/rsi_period, adjust=False).mean()

		# avoid division by zero
		rs = ma_up / ma_down.replace(0, np.nan)
		rsi = 100 - (100 / (1 + rs))
		# where ma_down == 0 -> RSI = 100 (price only went up)
		rsi = rsi.fillna(100).where(ma_up != 0, 0)  # if ma_up==0 and ma_down==0 -> 0
		df[f'rsi_{rsi_period}'] = rsi

		# --- ADX (Wilder's method) ---
		high = df['high']
		low = df['low']
		close = df['close']

		up_move = high.diff()
		down_move = low.shift(1) - low

		plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
		minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

		tr1 = high - low
		tr2 = (high - close.shift(1)).abs()
		tr3 = (low - close.shift(1)).abs()
		tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

		# Wilder smoothing of TR, +DM, -DM
		atr = tr.ewm(alpha=1.0/adx_period, adjust=False).mean()
		plus_dm_s = pd.Series(plus_dm, index=df.index).ewm(alpha=1.0/adx_period, adjust=False).mean()
		minus_dm_s = pd.Series(minus_dm, index=df.index).ewm(alpha=1.0/adx_period, adjust=False).mean()

		# +DI and -DI in percent
		# avoid division by zero
		atr_safe = atr.replace(0, np.nan)
		plus_di = 100 * (plus_dm_s / atr_safe)
		minus_di = 100 * (minus_dm_s / atr_safe)

		# DX and ADX
		dx = 100 * ( (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) )
		adx = dx.ewm(alpha=1.0/adx_period, adjust=False).mean()

		# fill back zeros where appropriate
		plus_di = plus_di.fillna(0)
		minus_di = minus_di.fillna(0)
		adx = adx.fillna(0)

		df[f'plus_di_{adx_period}'] = plus_di
		df[f'minus_di_{adx_period}'] = minus_di
		df[f'adx_{adx_period}'] = adx

		# optional fillna for early rows
		if fillna:
			df.fillna(method='ffill', inplace=True)
			df.fillna(method='bfill', inplace=True)

		return df

	def sd_open_high_low_dicts(self, stock_list):
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
				ohlc_df = self.stock_data(security_Id=stock_id, interval=15)
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
	
	def sd_check_call_entry2(self, stock_name, stock_id):
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
		print(out[['close','ema_9','ema_21','sma_9','sma_21','rsi_9','adx_9']].tail(1))
		latest_close = out['close'].iloc[-1]
		latest_high  = out['high'].iloc[-1]
		latest_low   = out['low'].iloc[-1]
		latest_open  = out['open'].iloc[-1]
		latest_ema9   = out['ema_9'].iloc[-1]
		latest_ema21  = out['ema_21'].iloc[-1]
		latest_rsi   = out['rsi_9'].iloc[-1]
		latest_adx   = out['adx_9'].iloc[-1]

		C1 = bool(latest_close > latest_ema9) and (latest_close > latest_ema21)
		C2 = bool(latest_ema9 > latest_ema21)
		C3 = bool((latest_adx > 20) and (latest_close > latest_open))
		# C4 = bool((latest_high - latest_low) < (0.002 * latest_open))  0.2% of the open price
		# C5 = bool((latest_close - latest_open) < (0.0004 * latest_open))  0.04% of the open price
		C6 = bool((latest_close - latest_ema9) < (0.02 * latest_open))  # 2% of the open price
		call_entry = bool(C1 and C2 and C3 and C6)

		# Check conditions
		if call_entry == True:
			print(f"✅ Entry CONFIRMED for {stock_name} [CALL] at {latest_close}")
			msg1 = f"✅ Entry CONFIRMED for {stock_name} [CALL] at {latest_close} on {current_time} \n Conditions Satisfied : \n latest OHLC valus: {latest_open}, {latest_high}, {latest_low}, {latest_close} \n latest EMA9: {latest_ema9} \n latest EMA21: {latest_ema21} \n latest ADX: {latest_adx} \n RSI: {latest_rsi} \n Call_entry: {call_entry}"
			self.send_telegram(msg1)
			return True
		else:
			print(f"❌ Entry NOT CONFIRMED for {stock_name} [CALL] at {latest_close}")
			# print(f"Latest Close: {latest_close}, Latest MA: {latest_ma}, Latest RSI: {latest_rsi}, Latest ADX: {latest_adx}")
			# print(f"Conditions not met for {stock_name}.")
		return False
	
	def sd_check_put_entry2(self, stock_name, stock_id):
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
		print(out[['close','ema_9','ema_21','sma_9','sma_21','rsi_9','adx_9']].tail(1))
		latest_close = out['close'].iloc[-1]
		latest_high  = out['high'].iloc[-1]
		latest_low   = out['low'].iloc[-1]
		latest_open  = out['open'].iloc[-1]
		latest_ema9   = out['ema_9'].iloc[-1]
		latest_ema21  = out['ema_21'].iloc[-1]
		latest_rsi   = out['rsi_9'].iloc[-1]
		latest_adx   = out['adx_9'].iloc[-1]

		C1 = bool(latest_close < latest_ema9) and (latest_close < latest_ema21)
		C2 = bool(latest_ema9 < latest_ema21)
		C3 = bool((latest_adx > 25) and (latest_close > latest_open))
		# C4 = bool((latest_high - latest_low) < (0.002 * latest_open))  # 0.2% of the open price
		# C5 = bool((latest_close - latest_open) < (0.0004 * latest_open))
		C6 = bool((latest_close - latest_ema9) < (0.02 * latest_open))  # 2% of the open price
		put_entry = bool(C1 and C2 and C3 and C6)

		if put_entry == True:
			print(f"✅ Entry CONFIRMED for {stock_name} [PUT] at {latest_close}")
			msg2 = f"✅ Entry CONFIRMED for {stock_name} [PUT] at {latest_close} on {current_time} \n Conditions Satisfied : \n latest OHLC valus: {latest_open}, {latest_high}, {latest_low}, {latest_close} \n latest EMA9: {latest_ema9} \n latest EMA21: {latest_ema21} \n latest ADX: {latest_adx} \n ADX: {latest_adx} \n Call_entry: {put_entry}"
			self.send_telegram(msg2)
			return True
		else:
			print(f"❌ Entry NOT CONFIRMED for {stock_name} [PUT] at {latest_close}")
			return False
