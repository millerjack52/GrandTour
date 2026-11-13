"""Offline regression checks for evidence handling; never launches Unreal."""
import csv
import tempfile
import unittest
from pathlib import Path
from benmore_profile_metrics import analyse,compare_isolation


class MetricsTests(unittest.TestCase):
    header = ['EVENTS', 'FrameTime', 'GPUTime', 'GameThreadTime',
              'GTWater/ActiveCells', 'GPUMem/LocalBudgetMB', 'GPUMem/LocalUsedMB']

    def capture(self, rows, header=None, footer=True):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / 'capture.csv'
        with path.open('w', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(header or self.header)
            writer.writerows(rows)
            if footer:
                writer.writerow(header or self.header)
                writer.writerow(['[HasHeaderRowAtEnd]', '1'])
        return path

    def test_event_frames_and_footer_not_lost(self):
        rows = [['crossing', 20, 18, 5, 9216, 5000, 4000] for _ in range(99)]
        rows.append(['', 120, 110, 5, 9216, 1800, 4600])
        result = analyse(self.capture(rows))
        self.assertEqual(result['frames'], 100)
        self.assertEqual(result['metrics']['GTWater/ActiveCells']['median'], 9216)
        self.assertEqual(result['metrics']['FrameTime']['p99'], 20)
        self.assertEqual(result['metrics']['FrameTime']['max'], 120)
        self.assertEqual(result['frame_hitches']['100']['count'], 1)
        self.assertEqual(result['local_memory']['over_budget_frames'], 1)
        self.assertEqual(result['local_memory']['minimum_headroom_mb'], -2800)

    def test_headroom_pairs_each_frames_budget(self):
        rows = [['', 20, 18, 5, 9216, 5000, 4000], ['', 20, 18, 5, 9216, 2000, 1900]]
        result = analyse(self.capture(rows), minimum_frames=2)
        self.assertEqual(result['local_memory']['minimum_headroom_mb'], 100)
        self.assertEqual(result['local_memory']['below_proposed_headroom_frames'], 1)

    def test_incomplete_capture_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            analyse(self.capture([['', 20, 18]], footer=False), minimum_frames=1)

    def test_nonfinite_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Non-finite'):
            analyse(self.capture([['', 'nan', 18, 5, 9216, 5000, 4000]]), minimum_frames=1)

    def test_missing_gpu_rejected(self):
        with self.assertRaisesRegex(ValueError, 'GPUTime'):
            analyse(self.capture([['', 20]], header=['EVENTS', 'FrameTime']), minimum_frames=1)

    def test_missing_cpu_warned(self):
        result = analyse(self.capture([['', 20, 18, 5, 9216, 5000, 4000]]), minimum_frames=1)
        self.assertTrue(any('RenderThreadTime' in warning for warning in result['warnings']))

    def test_counter_added_during_capture(self):
        row = ['', 20, 18, 5, 9216, 5000, 4000]
        path = self.capture([row, row + [42]], footer=False)
        with path.open('a', newline='') as stream:
            csv.writer(stream).writerow(self.header + ['NewCounter'])
            csv.writer(stream).writerow(['[HasHeaderRowAtEnd]', '1'])
        result = analyse(path, minimum_frames=2)
        self.assertEqual(result['frames'], 2)
        self.assertEqual(result['metrics']['NewCounter']['samples'], 1)
        self.assertEqual(result['metrics']['NewCounter']['median'], 42)

    def comparison(self, values):
        return [{'view':'Ford','feature':'composition_shrubs','disabled':off,
                 'analysis':{'metrics':{key:{stat:value for stat in ['median','p95','p99']}
                     for key in ['FrameTime','GPUTime']},'local_memory':{'over_budget_frames':0}}}
                for off,value in zip([False,True,True,False],values)]

    def test_abba_drift_prevents_false_win(self):
        result=compare_isolation(self.comparison([40,30,30,25]))[0]
        timing=result['timings']['GPUTime']['median']
        self.assertEqual(timing['saved_ms'],2.5)
        self.assertFalse(timing['exceeds_screening_threshold'])

    def test_abba_win_remains_diagnostic(self):
        result=compare_isolation(self.comparison([40,30,30,40]))[0]
        self.assertTrue(result['timings']['GPUTime']['median']['exceeds_screening_threshold'])
        self.assertFalse(result['promotion_ready'])

    def test_incomplete_abba_rejected(self):
        with self.assertRaisesRegex(ValueError,'Incomplete'):
            compare_isolation(self.comparison([40,30]))

    def test_duplicate_auxiliary_counters_preserved_separately(self):
        header=self.header+['FMsgLogf/FMsgLogfCount','FMsgLogf/FMsgLogfCount']
        result=analyse(self.capture([['',20,18,5,9216,5000,4000,2,7]],header=header),minimum_frames=1)
        self.assertEqual(result['metrics']['FMsgLogf/FMsgLogfCount#1']['median'],2)
        self.assertEqual(result['metrics']['FMsgLogf/FMsgLogfCount#2']['median'],7)
        self.assertEqual(result['metrics']['FrameTime']['samples'],1)
        self.assertTrue(any('Duplicate counters' in w for w in result['warnings']))

    def test_duplicate_critical_counters_rejected(self):
        for name in ['FrameTime','GPUTime','GPUMem/LocalBudgetMB']:
            with self.assertRaisesRegex(ValueError,'Duplicate critical'):
                analyse(self.capture([['',20,18,5,9216,5000,4000,8]],header=self.header+[name]),minimum_frames=1)

    def test_duplicate_renaming_collision_rejected(self):
        with self.assertRaisesRegex(ValueError,'collision'):
            analyse(self.capture([['',20,18,5,9216,5000,4000,2,7,9]],
                header=self.header+['Counter','Counter','Counter#1']),minimum_frames=1)

    def test_zero_memory_pair_is_unknown_not_free(self):
        result=analyse(self.capture([['',20,18,5,9216,5000,4000],
            ['',120,110,5,9216,0,0]]),minimum_frames=2)
        self.assertEqual(result['frames'],2)
        self.assertEqual(result['metrics']['FrameTime']['max'],120)
        self.assertEqual(result['local_memory']['unavailable_frames'],1)
        self.assertEqual(result['local_memory']['minimum_headroom_mb'],1000)
        self.assertEqual(result['local_memory']['coverage_fraction'],.5)

    def test_impossible_memory_pair_rejected(self):
        with self.assertRaisesRegex(ValueError,'Invalid GPU memory'):
            analyse(self.capture([['',20,18,5,9216,0,4000]]),minimum_frames=1)

    def test_memory_gap_prevents_valid_comparison(self):
        rows=self.comparison([40,30,30,40])
        rows[1]['analysis']['local_memory']['unavailable_frames']=1
        self.assertFalse(compare_isolation(rows)[0]['memory_budget_valid'])


if __name__ == '__main__':
    unittest.main()
