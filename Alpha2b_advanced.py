# from ws_ltp import run_ltp_socket
import datetime
import time
import os
import pandas as pd
import numpy as np
import pdb
import requests
from datetime import date, timedelta
import json
from datetime import time as dt_time
from ta.trend import EMAIndicator, SMAIndicator, ADXIndicator
from ta.momentum import RSIIndicator

from mock_engine import MockEngine	
engine = MockEngine()
from tools import Tools
tools = Tools()
from sdtools2 import SDTools2
sdtools = SDTools2()

sdtools.get_instrument_file()

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

message1 = "Advanced Stock Trading Bot Started"
send_telegram(message1)
print("Advanced Stock Trading Bot Started")
tools.get_instrument_file()

current_time = datetime.datetime.now().time()
focused_opts = ["BHARTIARTL", "COALINDIA", "DIXON", "ULTRACEMCO", "UNITDSPR"]
				
main_list = ["AARTIIND", "ABB", "ABCAPITAL", "ABFRL", "ACC", "ADANIENSOL", "ADANIENT", "ADANIGREEN", "ADANIPORTS", "AMBUJACEM", "ANGELONE", "APLAPOLLO", "APOLLOHOSP", "ASHOKLEY", "ASIANPAINT", "ASTRAL", "ATGL", "AUBANK", "AUROPHARMA", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BALKRISIND", "BANDHANBNK", "BANKBARODA", "BEL", "BHARATFORG", "BHARTIARTL", "BIOCON", "BPCL", "BRITANNIA", "BSE", "BSOFT", "CAMS", "CDSL", "CGPOWER", "CHAMBLFERT", "CHOLAFIN", "CIPLA", "COALINDIA", "COFORGE", "CONCOR", "CROMPTON", "CUMMINSIND", "DABUR", "DALBHARAT", "DIVISLAB", "DIXON", "DLF", "DMART", "DRREDDY", "EICHERMOT", "ETERNAL", "EXIDEIND", "GAIL", "GLENMARK", "GODREJCP", "GODREJPROP", "GRANULES", "GRASIM", "HAL", "HAVELLS", "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDCOPPER", "HINDPETRO", "HINDUNILVR", "HINDZINC", "ICICIBANK", "ICICIGI", "ICICIPRULI", "IGL", "INDHOTEL", "INDIGO", "INDUSINDBK", "INDUSTOWER", "INFY", "IOC", "IRCTC", "IREDA", "IRFC", "ITC", "JINDALSTEL", "JIOFIN", "JSWENERGY", "JSWSTEEL", "JUBLFOOD", "KAYNES", "KFINTECH", "KOTAKBANK", "KPITTECH", "LAURUSLABS", "LICHSGFIN", "LICI", "LODHA", "LT", "LTF", "LTIM", "LUPIN", "M&M", "M&MFIN", "MANAPPURAM", "MARICO", "MARUTI", "MAZDOCK", "MFSL", "MGL", "MOTHERSON", "MPHASIS", "MUTHOOTFIN", "NATIONALUM", "NAUKRI", "NCC", "NESTLEIND", "NTPC", "NYKAA", "OBEROIRLTY", "OFSS", "OIL", "ONGC", "PEL", "PERSISTENT", "PETRONET", "PFC", "PIDILITIND", "PIIND", "PNBHOUSING", "POLYCAB", "POWERGRID", "PPLPHARMA", "RECLTD", "RELIANCE", "RVNL", "SBICARD", "SBILIFE", "SBIN", "SHRIRAMFIN", "SIEMENS", "SOLARINDS", "SRF", "SUNPHARMA", "TATACHEM", "TATACOMM", "TATACONSUM", "TATAELXSI", "TATAMOTORS", "TATAPOWER", "TATATECH", "TCS", "TECHM", "TIINDIA", "TITAN", "TORNTPHARM", "TORNTPOWER", "TRENT", "TVSMOTOR", "ULTRACEMCO", "UNITDSPR", "UNOMINDA", "UPL", "VBL", "VEDL", "VOLTAS", "WIPRO", "ZYDUSLIFE"]

while True:
	print("Scan Loop begins 🔄\n")
	current_time = datetime.datetime.now().time()
	print("Current time:", current_time)
	# time.sleep(5)
	
	# Wait if before market time
	if current_time < datetime.time(9, 31):
		print(f"⏳ Waiting for market to start: {current_time}")
		time.sleep(5)
		continue

	# Start scanning exactly at 9:30-9:33
	elif datetime.time(9, 31) <= current_time < datetime.time(9, 35):
		print("🚀 Scan begins")
		# nifty_df_15 = sdtools.get_nifty_data(interval=15)
		# print(nifty_df_15)
		# stock_data = sdtools.stock_data(security_Id=13, interval=15)
		# print(stock_data)
		# pdb.set_trace()
		try:
			open_high_dict, open_low_dict = sdtools.sd_open_high_low_dicts(stock_list=main_list)
		except Exception as e:
			print(f"❌ Error fetching open high/low data: {e}")
			msg2 = f"❌ Error fetching open high/low data: {e} at {current_time}"
			send_telegram(msg2)
			continue
		break# exit the loop
		# open_high_dict
		# open_low_dict

	else:
		print("You missed the window ⏳ or already scanned !!")
		# open_high_dict, open_low_dict = sdtools.sd_open_high_low_dicts(stock_list=focused_opts)
		# open_high_dict = {}
		# open_low_dict = {}
		break

bullish_trend = None
already_traded = set()
max_trades = 15

# True # 
while True:

	current_time = datetime.datetime.now().time()
	print("starting Conditions Loop ⚒\n")

	# Run every 5 minutes between 12:33 and 15:30
	if datetime.time(9, 31) <= current_time < datetime.time(15, 30):
		if int(datetime.datetime.now().minute) % 5 == 0:
			try:
				nifty_df_15 = sdtools.get_nifty_data(interval=15)
				# nifty_df_15 = dummydata()
				sma21 = SMAIndicator(close=nifty_df_15['close'], window=21)
				nifty_df_15['sma_21'] = sma21.sma_indicator()
				latest_close = nifty_df_15['close'].iloc[-1]
				latest_ma    = nifty_df_15['sma_21'].iloc[-1]
				bullish_trend = latest_ma < latest_close
			except Exception as e:
				print(f"❌ Error fetching Nifty data: {e}")
				msg1 = f"❌ Error fetching Nifty data: {e} at {current_time}"
				send_telegram(msg1)
				continue
			print(f"Nifty's Latest Close: {latest_close}, Latest MA: {latest_ma}, Bullish Trend: {bullish_trend}, at: {current_time}")
			msg1 = (f"Nifty's Latest Close: {latest_close}, Latest MA: {latest_ma}, Bullish Trend: {bullish_trend}, at: {current_time}")
			send_telegram(msg1)
			print("waiting")
			# time.sleep(30)  # Sleep for 30 seconds to avoid duplicate triggers in the same minute
			# Check open_high_dict stocks for break and remove if broken
			stocks_to_remove_high = []
			for stock_name, stock_data in open_high_dict.items():
				stock_id = stock_data["security_id"]
				ohlc_df = sdtools.intra_data(security_id=stock_id, interval=15)
				if ohlc_df.empty:
					continue
				latest_close = ohlc_df['close'].iloc[-1]
				high_price = stock_data['high']
				if latest_close > high_price:
					print(f"⚠️ {stock_name} Open High broken! Latest Close: {latest_close}, High: {high_price}")
					send_telegram(f"{stock_name} Open High broken! Latest Close: {latest_close}, High: {high_price}")
					stocks_to_remove_high.append(stock_name)
			for stock_name in stocks_to_remove_high:
				del open_high_dict[stock_name]

			# Check open_low_dict stocks for break and remove if broken
			stocks_to_remove_low = []
			for stock_name, stock_data in open_low_dict.items():
				stock_id = stock_data["security_id"]
				ohlc_df = sdtools.intra_data(security_id=stock_id, interval=5)
				if ohlc_df.empty:
					continue
				latest_close = ohlc_df['close'].iloc[-1]
				low_price = stock_data['low']
				if latest_close < low_price:
					print(f"⚠️ {stock_name} Open Low broken! Latest Close: {latest_close}, Low: {low_price}")
					send_telegram(f"{stock_name} Open Low broken! Latest Close: {latest_close}, Low: {low_price}")
					stocks_to_remove_low.append(stock_name)
			for stock_name in stocks_to_remove_low:
				del open_low_dict[stock_name]
			time.sleep(30)  
		else:
			time.sleep(1)  # Sleep for 1 seconds before checking again
		
		if bullish_trend == True:
			print("Market is in Bull Mode !! ")
			try:
				for stock_name, stock_data in open_low_dict.items():
					if stock_name in already_traded:
						print(f"⏩ Skipping already traded: {stock_name}")
						continue
					
					stock_id = stock_data["security_id"]
					direction = "CALL"
					Call_entry = sdtools.sd_check_call_entry2(stock_name, stock_id)
					if Call_entry == True:
						print(f"✅ Entry CONFIRMED for {stock_name}")
						already_traded.add(stock_name)

						# PLACE ORDER logic goes here (next phase)
						# order_details = place_order(...)
			except Exception as e:
				print(f"❌ Error during Bull Side CALL entry check: {e}")
				msg2 = f"❌ Error during Bull Side CALL entry check: {e} at {current_time}"
				send_telegram(msg2)
				continue

			if len(already_traded) >= max_trades:
				print("⚠️ Max trades reached, halting scan")
				print(already_traded)
				break
			try:
				for stock_name, stock_data in open_high_dict.items():
					if stock_name in already_traded:
						print(f"⏩ Skipping already traded: {stock_name}")
						continue
					
					stock_id = stock_data["security_id"]
					direction = "PUT"
					Put_entry = sdtools.sd_check_put_entry2(stock_name, stock_id)
					if Put_entry == True:
						print(f"✅ Entry CONFIRMED for {stock_name} [{direction}]")
						already_traded.add(stock_name)

						# PLACE ORDER logic goes here (next phase)
						# order_details = place_order(...)
			except Exception as e:
				print(f"❌ Error during Bull Side PUT entry check: {e}")
				msg2 = f"❌ Error during Bull Side PUT entry check: {e} at {current_time}"
				send_telegram(msg2)
				continue

			if len(already_traded) >= max_trades:
				print("⚠️ Max trades reached, halting scan")
				print(already_traded)
				break

		else:
			print("Market is in Bear Mode !! ")
			try:
				for stock_name, stock_data in open_high_dict.items():
					if stock_name in already_traded:
						print(f"⏩ Skipping already traded: {stock_name}")
						continue
					
					stock_id = stock_data["security_id"]
					direction = "PUT"
					Put_entry = sdtools.sd_check_put_entry2(stock_name, stock_id)
					if Put_entry == True:
						print(f"✅ Entry CONFIRMED for {stock_name} [{direction}] ")
						already_traded.add(stock_name)

						# PLACE ORDER logic goes here (next phase)
						# order_details = place_order(...)
			except Exception as e:
				print(f"❌ Error during Bear Side PUT entry check: {e}")
				msg2 = f"❌ Error during Bear Side PUT entry check: {e} at {current_time}"
				send_telegram(msg2)
				continue

			if len(already_traded) >= max_trades:
				print("⚠️ Max trades reached, halting scan")
				print(already_traded)
				break

			try:
				for stock_name, stock_data in open_low_dict.items():
					if stock_name in already_traded:
						print(f"⏩ Skipping already traded: {stock_name}")
						continue
					
					stock_id = stock_data["security_id"]
					direction = "CALL"
					Call_entry = sdtools.sd_check_call_entry2(stock_name, stock_id)
					if Call_entry == True:
						print(f"✅ Entry CONFIRMED for {stock_name} [{direction}]")
						already_traded.add(stock_name)

						# PLACE ORDER logic goes here (next phase)
						# order_details = place_order(...)
			except Exception as e:
				print(f"❌ Error during Bear Side CALL entry check: {e}")
				msg2 = f"❌ Error during Bear Side CALL entry check: {e} at {current_time}"
				send_telegram(msg2)
				continue

			if len(already_traded) >= max_trades:
				print("⚠️ Max trades reached, halting scan")
				print(already_traded)
				break

	
#  all_stocks = ["360ONE", "AARTIIND", "ABB", "ACC", "ADANIENSOL", "ADANIENT", "ADANIGREEN", "ADANIPORTS", "ATGL", "ABCAPITAL", "ABFRL", "ALKEM", "AMBER", "AMBUJACEM", "ANGELONE", "APLAPOLLO", "APOLLOHOSP", "ASHOKLEY", "ASIANPAINT", "ASTRAL", "AUBANK", "AUROPHARMA", "DMART", "AXISBANK", "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BALKRISIND", "BANDHANBNK", "BANKBARODA", "BANKINDIA", "BDL", "BEL", "BHARATFORG", "BHEL", "BPCL", "BHARTIARTL", "BIOCON", "BSOFT", "BLUESTARCO", "BOSCHLTD", "BRITANNIA", "BSE" "ULTRACEMCO", "UNIONBANK", "UNITDSPR", "UNOMINDA", "UPL", "VBL", "VEDL", "IDEA", "VOLTAS", "WIPRO", "YESBANK", "ZYDUSLIFE", "CANBK", "CDSL", "CESC", "CGPOWER", "CHAMBLFERT", "CHOLAFIN", "CIPLA", "COALINDIA", "COFORGE", "COLPAL", "CAMS", "CONCOR", "CROMPTON", "CUMMINSIND", "CYIENT", "DABUR", "DALBHARAT", "DELHIVERY", "DIVISLAB", "DIXON", "DLF", "DRREDDY", "EICHERMOT", "ETERNAL", "EXIDEIND", "FEDERALBNK", "FINNIFTY", "FORTIS", "GAIL", "GLENMARK", "GMRAIRPORT", "GODREJCP", "GODREJPROP", "GRANULES", "GRASIM", "HAVELLS", "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HFCL", "HINDALCO", "HAL", "HINDCOPPER", "HINDPETRO", "HINDUNILVR", "HINDZINC", "HUDCO", "ICICIBANK", "ICICIGI", "ICICIPRULI", "IDFCFIRSTB", "IIFL", "INDIANB", "IEX", "INDHOTEL", "IOC", "IGL", "INDUSTOWER", "INDUSINDBK", "NAUKRI", "INFY", "INOXWIND", "INDIGO", "IRB", "IRCTC", "IREDA", "IRFC", "ITC", "JSL", "JINDALSTEL", "JIOFIN", "JSWENERGY", "JSWSTEEL", "JUBLFOOD", "KALYANKJIL", "KAYNES", "KEI", "KFINTECH", "KOTAKBANK", "KPITTECH", "LT", "LTF", "LAURUSLABS", "LICHSGFIN", "LICI", "LODHA", "LTIM", "LUPIN", "M&MFIN", "MGL", "M&M", "MANAPPURAM", "MANKIND", "MARICO", "MARUTI", "MFSL", "MAXHEALTH", "MAZDOCK", "MCX", "MPHASIS", "MUTHOOTFIN", "NATIONALUM", "NBCC", "NCC", "NESTLEIND", "NHPC", "NIFTY", "BANKNIFTY", "MIDCPNIFTY", "NIFTY NEXT 50", "NMDC", "NTPC", "NYKAA", "OBEROIRLTY", "ONGC", "OIL", "PAYTM", "OFSS", "PAGEIND", "PATANJALI", "POLICYBZR", "PERSISTENT", "PETRONET", "PGEL", "PHOENIXLTD", "PIIND", "PIDILITIND", "PEL", "PPLPHARMA", "PNBHOUSING", "POLYCAB", "POONAWALLA", "PFC", "POWERGRID", "PRESTIGE", "PNB", "RVNL", "RBLBANK", "RECLTD", "RELIANCE", "MOTHERSON", "SBICARD", "SBILIFE", "SHREECEM", "SHRIRAMFIN", "SIEMENS", "SJVN", "SOLARINDS", "SONACOMS", "SRF", "SBIN", "SAIL", "SUNPHARMA", "SUPREMEIND", "SYNGENE", "TATACHEM", "TATACOMM", "TCS", "TATACONSUM", "TATAELXSI", "TATAMOTORS", "TATAPOWER", "TATASTEEL", "TATATECH", "TECHM", "TITAGARH", "TITAN", "TORNTPHARM", "TORNTPOWER", "TRENT", "TIINDIA", "TVSMOTOR" ]
