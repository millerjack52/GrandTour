from pathlib import Path
script=Path('C:/GrandTour/Art/VehicleTools/glazing_audit_wind_bands.py').read_text()
script=script.replace("sets=[set(row['faces']) for row in d]", "corner=json.loads((O/'windscreen-corner-repair-contract.json').read_text()); sets=[set(d[0]['faces']),set(d[2]['faces']),set(corner['surround_source_faces_to_remove'])|set(corner['pane_source_faces_already_removed'])]")
script=script.replace("wind-bands-", "wind-corner-patch-")
exec(compile(script,'corner bands','exec'))
