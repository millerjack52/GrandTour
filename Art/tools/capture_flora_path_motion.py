"""Capture a short actual-game camera move. Playback fps is not a benchmark."""
from pathlib import Path
import json,math,subprocess,ctypes,datetime,sys
ROOT=Path('C:/GrandTour');OUT=ROOT/'Art/Export/LidarStudy/FloraPath'
FRAMES=Path('D:/GrandTourAssets/Reviews/FloraPathMotion');FRAMES.mkdir(parents=True,exist_ok=True)
cfg=json.loads((OUT/'build-report.json').read_text());c=cfg['camera'];x,y,z=c['position'];cmds=['2:EnableCheats','3:ke GTDistanceStyleController FinishReviewShaders','4:r.SetRes 1280x640w',f"5:ke GTDistanceStyleController SetReviewView {x} {y} {z} {c['pitch']} {c['yaw']} {c['fov']}"]
for i in range(60):
 t=max(0,min(1,(i-8)/44));ease=t*t*(3-2*t);frame=90+i
 cmds.append(f"{frame}:ke GTDistanceStyleController SetReviewView {x+45*ease:.3f} {y-70*ease:.3f} {z+12*ease:.3f} {c['pitch']-3*ease:.3f} {c['yaw']+4*ease:.3f} {c['fov']:.3f}")
 cmds.append(f'{frame}:Shot filename={FRAMES.as_posix()}/frame-{i:03}.png -nosuffix')
initial='EnableCheats,ShowHUD,DisableAllScreenMessages,r.MotionBlurQuality 0,r.ScreenPercentage 100,r.AntiAliasingMethod 4,sg.AntiAliasingQuality 3,r.VolumetricFog.GridPixelSize 16,r.VolumetricFog.GridSizeZ 64,t.IdleWhenNotForeground 0,CsvProfile FRAMES=155'
args=['C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe',str(ROOT/'GrandTour.uproject'),'/Game/GrandTour/ArtTests/FloraPath/L_FloraPath','-game','-windowed','-ResX=1280','-ResY=640','-RenderOffScreen','-Unattended','-NoSplash','-NoSound','-GTNoLoad','-noshaderworker','-GTLookKuwahara=0','-GTLidarPerformance=0','-dx12','-ExecCmds='+initial,'-ExitAfterCsvProfiling','-csvExecCmds='+','.join(cmds),'-abslog='+str(OUT/'motion.log')]
assert len(subprocess.list2cmdline(args))<16000
kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.CreateMutexW.restype=ctypes.c_void_p;kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint];kernel.ReleaseMutex.argtypes=[ctypes.c_void_p];kernel.CloseHandle.argtypes=[ctypes.c_void_p]
h=kernel.CreateMutexW(None,False,'Local\\GrandTour-BenmoreProfiling');held=kernel.WaitForSingleObject(h,0) in (0,0x80)
assert held,'Unreal reserved'
start=datetime.datetime.now().timestamp()
try:
 processes=subprocess.run(['powershell','-NoProfile','-Command','@(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue).Count'],capture_output=True,text=True)
 assert processes.stdout.strip()=='0','Unreal occupied'
 si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
 result=subprocess.run(args,cwd=ROOT,startupinfo=si);assert result.returncode==0,result.returncode
 frames=[FRAMES/f'frame-{i:03}.png' for i in range(60)];assert all(p.exists() and p.stat().st_mtime>=start for p in frames)
 import imageio_ffmpeg
 subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-framerate','15','-i',str(FRAMES/'frame-%03d.png'),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/'camera-check.mp4')],check=True,capture_output=True)
 (OUT/'motion-report.json').write_text(json.dumps({'ok':True,'frames':60,'playback_fps':15,'duration_seconds':4,'resolution':[1280,640],'renderer':'Unreal game / TSR','benchmark':False,'wind_enabled':False,'description':'Slow camera translation and pan with continuous temporal history; screenshot capture time is excluded from performance assessment.'},indent=2))
 print('Actual-game camera clip captured: 60 frames. Playback is not performance evidence.')
finally:
 if held:kernel.ReleaseMutex(h)
 kernel.CloseHandle(h)
