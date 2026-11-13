"""Canonical L_MudVariants rebuild; the legacy four-patch implementation is retained in Git history."""
import sys
from pathlib import Path
import unreal as u
sys.path.insert(0,str(Path(u.Paths.project_dir()).resolve()/'Art/Unreal'))
import rebuild_mud_variants_response
