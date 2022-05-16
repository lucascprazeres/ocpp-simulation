import asyncio
import json
import logging
import datetime
import os

from random import randint
from mqtt import Client
from dotenv import load_dotenv

load_dotenv()

DOJOT_HOST = os.getenv('DOJOT_HOST')
MQTT_PORT = int(os.getenv('MQTT_PORT'))

class ChargePoint:

    num_charge_sessions = 3
    sample_interval_seconds = 1
    charging_seconds = 10 * 60 # 10 minutes
    
    def __init__(self, id, device, host, port):
        self.id = id
        self.is_charging = False
        self.mqtt_client = Client('admin', device)

    async def run(self):
        await self.mqtt_client.connect(DOJOT_HOST, MQTT_PORT)
        
        for _ in range(self.num_charge_sessions):
            await self.charge()

        await self.mqtt_client.disconnect()



    async def send_authorize(self):
        msg = json.dumps({
            "authorize": [
                2,
                "abcdefg",
                "Authorize",
                { "idTag": self.id }
            ]
        })

        logging.info(f'{self.id}:{msg}')

        self.mqtt_client.send(msg)


    async def send_meter_values(self):
        while self.is_charging:
            msg = json.dumps({
                "meter_values": [
                    2,
                    "2961:137639",
                    "MeterValues",
                    {
                        "connectorId": 1,
                        "meterValue": [
                            {
                                "sampledValue": [
                                    {
                                        "unit": "Percent",
                                        "context": "Transaction.Begin",
                                        "measurand": "SoC",
                                        "location": "EV",
                                        "value": randint(0,100)
                                    }
                                ]
                            }
                        ]
                    }
                ]
            })
            
            self.mqtt_client.send(msg)

            await asyncio.sleep(self.sample_interval_seconds)            

    async def send_start_transaction(self):
        self.is_charging = True

        msg = json.dumps({
            "start_transaction": [
                2,
                "2961:137638",
                "StartTransaction",
                {
                    "connectorId": 1,
                    "idTag": self.id,
                    "meterStart": 2656119,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
            ]
        })

        logging.info(f'{self.id}:{msg}')

        self.mqtt_client.send(msg)


        await self.send_meter_values()

    async def send_stop_transaction(self):
        await asyncio.sleep(self.charging_seconds)

        self.is_charging = False

        self.mqtt_client.send(json.dumps({
            "stop_transaction": [
                2,
                "2961:137794",
                "StopTransaction",
                {
                    "reason": "Other",
                    "transactionId": 0,
                    "meterStop": 2810542,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
            ]
        }))

        logging.info(f'{self.id}:{msg}')

    async def charge(self):
        await asyncio.gather(
            self.send_authorize(),
            self.send_start_transaction(),
            self.send_stop_transaction()
        )