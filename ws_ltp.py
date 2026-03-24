from tools import Tools
from dhanhq import marketfeed
import os
from dotenv import load_dotenv
import time
import requests
import json
import pdb
import datetime
from datetime import time as dt_time
from datetime import datetime, timedelta

load_dotenv()
client_id = os.getenv("DHAN_CLIENT_ID")
access_token = os.getenv("DHAN_ACCESS_TOKEN")

tools = Tools()

LTP_JSON_PATH = "data/live_feed.json"
STOCK_FEED_PATH = "data/stock_feed.json"

def run_stock_ohlc_socket(security_ids, duration_seconds=3600):
    version = "v2"
    instruments = [(marketfeed.NSE_EQUITY, str(sec_id), marketfeed.Ticker) for sec_id in security_ids]
    print(f"🛰️ Subscribing to {len(instruments)} stocks for OHLC tracking")

    try:
        socket = marketfeed.DhanFeed(client_id, access_token, instruments, version)

        ohlc_data = {}

        start_time = time.time()

        while time.time() - start_time < duration_seconds:
            socket.run_forever()

            tick = socket.get_data()

            if tick.get("type") != "Ticker Data":
                continue

            sec_id = tick.get("security_id")
            ltp = float(tick.get("last_traded_price", 0.0))

            if not sec_id or ltp == 0.0:
                continue

            current_time = datetime.now().time()

            # Initialize OHLC for the security
            if sec_id not in ohlc_data:
                ohlc_data[sec_id] = {
                    "open": ltp,
                    "high": ltp,
                    "low": ltp,
                    "close": ltp,
                    "last_updated": str(current_time)
                }
            else:
                ohlc_data[sec_id]["high"] = max(ohlc_data[sec_id]["high"], ltp)
                ohlc_data[sec_id]["low"] = min(ohlc_data[sec_id]["low"], ltp)
                ohlc_data[sec_id]["close"] = ltp
                ohlc_data[sec_id]["last_updated"] = str(current_time)

            # Save to JSON every second
            with open(STOCK_FEED_PATH, "w") as f:
                json.dump(ohlc_data, f, indent=2)

            print(f"📈 Updated {sec_id}: {ohlc_data[sec_id]}")

        socket.disconnect()
        print(f"✅ Stock OHLC WebSocket closed after {duration_seconds}s")

    except Exception as e:
        print("❌ WebSocket error:", e)

def run_ltp_socket(security_ids, duration_seconds=60):
    version = "v2"
    instruments = [(marketfeed.NSE_FNO, str(sec_id), marketfeed.Ticker) for sec_id in security_ids]
    instruments.append((marketfeed.IDX, "13", marketfeed.Ticker))
    
    try:
        socket = marketfeed.DhanFeed(client_id, access_token, instruments, version)

        start_time = time.time()
        already_cleared_today = False  # Track if reset is done for the day

        while time.time() - start_time < duration_seconds:
            socket.run_forever()
            
            tick = socket.get_data()
            print("success", tick)

            now = datetime.now()
            if not already_cleared_today and now.hour == 14 and now.minute >= 45:
                print("🧹 Clearing live_feed.json at 9:30 AM...")
                with open(LTP_JSON_PATH, "w") as f:
                    json.dump({}, f)
                already_cleared_today = True  # Don't clear again today

            # Save latest LTP data into live_feed.json
            try:
                if os.path.exists(LTP_JSON_PATH) and os.path.getsize(LTP_JSON_PATH) > 0:
                    with open(LTP_JSON_PATH, "r") as f:
                        current_data = json.load(f)
                else:
                    current_data = {}
            except (json.JSONDecodeError, FileNotFoundError):
                current_data = {}
            # pdb.set_trace()
            # Unique key per instrument (e.g. by security_id)
            # Save only "Ticker Data" (live LTPs)
            if tick.get("type") == "Ticker Data":
                sec_id = tick.get("security_id")
                if sec_id:
                    current_data[str(sec_id)] = tick
                    with open(LTP_JSON_PATH, "w") as f:
                        json.dump(current_data, f, indent=2)
                    print("📈 Saved tick:", tick)
            else:
                print("⏩ Ignored non-LTP tick:", tick.get("type"))

        socket.disconnect()
        print(f"✅ WebSocket closed after {duration_seconds} seconds.")

    except Exception as e:
        print("❌ WebSocket error:", e)

if __name__ == "__main__":
    from tools import Tools
    print("running")
    tools = Tools()
    security_ids = tools.get_security_id(tools.get_instrument_file())
    run_stock_ohlc_socket(security_ids, duration_seconds=19800)  # ~5.5 hrs


# ce_pe_data = tools.get_ce_pe()
# print(ce_pe_data)

# security_id_ce  = ce_pe_data['ce']['security_id']
# security_id_pe  = ce_pe_data['pe']['security_id']

# run_ltp_socket([security_id_ce, security_id_pe], 6000)     
'''
ABB	13	1755853200	5073	5077.5	5070.5	5070.5	2831	2025-08-22 14:30:00+05:30	5081.858244	5088.752339	5085.111111	5089.642857	19.92029876	7.902714019	33.90985085	31.24395053	FALSE	TRUE
DIVISLAB	10940	1755841500	6142	6142	6133.5	6139.5	12801	2025-08-22 11:15:00+05:30	6146.075434	6148.184944	6147.222222	6148.547619	40.19199359	8.927813845	18.30435157	26.80052256	FALSE	TRUE
DIVISLAB	10940	1755848700	6126.5	6126.5	6122.5	6125	4301	2025-08-22 13:15:00+05:30	6129.231526	6134.609814	6129.166667	6136.452381	32.22014416	5.348898672	32.38815152	39.2222539	FALSE	TRUE
GRASIM	1232	1755853800	2815	2815	2813	2813.2	4883	2025-08-22 14:40:00+05:30	2817.251967	2819.278761	2818.233333	2819.542857	25.13764153	11.66052956	24.02097105	28.7661885	FALSE	TRUE
TATAELXSI	3411	1755853200	5565	5565	5555.5	5560.5	2715	2025-08-22 14:30:00+05:30	5567.725259	5570.945697	5569.222222	5571.47619	28.0584793	11.72419516	33.99389954	23.76740494	FALSE	TRUE
OFSS	10738	1755853200	8647	8647	8618	8623	1601	2025-08-22 14:30:00+05:30	8656.945493	8659.961602	8663.611111	8659.166667	22.35404498	10.26306661	38.03474567	32.28509176	FALSE	TRUE



'''