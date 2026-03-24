# mock_engine.py - Alpha Advanced Version
import os
import json
import datetime
import pdb

class MockEngine:
	def __init__(self):
		self.positions_path = "data/positions.json"
		self.tradebook_path = "data/tradebook.json"
		self.order_state_path = "data/order_state.json"

		self.positions = self._load_json(self.positions_path, [])
		self.trades = self._load_json(self.tradebook_path, [])
		self.order_state = self._load_json(self.order_state_path, {})

		self.settings = {
			"capital": 100000.0,
			"stoploss_percent": 10,
			"target_percent": 15
		}

	def _load_json(self, path, default):
		if not os.path.exists(path):
			return default
		try:
			with open(path, "r") as f:
				return json.load(f)
		except:
			return default

	def _safe_save_json(self, path, data):
		with open(path, "w") as f:
			json.dump(data, f, indent=2)

	def _calculate_required_margin(self, entry_price, qty):
		return round(entry_price * qty, 2)

	def place_order(self, order):
		required_margin = self._calculate_required_margin(order['entry_price'], order['qty'])
		if self.settings['capital'] < required_margin:
			print("\n❌ Not enough capital.")
			return False

		position = {
			"symbol": order['options_name'],
			"buy_sell": order['buy_sell'],
			"entry_price": order['entry_price'],
			"qty": order['qty'],
			"entry_time": str(datetime.datetime.now()),
			"ltp": order['entry_price'],
			"security_id": order.get("security_id", None),
			"pnl": 0.0
		}

		self.positions.append(position)
		self.settings['capital'] -= required_margin
		print("✅ Order placed.")

		# Save state
		self._safe_save_json(self.positions_path, self.positions)
		self._safe_save_json(self.positions_path, self.positions)
		return True

	def update_all_ltps(self):
		if not self.positions:
			return

		try:
			with open("data/live_feed.json", "r") as f:
				live_data = json.load(f)
				print()
			for pos in self.positions:
				sec_id = str(pos["security_id"])
				if sec_id in live_data and "LTP" in live_data[sec_id]:
					pos["ltp"] = float(live_data[sec_id]["LTP"])
					pos["pnl"] = round((pos["ltp"] - pos["entry_price"]) * pos["qty"], 2)
			
					print("Updated LTP")
			self._safe_save_json(self.positions_path, self.positions)
		except Exception as e:
			print("❌ Error updating LTPs:", e)

	def check_and_close_positions(self):
		to_close = []
		for pos in self.positions:
			pnl_percent = ((pos['ltp'] - pos['entry_price']) / pos['entry_price']) * 100
			print(pnl_percent)
			if pnl_percent >= self.settings['target_percent'] :
				to_close.append(pos)
				self.close_position(pos, reason="TGT Hit")
				print("Position closed TGT")
			elif pnl_percent <= -self.settings['stoploss_percent']:
				to_close.append(pos)
				self.close_position(pos, reason="SL Hit")
				print("Position closed SL")
			# pdb.set_trace()
		# for pos in to_close:
		# 	self.close_position(pos, reason="SL/TGT Hit")

	def close_position(self, pos, reason="Closed"):
		pos["exit_price"] = pos["ltp"]
		pos["exit_time"] = str(datetime.datetime.now())
		pos["status"] = reason

		self.trades.append(pos)
		self.settings['capital'] += pos["ltp"] * pos["qty"]

		if pos in self.positions:
			self.positions.remove(pos)

		# Save files
		self._safe_save_json(self.positions_path, self.positions)
		self._safe_save_json(self.tradebook_path, self.trades)
		self._safe_save_json(self.order_state_path, self.positions)
		print(f"🔴 Closed trade: {pos['symbol']} at {pos['ltp']:.2f} due to {reason}")
