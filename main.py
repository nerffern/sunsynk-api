#!/usr/bin/env python3
"""
Sunsynk Cloud – Plant Summary + Inverter Live Power Flow
Region-safe (SA / EU backends)
"""

import base64
import hashlib
import os
import time
from typing import Any, Dict, Optional

import requests
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template

load_dotenv()


class SunsynkAPI:
    BASE_URL = "https://api.sunsynk.net"
    CLIENT_ID = "csp-web"
    SOURCE = "sunsynk"

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.token: Optional[str] = None

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0",
                "Origin": "https://sunsynk.net",
                "Referer": "https://sunsynk.net",
            }
        )

    # -------------------------
    # Helpers
    # -------------------------
    @staticmethod
    def _md5(s):
        return hashlib.md5(s.encode()).hexdigest()

    @staticmethod
    def _nonce():
        return int(time.time() * 1000)

    # -------------------------
    # Auth
    # -------------------------
    def get_public_key(self):
        nonce = self._nonce()
        sign = self._md5(f"{nonce}{self.SOURCE}")

        r = self.session.get(
            f"{self.BASE_URL}/anonymous/publicKey",
            params={"nonce": nonce, "source": self.SOURCE, "sign": sign},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()["data"]

    def encrypt_password(self, rsa_b64):
        key = RSA.import_key(base64.b64decode(rsa_b64))
        cipher = PKCS1_v1_5.new(key)
        return base64.b64encode(cipher.encrypt(self.password.encode())).decode()

    def login(self):
        rsa = self.get_public_key()
        enc_pw = self.encrypt_password(rsa)
        nonce = self._nonce()
        sign = self._md5(f"nonce={nonce}&source={self.SOURCE}{rsa[:10]}")

        payload = {
            "username": self.username,
            "password": enc_pw,
            "grant_type": "password",
            "client_id": self.CLIENT_ID,
            "source": self.SOURCE,
            "nonce": nonce,
            "sign": sign,
        }

        r = self.session.post(
            f"{self.BASE_URL}/oauth/token/new",
            json=payload,
            timeout=10,
        )
        data = r.json()

        if data.get("success"):
            self.token = data["data"]["access_token"]
            return True

        return False

    # -------------------------
    # API wrapper
    # -------------------------
    def _get(self, endpoint):
        r = self.session.get(
            f"{self.BASE_URL}/api/{endpoint}",
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=10,
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json().get("data")

    # -------------------------
    # Endpoints
    # -------------------------
    def get_plants(self):
        return self._get("v1/plants?page=1&limit=10")["infos"]

    def get_plant_summary(self, plant_id):
        return self._get(f"v1/plant/{plant_id}/realtime")

    def get_inverter_flow(self, sn):
        return self._get(f"v1/inverter/{sn}/flow")


FETCH_INTERVAL_SECONDS = 60

# Optional cost assumptions (per kWh)
GRID_IMPORT_RATE = float(os.getenv("GRID_IMPORT_RATE", "4"))
GRID_EXPORT_RATE = float(os.getenv("GRID_EXPORT_RATE", str(GRID_IMPORT_RATE)))

USERNAME = os.getenv("SUNSYNK_USERNAME")
PASSWORD = os.getenv("SUNSYNK_PASSWORD")
INVERTER_SN = os.getenv("SUNSYNK_INVERTER_SN")

app = Flask(__name__)
api_client: Optional[SunsynkAPI] = None
_cache: Dict[str, Any] = {"data": None, "timestamp": 0, "plant_id": None, "plant_name": None}


def _ensure_credentials():
    missing = [
        name
        for name, value in [
            ("SUNSYNK_USERNAME", USERNAME),
            ("SUNSYNK_PASSWORD", PASSWORD),
            ("SUNSYNK_INVERTER_SN", INVERTER_SN),
        ]
        if not value
    ]
    if missing:
        raise RuntimeError(
            f"Missing env vars: {', '.join(missing)}. Set them before starting the dashboard."
        )


def _get_client() -> SunsynkAPI:
    global api_client
    if api_client is None:
        _ensure_credentials()
        api_client = SunsynkAPI(USERNAME, PASSWORD)
    if not api_client.token:
        logged_in = api_client.login()
        if not logged_in:
            raise RuntimeError("Unable to login to Sunsynk Cloud with the provided credentials.")
    return api_client


def _first_value(payload: Dict[str, Any], keys, default=0):
    for key in keys:
        if key in payload and payload.get(key) is not None:
            return payload.get(key)
    return default


def _power_direction(value: Optional[float], positive_label: str, negative_label: str):
    if value is None:
        return "Idle"
    if value > 0:
        return positive_label
    if value < 0:
        return negative_label
    return "Idle"


def _build_payload(summary: Dict[str, Any], flow: Dict[str, Any]) -> Dict[str, Any]:
    pv_list = flow.get("pv", [])
    pv_total = sum(p.get("power", 0) for p in pv_list)

    battery_power = flow.get("battPower")
    grid_power = flow.get("gridOrMeterPower")
    load_power = flow.get("loadOrEpsPower")

    currency = summary.get("currency", {}).get("text", "R")

    grid_import_today = _first_value(
        summary,
        [
            "buyToday",
            "gridBuyToday",
            "importEnergyToday",
            "gridImportToday",
        ],
        0,
    )
    grid_export_today = _first_value(
        summary,
        ["sellToday", "feedInEnergyToday", "exportEnergyToday", "gridSellToday"],
        0,
    )

    grid_import_value = _first_value(
        summary, ["buyIncome", "gridCostToday", "importCostToday"], 0
    )
    grid_export_value = _first_value(
        summary, ["sellIncome", "feedInIncomeToday", "exportIncomeToday"], 0
    )

    # Compute fallback values if the API does not provide money totals
    if not grid_import_value and grid_import_today is not None:
        grid_import_value = round(grid_import_today * GRID_IMPORT_RATE, 2)

    if not grid_export_value and grid_export_today is not None:
        grid_export_value = round(grid_export_today * GRID_EXPORT_RATE, 2)

    data = {
        "plant_name": _cache.get("plant_name", "Plant"),
        "pv_watts": pv_total,
        "battery_watts": battery_power,
        "battery_direction": _power_direction(
            battery_power, "Discharging", "Charging"
        ),
        "grid_watts": grid_power,
        "grid_direction": _power_direction(grid_power, "Importing", "Exporting"),
        "load_watts": load_power,
        "soc": flow.get("soc"),
        "etoday": summary.get("etoday"),
        "etotal": summary.get("etotal"),
        "currency": currency,
        "income_today": _first_value(summary, ["incomeToday", "income"], 0),
        "grid_import_today": grid_import_today,
        "grid_export_today": grid_export_today,
        "grid_import_value": grid_import_value,
        "grid_export_value": grid_export_value,
        "grid_import_rate": GRID_IMPORT_RATE,
        "grid_export_rate": GRID_EXPORT_RATE,
        "last_updated": summary.get("updateAt") or flow.get("updateAt"),
    }
    return data


def fetch_latest_data(force: bool = False) -> Dict[str, Any]:
    now = time.time()
    if (
        _cache.get("data")
        and not force
        and now - _cache.get("timestamp", 0) < FETCH_INTERVAL_SECONDS
    ):
        return _cache["data"]

    client = _get_client()

    if _cache.get("plant_id") is None:
        plants = client.get_plants()
        if not plants:
            raise RuntimeError("No plants were returned for this account.")
        _cache["plant_id"] = plants[0]["id"]
        _cache["plant_name"] = plants[0].get("name", "Sunsynk")

    summary = client.get_plant_summary(_cache["plant_id"])
    flow = client.get_inverter_flow(INVERTER_SN)

    if not summary or not flow:
        raise RuntimeError("Unable to retrieve realtime data from Sunsynk.")

    payload = _build_payload(summary, flow)
    _cache.update({"data": payload, "timestamp": now})
    return payload


@app.route("/")
def index():
    return render_template("index.html", refresh_interval=FETCH_INTERVAL_SECONDS)


@app.route("/api/status")
def status():
    try:
        payload = fetch_latest_data()
        return jsonify({"success": True, "data": payload, "refreshInterval": FETCH_INTERVAL_SECONDS})
    except Exception as exc:  # pragma: no cover - defensive server response
        return jsonify({"success": False, "error": str(exc)}), 500


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(
        host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=os.getenv("FLASK_DEBUG") == "1"
    )
