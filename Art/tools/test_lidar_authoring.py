"""Functional design contracts: independent soil/ruts, reversible beds and digest coverage."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
import lidar_authoring as la


def document(paths):
    return dict(version=1,coordinate_system=la.COORDINATES,paths=paths)


def bed():
    return dict(id='bed',name='Ford',kind='river_bed',enabled=True,points_cm=[[-2000,0,965],[2000,0,965]],width_m=8,bank_blend_m=4,target_depth_m=.35,max_cut_fill_m=2)


def track():
    return dict(id='track',name='Logging trail',kind='mud_track',enabled=True,points_cm=[[0,0,1000],[1000,0,1100]],width_m=2.4,max_cut_fill_m=1,mud_depth_cm=18,rut_depth_cm=0,firmness=.45,wetness=.65,relief_strength=0,conditions=[])


class DesignTests(unittest.TestCase):
    def grid(self):
        x,y=np.meshgrid(np.arange(-30.,31.),np.arange(-20.,21.))
        original=np.where(np.abs(y)<10,9.,10.2)
        water=np.full(x.shape,10.)
        return x,y,original,water

    def test_zero_edits_exact_identity(self):
        x,y,base,water=self.grid();result,mask=la.sculpt_beds(document([]),x,y,base,water,base)
        np.testing.assert_array_equal(result,base);self.assertFalse(mask.any())

    def test_ford_and_unmodified_banks(self):
        x,y,base,water=self.grid();data=la.validate(document([bed()]))
        result,mask=la.sculpt_beds(data,x,y,base,water,base)
        self.assertAlmostEqual(result[20,30],9.65)
        np.testing.assert_array_equal(result[~mask],base[~mask])
        np.testing.assert_array_equal(result[np.abs(y)>=10],base[np.abs(y)>=10])
        again,_=la.sculpt_beds(data,x,y,base,water,base);np.testing.assert_array_equal(result,again)
        reverted,_=la.sculpt_beds(document([]),x,y,base,water,base);np.testing.assert_array_equal(reverted,base)

    def test_deepen_and_limits(self):
        x,y,base,water=self.grid();p=bed();p['points_cm']=[[-2000,0,880],[2000,0,880]]
        result,_=la.sculpt_beds(document([p]),x,y,base,water,base);self.assertAlmostEqual(result[20,30],8.8)
        p['points_cm']=[[-2000,0,1100],[2000,0,1100]]
        with self.assertRaises(ValueError):la.sculpt_beds(document([p]),x,y,base,water,base)

    def test_overlap_rejected(self):
        x,y,base,water=self.grid();other=copy.deepcopy(bed());other['id']='second';other['name']='Other'
        with self.assertRaisesRegex(ValueError,'overlap'):la.sculpt_beds(document([bed(),other]),x,y,base,water,base)

    def test_disabled_bed_does_not_apply(self):
        x,y,base,water=self.grid();p=bed();p['enabled']=False
        result,mask=la.sculpt_beds(document([p]),x,y,base,water,base);np.testing.assert_array_equal(result,base)

    def test_mud_depth_is_not_authored_rut(self):
        row=la.road_records(la.validate(document([track()])))[0]
        self.assertEqual(row['surface'],'mud');self.assertEqual(row['authoring']['rut_depth_cm'],0)
        self.assertEqual(row['authoring']['mud_depth_cm'],18);self.assertEqual(row['points'][-1],[1000,0])
        self.assertEqual(row['elevations_cm'][-1],1100);self.assertAlmostEqual(row['length_m'],101**.5)

    def test_invalid_geometry_and_duplicate_ids(self):
        for value in (float('nan'),float('inf'),True):
            p=track();p['points_cm'][1][0]=value
            with self.assertRaises(ValueError):la.validate(document([p]))
        with self.assertRaises(ValueError):la.validate(document([track(),track()]))

    def test_bog_pool_independent_of_ruts_and_depth_limits(self):
        p=track();c=dict(name='Bog',start_metres=1.,end_metres=9.,blend_metres=2.,mud_depth_cm=55.,rut_depth_cm=0.,wetness=.95,firmness=.2,grass_cover=0.,water_fill_cm=25.,basin_depth_cm=60.,track_spread_cm=0.,churn=0.,crossing_tracks=0.,breakup_cm=0.)
        p['conditions']=[c];la.validate(document([p]))
        self.assertEqual(la.road_records(document([p]))[0]['authoring']['conditions'][0]['rut_depth_cm'],0)
        for key,value in [('basin_depth_cm',101.),('water_fill_cm',41.),('basin_depth_cm',float('nan'))]:
            bad=copy.deepcopy(p);bad['conditions'][0][key]=value
            with self.assertRaises(ValueError):la.validate(document([bad]))

    def test_narrow_track_does_not_clear_wide_verges(self):
        x=np.full(5,5.);y=np.array([0.,1.2,1.5,1.8,3.])
        mask=la.track_mask(document([track()]),x,y,np.zeros(5))
        self.assertEqual(mask[0],1);self.assertEqual(mask[1],1)
        self.assertAlmostEqual(mask[2],.5);self.assertEqual(mask[3],0);self.assertEqual(mask[4],0)

    def test_water_and_terrain_alone_invalidate_install(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);(p/'roads.json').write_text('[]');before=la.inputs_digest(p)
            for name in ['River-domain.bin','River.obj','River-flow.png','River-shore.png','authoring-height.r16','logging_trial.json']:
                (p/name).write_bytes(b'new');after=la.inputs_digest(p);self.assertNotEqual(before,after);before=after

    def test_variable_width_survives_resampling_and_clearing(self):
        p=track();p['widths_m']=[2.,4.]
        row=la.road_records(la.validate(document([p])))[0]
        self.assertEqual(row['widths_cm'],[200.,300.,400.])
        mask=la.track_mask(document([p]),np.array([0.,10.]),np.array([1.9,1.9]),np.zeros(2))
        np.testing.assert_array_equal(mask,[0.,1.])
        for widths in ([2.], [2.,float('nan')], [2.,21.]):
            p['widths_m']=widths
            with self.assertRaises(ValueError):la.validate(document([p]))


if __name__=='__main__':unittest.main()
