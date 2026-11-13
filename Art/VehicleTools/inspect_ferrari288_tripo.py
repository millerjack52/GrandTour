"""Freeze and inspect the supplied Ferrari GLB; no body reconstruction."""
from pathlib import Path
src=Path('C:/GrandTour/Art/VehicleTools/inspect_prado_tripo.py').read_text()
src=src.replace('pradotripo.glb','288gtotripo.glb').replace('prado-source-v01','ferrari288-source-v01').replace('Prado','Ferrari288')
exec(compile(src,'inspect_ferrari288_source','exec'))
