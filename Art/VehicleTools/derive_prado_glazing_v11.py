from pathlib import Path
p=Path('C:/GrandTour/Art/VehicleTools/repair_prado_glazing_lamps_v10.py')
s=p.read_text().replace('prado-glazing-v10','prado-glazing-v11')
s=s.replace('from prado_lamp_repair_module import repair_rear_lamps','from prado_lamp_repair_module import repair_rear_lamps\nfrom prado_wiper_repair import repair_wipers')
s=s.replace("'windscreen-repair-contract.json'","'windscreen-corner-repair-contract.json'")
s=s.replace("report['rear_lamps']=repair_rear_lamps()","report['rear_lamps']=repair_rear_lamps()\nreport['wipers']=repair_wipers(json.loads((audit/'windscreen-corner-repair-contract.json').read_text()))")
Path('C:/GrandTour/Art/VehicleTools/repair_prado_glazing_lamps_v11.py').write_text(s)
