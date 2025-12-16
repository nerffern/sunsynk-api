#!/usr/bin/env python3
"""
Sunsynk Cloud – Plant Summary + Inverter Live Power Flow
Region-safe (SA / EU backends)
"""

import time
import json
import base64
import hashlib
import requests
import os
from dotenv import load_dotenv
load_dotenv()
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5


class SunsynkAPI:
    BASE_URL = "https://api.sunsynk.net"
    CLIENT_ID = "csp-web"
    SOURCE = "sunsynk"

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.token = None

        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
            "Origin": "https://sunsynk.net",
            "Referer": "https://sunsynk.net",
        })

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
        print("→ Logging in to Sunsynk Cloud...")
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
            print("✓ Login successful\n")
            return True

        print("✗ Login failed:", data)
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


# ============================================================
# MAIN
# ============================================================
def main():
    USERNAME = os.getenv('SUNSYNK_USERNAME')
    PASSWORD = os.getenv('SUNSYNK_PASSWORD')
    INVERTER_SN = os.getenv('SUNSYNK_INVERTER_SN')

    if not USERNAME or not PASSWORD or not INVERTER_SN:
        raise RuntimeError(
            "Missing env vars: SUNSYNK_USERNAME, SUNSYNK_PASSWORD, SUNSYNK_INVERTER_SN"
        )

    api = SunsynkAPI(USERNAME, PASSWORD)

    if not api.login():
        return

    plant = api.get_plants()[0]
    plant_id = plant["id"]

    print(f"✓ Using plant: {plant['name']} (ID {plant_id})\n")

    summary = api.get_plant_summary(plant_id)
    flow = api.get_inverter_flow(INVERTER_SN)

    print("========== PLANT SUMMARY ==========")
    print(json.dumps(summary, indent=2))

    print("\n========== LIVE POWER FLOW ==========")
    print(json.dumps(flow, indent=2))

    # ----- POWER CALCULATIONS -----
    pv_list = flow.get("pv", [])
    pv_total = sum(p.get("power", 0) for p in pv_list)

    battery_power = flow.get("battPower")
    grid_power = flow.get("gridOrMeterPower")
    load_power = flow.get("loadOrEpsPower")
    soc = flow.get("soc")

    print("\n========== QUICK SUMMARY ==========")
    print(f"PV Power        : {pv_total} W")
    print(f"Load Power      : {load_power} W")
    print(f"Grid Power      : {grid_power} W")
    print(f"Battery Power   : {battery_power} W")
    print(f"Battery SOC     : {soc} %")
    print(f"Inverter AC Out : {summary.get('pac')} W")
    print(f"Energy Today    : {summary.get('etoday')} kWh")
    print(f"Total Energy    : {summary.get('etotal')} kWh")
    print(f"Income          : {summary.get('currency', {}).get('text')} {summary.get('income')}")
    print(f"Last Update     : {summary.get('updateAt')}")


if __name__ == "__main__":
    main()
