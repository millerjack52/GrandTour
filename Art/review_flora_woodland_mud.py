"""Unmodified native before/after captures for the mud pigment adjustment."""
import json
from pathlib import Path
import review_flora_woodland as review
O=Path('D:/GrandTourAssets/ReviewEvidence/FloraTrail/WoodlandMud')
if __name__=='__main__':
    assert json.loads((O/'candidate-report.json').read_text())['ok']
    review.O=O
    review.panel([(label+' / '+view,O/f'candidate_{case}_{view}.png')
                  for view in ('drive','bank','close','distance')
                  for case,label in [('before','Before'),('brown','Browner mud')]],'before-after.jpg')
    review.panel([('Before',O/'candidate_before_drive.png'),('Browner mud',O/'candidate_brown_drive.png')],'road-comparison.jpg')
