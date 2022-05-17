import json

devices = []

for i in range(160):
    devices.append({ "name": f'eletroposto_simulado_{i}' })

data = { "eletroposto_simulado": devices }

with open('devices.json', 'w') as outfile:
    json.dump(data, outfile)