from dhanhq import dhanhq
import os
from dotenv import load_dotenv
import pdb
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from datetime import date, time
import requests
import time
import json
from datetime import time as dt_time

load_dotenv()

token_id = os.getenv("DHAN_ACCESS_TOKEN")
client_code = os.getenv("DHAN_CLIENT_ID")

dhan        = dhanhq(client_code, token_id)

class Tools:
	
	def __init__(self):
		print("Tools Loaded")

	def get_instrument_file(self) -> pd.DataFrame:
		"""Loads today's Dhan instrument file, or downloads it if not present."""
		try:
			current_date = time.strftime("%Y-%m-%d")
			file_name = f"all_instruments_{current_date}.csv"
			file_path = os.path.join("Dependencies", file_name)

			# Make sure data/ directory exists
			os.makedirs("Dependencies", exist_ok=True)

			# If file already exists, load it
			if os.path.exists(file_path):
				df = pd.read_csv(file_path, low_memory=False)
			else:
				# Download fresh file from Dhan
				url = "https://images.dhan.co/api-data/api-scrip-master.csv"
				df = pd.read_csv(url, low_memory=False)
				df.to_csv(file_path, index=False)

			# Store as class attribute
			instrument_df = df
		except Exception as e:
			print("Error getting instrument file!!")


	def get_atm_strike(self, ltp: float, strike_step: int = 50) -> int:
		"""
		Rounds LTP to nearest ATM strike using given strike step (default 50).
		"""
		return int(round(ltp / strike_step) * strike_step)

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
		"""
		ltp_data = dhan.ohlc_data(securities = {"IDX_I":[13]})
		print(ltp_data)
		ltp      = ltp_data['data']['data']['IDX_I']['13']['last_price']
		# print("Current Ltp:", ltp)
		time.sleep(1)
		expiry_list = dhan.expiry_list(under_security_id=13, under_exchange_segment="IDX_I")
		latest_expiry = expiry_list['data']['data'][0]
		# print("✅ Latest Expiry:", latest_expiry)
		time.sleep(3)
		option_response = dhan.option_chain(
			under_security_id=13,                      
			under_exchange_segment="IDX_I",
			expiry=latest_expiry)
		# print(option_response)
		time.sleep(1)
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
		filtered_strikes = self.extract_strikes(oc_data, atm, depth=3)
		oc_df = self.oc_to_df(filtered_strikes)
		# print(oc_df)

		# def get_nearest_filtered_option_loose(df, atm_strike):
		result = {}
		# Filter CE
		ce_df = oc_df[oc_df['CE LTP'].between(100, 150)].copy()
		ce_df['distance'] = (ce_df['STRIKE'] - atm).abs()
		if not ce_df.empty:
			ce_best = ce_df.sort_values(by='distance').iloc[0]
			result["CE"] = {
				"name": f"NIFTY{int(ce_best['STRIKE'])}CE",
				"ltp": float(ce_best['CE LTP']),
				"strike": int(ce_best['STRIKE'])
			}
		# Filter PE
		pe_df = oc_df[oc_df['PE LTP'].between(100, 150)].copy()
		pe_df['distance'] = (pe_df['STRIKE'] - atm).abs()
		if not pe_df.empty:
			pe_best = pe_df.sort_values(by='distance').iloc[0]
			result["PE"] = {
				"name": f"NIFTY{int(pe_best['STRIKE'])}PE",
				"ltp": float(pe_best['PE LTP']),
				"strike": int(pe_best['STRIKE'])
			}

		# print(result)

		expiry_date_str = latest_expiry
		expiry_dt = datetime.strptime(expiry_date_str, "%Y-%m-%d")
		expiry_display = expiry_dt.strftime("%d %b").upper()

		if 'CE' not in result:
			raise ValueError("No suitable CE option found.")
		ce_strike = result['CE']['strike']
		selected_ce_name = f"NIFTY {expiry_display} {ce_strike} CALL"
		# pdb.set_trace()
		# If PE is not found, raise an error
		if 'PE' not in result:
			raise ValueError("No suitable PE option found.")
		pe_strike = result['PE']['strike']
		selected_pe_name = f"NIFTY {expiry_display} {pe_strike} PUT"
		todays_date = datetime.now().date()
		# current_dt = datetime.strptime(str(todays_date), "%Y-%m-%d")
		previous_date = todays_date - timedelta(days=1)
		previous_file_path = rf"C:\Users\Infinity\OneDrive\डेस्कटॉप\Project Alpha\Alpha advanced\Dependencies\all_instruments_{previous_date}.csv"
		if os.path.exists(previous_file_path):
			os.remove(previous_file_path)
			print(f"Deleted: {previous_file_path}")
		
		
		file_path = rf"C:\Users\Infinity\OneDrive\डेस्कटॉप\Project Alpha\Alpha advanced\Dependencies\all_instruments_{todays_date}.csv"
		os.makedirs("Dependencies", exist_ok=True)
		if os.path.exists(file_path):
			print("File exists")
		else:
			self.get_instrument_file()

		if os.path.exists(file_path):
			df = pd.read_csv(file_path, low_memory=False)
		else:
			# Download fresh file from Dhan
			url = "https://images.dhan.co/api-data/api-scrip-master.csv"

		instrument_df = pd.read_csv(r"C:\Users\Infinity\OneDrive\डेस्कटॉप\Project Alpha\Alpha advanced\Dependencies\all_instruments_{}.csv".format(todays_date), low_memory=False)
		selected_opts = [selected_ce_name, selected_pe_name]

		selected_instruments = instrument_df[instrument_df['SEM_CUSTOM_SYMBOL'].isin(selected_opts)]
		instrument_details = {}
		for _, row in selected_instruments.iterrows():
			name = row['SEM_CUSTOM_SYMBOL']
			instrument_details[name] = {
				'segment_id': row.get('SEM_SMST_SECURITY_ID'),
				'exchange_segment': row.get('SEM_EXM_EXCH_ID'),
				'instrument_type': row.get('SEM_INSTRUMENT_NAME'),
				'symbol': row.get('SEM_CUSTOM_SYMBOL'),
				'expiry': row.get('SEM_EXPIRY_DATE'),
				'strike_price': row.get('SEM_STRIKE_PRICE'),
				'lot_size': int(row.get('SEM_LOT_UNITS', 0))
			}
		# print(f"Instrument Details: {instrument_details}")
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
				"strike": ce_strike
			},
			"pe": {
				"name": selected_pe_name,
				"security_id": security_id_pe,
				"ltp": result['PE']['ltp'],
				"strike": pe_strike
			}
		}

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

	def get_nifty_data(self, interval=5):

		todays_date = datetime.now().date()
		current_dt = datetime.strptime(str(todays_date), "%Y-%m-%d")
		url = "https://api.dhan.co/v2/charts/intraday"
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
			"access-token": token_id,
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

	def heikin_ashi_data(self, df: pd.DataFrame) -> pd.DataFrame:
		"""
		Generates Heikin Ashi candles from standard OHLC DataFrame.
		Input columns: ['datetime', 'open', 'high', 'low', 'close']
		"""
		ha_df = pd.DataFrame(columns=["datetime", "HA_Open", "HA_High", "HA_Low", "HA_Close"])
		ha_df["datetime"] = df["datetime"]

		ha_close = []
		ha_open = []
		ha_high = []
		ha_low = []

		for i in range(len(df)):
			o = df["open"].iloc[i]
			h = df["high"].iloc[i]
			l = df["low"].iloc[i]
			c = df["close"].iloc[i]

			# ---- Compute HA Close
			ha_c = (o + h + l + c) / 4
			ha_close.append(round(ha_c, 2))

			# ---- Compute HA Open
			if i == 0:
				ha_o = (o + c) / 2  # For first candle
			else:
				ha_o = (ha_open[i-1] + ha_close[i-1]) / 2
			ha_open.append(round(ha_o, 2))

			# ---- HA High and Low
			ha_h = max(h, ha_o, ha_c)
			ha_l = min(l, ha_o, ha_c)
			ha_high.append(round(ha_h, 2))
			ha_low.append(round(ha_l, 2))

		ha_df["HA_Open"] = ha_open
		ha_df["HA_High"] = ha_high
		ha_df["HA_Low"] = ha_low
		ha_df["HA_Close"] = ha_close

		return ha_df

	def get_levels(self, ha_df: pd.DataFrame) -> dict:
		try:
			ha_df['datetime'] = pd.to_datetime(ha_df['datetime'])
			ha_df['date'] = ha_df['datetime'].dt.date

			current_date = datetime.now().date()
			current_dt = datetime.strptime(str(current_date), "%Y-%m-%d")
			backtest_date = current_date - timedelta(days=2)
			today_data = ha_df[ha_df['datetime'] == '2025-07-14 09:15:00+05:30']
			# pdb.set_trace()
			if today_data.empty:
				print("⚠️ No Heikin Ashi data found for today.")
				return None

			first_candle = today_data.iloc[0]

			levels = {
				"HA_Open": round(first_candle["HA_Open"], 2),
				"HA_High": round(first_candle["HA_High"], 2),
				"HA_Low": round(first_candle["HA_Low"], 2),
				"HA_Close": round(first_candle["HA_Close"], 2)
			}

			return levels

		except Exception as e:
			print(f"❌ Error in get_levels(): {e}")
			return None

	def get_options_data(self, security_Id=13, interval=1):

		todays_date = datetime.now().date()
		current_dt = datetime.strptime(str(todays_date), "%Y-%m-%d")
		url = "https://api.dhan.co/v2/charts/intraday"
		todays_date = datetime.now().date()
		previous_date = todays_date - timedelta(days=1)
		payload = {
			"securityId": str(security_Id),
			"exchangeSegment": "NSE_FNO",
			"instrument": "OPTIDX",
			"interval": str(interval),
			"oi": False,
			"fromDate": str(previous_date), # "2025-07-03"
			"toDate": str(todays_date), # "2025-07-04"
		}
		headers = {
			"access-token": token_id,
			"Content-Type": "application/json",
			"Accept": "application/json"
		}
		time.sleep(1)

		response = requests.post(url, json=payload, headers=headers)
		json_options_data = response.json()
		# print(json_options_data)
		candles = json_options_data
		# --- Construct DataFrame ---
		options_data = pd.DataFrame(candles, columns=[
			'timestamp', 'open', 'high', 'low', 'close', 'volume'
		])
		# Convert UNIX timestamp to datetime
		options_data['datetime'] = pd.to_datetime(options_data['timestamp'], unit='s', utc=True)
		options_data['datetime'] = options_data['datetime'].dt.tz_convert('Asia/Kolkata')
		options_data['time_only'] = options_data['datetime'].dt.time
		# Filter for Indian market hours: 09:15 to 15:30
		market_start = dt_time(9, 15)
		market_end = dt_time(15, 30)
		options_filtered = options_data[
			(options_data['time_only'] >= market_start) & (options_data['time_only'] <= market_end)
		].copy()
		options_filtered.drop(columns=['time_only'], inplace=True)
		# Optional: Reset index
		options_filtered.reset_index(drop=True, inplace=True)

		return options_filtered
	
	def stock_data(self, security_Id=13, interval=15):

		todays_date = datetime.now().date()
		current_dt = datetime.strptime(str(todays_date), "%Y-%m-%d")
		url = "https://api.dhan.co/v2/charts/intraday"
		todays_date = datetime.now().date()
		previous_date = todays_date - timedelta(days=1)
		payload = {
			"securityId": str(security_Id),
			"exchangeSegment": "NSE_EQ",
			"instrument": "EQUITY",
			"interval": str(interval),
			"oi": False,
			"fromDate": str(previous_date), # "2025-07-01"
			"toDate": str(todays_date) # "2025-07-18"
		}
		headers = {
			"access-token": token_id,
			"Content-Type": "application/json",
			"Accept": "application/json"
		}
		time.sleep(1)

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
		  
		stock_915 = stock_filtered[stock_filtered['time_only'] == dt_time(9, 15)]

		final_df = stock_915[(stock_915['open'] == stock_915['high']) | (stock_915['open'] == stock_915['low'])]
		final_df.reset_index(drop=True, inplace=True)
	  
		# print(final_df)
		# pdb.set_trace()
		return final_df
	
	def get_security_id(self, selected_opts):

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
	
	def get_open_high_low_dicts(self, stock_list):
		"""
		Scans 160 stocks for Open=High / Open=Low at 9:15 candle.
		Returns: open_high_dict, open_low_dict
		"""
		open_high_dict = {}
		open_low_dict = {}

		instrument_data = self.get_security_id(stock_list)

		for stock_name, details in instrument_data.items():
			try:
				stock_id = details['segment_id']
				ohlc_df = self.stock_data(stock_id)

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

		return open_high_dict, open_low_dict

	def get_latest_expiry(self, security_id: int, exchange_segment: str = "NSE_EQ") -> str:
		expiry_data = dhan.expiry_list(under_security_id=security_id, under_exchange_segment=exchange_segment)
		expiry = expiry_data['data']['data'][0]
		return expiry
	
	def get_stock_option_chain(self, stock_security_id: int, exchange_segment: str = "NSE_EQ"):
		expiry = self.get_latest_expiry(stock_security_id, exchange_segment)
		time.sleep(1)
		option_chain = dhan.option_chain(
			under_security_id=stock_security_id,
			under_exchange_segment=exchange_segment,
			expiry=expiry
		)
		return option_chain['data']['data']['oc'], expiry
	
	def extract_stock_strikes(self, oc_data: dict, stock_name: str, atm_strike: float, depth: int = 3):
		strikes = {}
		try:
			all_strikes = sorted([float(k) for k in oc_data.keys()])
			target_strikes = [atm_strike + i * 10 for i in range(-depth, depth + 1)]

			for strike in target_strikes:
				strike_key = f"{strike:.6f}"
				data = oc_data.get(strike_key, {})
				ce = data.get("ce")
				pe = data.get("pe")

				if ce:
					strikes[f"{stock_name}{int(strike)}CE"] = ce
				if pe:
					strikes[f"{stock_name}{int(strike)}PE"] = pe

			return strikes
		except Exception as e:
			print(f"❌ Error filtering stock strikes: {e}")
			return {}