import asyncio
import os

from dojot import Dojot
from dotenv import load_dotenv
from charge_point import ChargePoint

load_dotenv()

DOJOT_HOST = os.getenv('DOJOT_HOST')
MQTT_PORT = int(os.getenv('MQTT_PORT'))
HTTP_PORT = int(os.getenv('HTTP_PORT'))

DOJOT_USERNAME = os.getenv('DOJOT_USERNAME')
DOJOT_PASSWORD = os.getenv('DOJOT_PASSWORD')

dojot = Dojot(
    ip=DOJOT_HOST,
    http_port=HTTP_PORT,
    mqtt_port=MQTT_PORT,
    user=DOJOT_USERNAME,
    password=DOJOT_PASSWORD
)

dojot.create_all_devices()