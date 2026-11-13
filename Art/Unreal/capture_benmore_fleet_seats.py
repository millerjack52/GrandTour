from pathlib import Path
p=Path('C:/GrandTour/Art/Unreal/capture_benmore_fleet_driving.py')
src=p.read_text()
src=src.replace("(OUT/'visual-report.json')", "(OUT/'seat-visual-report.json')")
old="            phase='view'\n        elif phase=='view':"
new="""            views=[v for v in views if v[0].endswith('_Cockpit')]
            report['saved_eyes']={}
            for v in views:
                a=cars[v[0].removesuffix('_Cockpit')]
                eye=a.get_editor_property('driver_eye_offset')
                assert eye==u.get_default_object(a.get_class()).get_editor_property('driver_eye_offset')
                report['saved_eyes'][v[0]]=list(eye.to_tuple())
            phase='view'
        elif phase=='view':"""
assert old in src
exec(compile(src.replace(old,new),str(p),'exec'))
