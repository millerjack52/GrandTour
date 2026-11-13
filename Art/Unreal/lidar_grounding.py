"""Ground queries against final relief tiles, shared by vegetation and dressing.

No traces against foliage or water, and no cached pre-sculpt elevations.
"""
import math
import unreal as u

class GroundSampler:
 def __init__(self,author):
  self.author=author
  tiles=list(author.relief_tiles.values())
  self.span=tiles[0].span_cm if tiles else 0
  self.origin=tiles[0].get_actor_location() if tiles else u.Vector()
  self.tiles={(round((t.get_actor_location().x-self.origin.x)/self.span),round((t.get_actor_location().y-self.origin.y)/self.span)):t for t in tiles}
 def height(self,x,y):
  t=self.tiles.get((math.floor((x-self.origin.x)/self.span),math.floor((y-self.origin.y)/self.span))) if self.span else None
  return t.height_at(u.Vector2D(x,y)) if t else self.author.base_height_at(u.Vector2D(x,y))
 def seat(self,mesh,tf,plant=False):
  p=tf.translation;sc=tf.scale3d;box=mesh.get_bounding_box();yaw=tf.rotation.rotator().yaw
  angle=math.radians(yaw);dx,dy=math.cos(angle),math.sin(angle)
  z=self.height(p.x,p.y)
  # Keep living crowns upright; slope-align low debris/stone footprints.
  if plant:
   pitch=roll=0;z-=3  # Native living plants have a ground pivot; cards are not root geometry.
  else:
   gx=(self.height(p.x+35,p.y)-self.height(p.x-35,p.y))/70
   gy=(self.height(p.x,p.y+35)-self.height(p.x,p.y-35))/70
   pitch=math.degrees(math.atan(gx*dx+gy*dy));roll=-math.degrees(math.atan(-gx*dy+gy*dx))
   radius=min(250,max(box.max.x-box.min.x,box.max.y-box.min.y)*max(sc.x,sc.y)*.45)
   error=min(self.height(p.x+radius*math.cos(a),p.y+radius*math.sin(a))-z-radius*(gx*math.cos(a)+gy*math.sin(a)) for a in [j*math.pi/4 for j in range(8)])
   z+=min(0,error)-box.min.z*sc.z-4
  return u.Transform(location=u.Vector(p.x,p.y,z),rotation=u.Rotator(pitch=pitch,yaw=yaw,roll=roll),scale=sc)
