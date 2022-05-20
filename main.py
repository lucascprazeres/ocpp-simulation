import asyncio
import os
from datetime import datetime
import json
import logging

from dojot import Dojot
from dotenv import load_dotenv
from charge_point import ChargePoint

load_dotenv()

logging.basicConfig(level=logging.INFO)

DOJOT_HOST = os.getenv('DOJOT_HOST')
MQTT_PORT = int(os.getenv('MQTT_PORT'))
HTTP_PORT = int(os.getenv('HTTP_PORT'))

DOJOT_USERNAME = os.getenv('DOJOT_USERNAME')
DOJOT_PASSWORD = os.getenv('DOJOT_PASSWORD')

async def run_scenario(devices):
    chargers = [ChargePoint(id=label, device=device_id, host=DOJOT_HOST, port=MQTT_PORT) for label, device_id in devices.items()]

    tasks = [cp.run() for cp in chargers]

    await asyncio.gather(*tasks)

async def run_scenarios(devices):
    scenarios = [10,20,40,80,160]
    checkpoints = {
        "start": datetime.utcnow.isoformat()
    }

    for num_chargers in scenarios:
        splitted_devices = dict(list(devices.items())[:num_chargers])
        await run_scenario(splitted_devices)

    checkpoints["end"] = datetime.utcnow.isoformat()

    with open('simulation_checkpoints.json', 'w') as json_file:
        json.dump(checkpoints, json_file)



async def main():
    dojot = Dojot(
        ip=DOJOT_HOST,
        http_port=HTTP_PORT,
        mqtt_port=MQTT_PORT,
        user=DOJOT_USERNAME,
        password=DOJOT_PASSWORD
    )

    devices = dojot.get_all_devices_id(template_id=5)

    await run_scenarios(devices)



if __name__ == '__main__':
    asyncio.run(main())

