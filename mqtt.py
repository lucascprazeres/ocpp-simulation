import paho.mqtt.client as mqtt

class Client:
  def __init__(self, tenant, device_id):
    self.tenant = tenant
    self.device_id = device_id
    self.client = mqtt.Client(f'{tenant}:{device_id}')
    self.client.username_pw_set(f'{self.tenant}:{self.device_id}', None)

  def connect(self, host, port):
    self.client.connect(host, port)
    self.client.loop_start()

  def send(self, message):
    topic = f'{self.tenant}:{self.device_id}/attrs'
    self.client.publish(topic, message)