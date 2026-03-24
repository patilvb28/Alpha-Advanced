# from ws_ltp import run_ltp_socket
import datetime
import time
import os
import pandas as pd
import pdb
import requests
from datetime import date, timedelta
import json
import talib

from mock_engine import MockEngine
engine = MockEngine()
from tools import Tools
tools = Tools()

def send_telegram(message):
	try:
		import requests
		TELEGRAM_BOT_TOKEN = ""
		TELEGRAM_CHAT_ID = ""
		url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
		data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
		requests.post(url, data=data)
	except Exception as e:
		print(f"❌ Failed to send Telegram alert: {e}")

message1 = "Advanced Trading Bot Started"
send_telegram(message1)
print("Advanced Trading Bot Started")

while True:

	print("starting while Loop \n")

	current_time = datetime.datetime.now().time()
	if current_time < datetime.time(2, 30):
		print(f"Wait for market to start", current_time)
		time.sleep(1)
		continue
	time.sleep(1)

	ce_pe_data = tools.get_ce_pe()
	print(ce_pe_data)

	security_id_ce   = ce_pe_data['ce']['security_id']
	security_id_pe   = ce_pe_data['pe']['security_id']
	selected_ce_name = ce_pe_data['ce']['name']
	selected_pe_name = ce_pe_data['pe']['name']
	print(f"{security_id_ce} -> For Call \n {security_id_pe} -> For Put")
	nifty_5     = tools.get_nifty_data(interval=5)	
	nifty_df_15 = tools.get_nifty_data(interval=15)
	# nifty_df_15[['open', 'high', 'low', 'close']] = nifty_df_15[['open', 'high', 'low', 'close']].round(2)
	ha_df       = tools.heikin_ashi_data(nifty_df_15)
	ha_df[['HA_Open', 'HA_High', 'HA_Low', 'HA_Close']] = ha_df[['HA_Open', 'HA_High', 'HA_Low', 'HA_Close']].round(2)
	# print(ha_df)

	levels   = tools.get_levels(ha_df)
	ha_open  = float(levels['HA_Open'])
	ha_high  = float(levels['HA_High'])
	ha_low   = float(levels['HA_Low'])
	ha_close = float(levels['HA_Close'])

	if len(nifty_5) >= 20:
		nifty_5['ma'] = talib.MA(nifty_5['close'], timeperiod=9)
		nifty_5['adx'] = talib.ADX(nifty_5['high'], nifty_5['low'], nifty_5['close'], timeperiod=10)
		ma = nifty_5['ma'].iloc[-1]
		current_adx = nifty_5['adx'].iloc[-1]
		# print(f"🔍 Current MA: {ma} | ADX: {current_adx}")
	else:
		print("⚠️ Not enough data for ADX & MA. Skipping this loop.")
		continue

	breakout_candle  = nifty_5.iloc[-1]
	previous_candle  = nifty_5.iloc[-2]
	pc_high		     = float(previous_candle['high'])
	pc_low		     = float(previous_candle['low'])
	pc_close   		 = float(previous_candle['close'])
	pc_open		     = float(previous_candle['open'])
	breakout_point   = float(breakout_candle['open'])

	# Entry Conditions 

	# High Level Brekout plan 
	C1 = bool((pc_close > ha_high) and (pc_low < ha_high) and (breakout_point > ha_high) and (ma < pc_close) and (current_adx > 20) and ((pc_close - pc_open) < 20) and ((pc_high - pc_low) < 30))  # Call Entry Condition (ma wala condition tweak kiya hai taki test easily ho sake later edit close to open)
	C2 = bool((pc_close < ha_high) and (pc_high > ha_high) and (breakout_point < ha_high) and (ma > pc_close) and (current_adx > 20) and ((pc_open - pc_close) < 20) and ((pc_high - pc_low) < 30))  # Put Entry Condition (ma wala condition tweak kiya hai taki test easily ho sake later edit close to open) 

	# Open Level Brekout plan
	C3 = bool((pc_close > ha_open) and (pc_low < ha_open) and (breakout_point > ha_open) and (ma < pc_close) and (current_adx > 20) and ((pc_close - pc_open) < 20) and ((pc_high - pc_low) < 30)) # Call Entry Condition (ma wala condition tweak kiya hai taki test easily ho sake later edit close to open)
	C4 = bool((pc_close < ha_open) and (pc_high > ha_open) and (breakout_point < ha_open) and (ma > pc_close) and (current_adx > 20) and ((pc_open - pc_close) < 20) and ((pc_high - pc_low) < 30)) # Put Entry Condition (ma wala condition tweak kiya hai taki test easily ho sake later edit close to open)
	
	# Close Level Brekout plan
	C5 = bool((pc_close > ha_close) and (pc_low < ha_close) and (breakout_point > ha_close) and (ma < pc_close) and (current_adx > 20) and ((pc_close - pc_open) < 20) and ((pc_high - pc_low) < 30)) # Call Entry Condition (ma wala condition tweak kiya hai taki test easily ho sake later edit close to open)
	C6 = bool((pc_close < ha_close) and (pc_high > ha_close) and (breakout_point < ha_close) and (ma > pc_close) and (current_adx > 20) and ((pc_open - pc_close) < 20) and ((pc_high - pc_low) < 30)) # Put Entry Condition (ma wala condition tweak kiya hai taki test easily ho sake later edit close to open)

	# Low Level Brekout plan
	C7 = bool((pc_close > ha_low) and (pc_low < ha_low) and (breakout_point > ha_low) and (ma < pc_close) and (current_adx > 20) and ((pc_close - pc_open) < 20) and ((pc_high - pc_low) < 30)) # Call Entry Condition (ma wala condition tweak kiya hai taki test easily ho sake later edit close to open)
	C8 = bool((pc_close < ha_low) and (pc_high > ha_low) and (breakout_point < ha_low) and (ma > pc_close) and (current_adx > 20) and ((pc_open - pc_close) < 20) and ((pc_high - pc_low) < 30)) # Put Entry Condition (ma wala condition tweak kiya hai taki test easily ho sake later edit close to open)	

	# Additional Conditions
	C9  = bool((pc_open != pc_low) or (pc_open != pc_high))
	C10 = bool((pc_low - ma) <25)
	C11 = bool((ma - pc_high) <25)

	Call_Entry = bool(((C1 or C3 or C5 or C7) and C9 and C10)) # True  
	Put_Entry  = bool(((C2 or C4 or C6 or C8) and C9 and C11))  #  True
	# pdb.set_trace()
	print("Entry Conditions checked")
		
	if (Call_Entry == True) and not engine.positions:
		print(f"🟢 Call Entry Condition met for NIFTY 50 at {current_time} in {selected_ce_name}-{security_id_ce}")

		# Get last candle close as entry price
		ce_chart1 = tools.get_options_data(security_Id=security_id_ce, interval=1)
		running_candle = ce_chart1.iloc[-1]
		entry_price = running_candle['close']

		# Set quantity (e.g., 1 lot of 75)
		lot_size = 75
		qty = int(lot_size * 1)

		order = {
			"name": "NIFTY",
			"options_name": selected_ce_name,
			"buy_sell": "BUY",
			"entry_price": float(entry_price),
			"Call_Put": "Call",
			"qty": qty,
			"security_id": security_id_ce
		}
		engine.place_order(order)

		try:
			with open("data/live_feed.json", "r") as f:
				ltp_data = json.load(f)

				ltp_ce = float(ltp_data[str(security_id_ce)]["LTP"])
				ltp_pe = float(ltp_data[str(security_id_pe)]["LTP"])
				ltp_nifty = float(ltp_data["13"]["LTP"])

				print(f"📊 LTPs -> CE: {ltp_ce} | PE: {ltp_pe} | NIFTY: {ltp_nifty}")

		except Exception as e:
			print(f"❌ Error loading LTPs: {e}")

		# 🟢 Monitor and close based on SL/Target
		while engine.positions:
			engine.update_all_ltps()
			print("Updating Ltp and running loop !!")
			engine.check_and_close_positions()
			
			time.sleep(1)

	if (Put_Entry == True) and not engine.positions:
		print(f"🟢 Put Entry Condition met for NIFTY 50 at {current_time} in {selected_pe_name}-{security_id_pe}")

		# Get last candle close as entry price
		pe_chart1 = tools.get_options_data(security_Id=security_id_pe, interval=1)
		running_candle = pe_chart1.iloc[-1]
		entry_price_put = running_candle['close']

		# Set quantity (e.g., 1 lot of 75)
		lot_size = 75
		qty = int(lot_size * 1)

		order = {
			"name": "NIFTY",
			"options_name": selected_pe_name,
			"buy_sell": "BUY",
			"entry_price": float(entry_price_put),
			"Call_Put": "Call",
			"qty": qty,
			"security_id": security_id_pe
		}
		engine.place_order(order)

		try:
			with open("data/live_feed.json", "r") as f:
				ltp_data = json.load(f)

				ltp_ce = float(ltp_data[str(security_id_ce)]["LTP"])
				ltp_pe = float(ltp_data[str(security_id_pe)]["LTP"])
				ltp_nifty = float(ltp_data["13"]["LTP"])

				print(f"📊 LTPs -> CE: {ltp_ce} | PE: {ltp_pe} | NIFTY: {ltp_nifty}")

		except Exception as e:
			print(f"❌ Error loading LTPs: {e}")

		# 🟢 Monitor and close based on SL/Target
		while engine.positions:
			engine.update_all_ltps()
			print("Updating Ltp and running loop !!")
			engine.check_and_close_positions()
			
			time.sleep(1)

time.sleep(5)
pdb.set_trace()