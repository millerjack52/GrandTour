@echo off
setlocal
set UE="C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
for %%I in ("%~dp0..") do set ROOT=%%~fI
set SRC=%ROOT%\Art\Textures\Mud\muddy_tracks
echo Close the Unreal editor first. Imports the CC0 mud texture set "Muddy Tracks" (muddy_tracks by Amal Kumar,
echo Poly Haven, CC0), 2K diffuse / normal (DirectX, _nor_dx) / roughness / displacement, from
echo Art\Textures\Mud\muddy_tracks into /Game/GrandTour/Textures/Mud. Run it before setup_m6_mud.bat, which is the
echo material that will sample them (docs/MUD_ONE_SURFACE_PLAN.md stage E). Nothing is painted or generated.
echo It also imports the CC0 water ripple normal (others_0028 "Rain Ripples on Puddle" by TextureCan.com, CC0 1.0,
echo Art\Textures\Water\rain_ripples, provenance in Art\Textures\Water\SOURCE.txt) into
echo /Game/GrandTour/Textures/Water as T_GT_Water_N - docs/WATER_PLAN.md stage W4. M_GT_Water refuses to build
echo without it, so run this before setup_m6_water.bat.
echo.
echo Measuring the diffuse map's mean colour in linear space (PowerShell System.Drawing: Unreal's Python has no
echo PIL and cannot decode a JPG, so the number is written to muddy_tracks_mean.json for the script to read)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Add-Type -AssemblyName System.Drawing; $src='%SRC%\muddy_tracks_diff_2k.jpg'; $out='%SRC%\muddy_tracks_mean.json'; if (-not (Test-Path $src)) { Write-Host ('SETUP_M6_TEXTURES missing ' + $src); exit 1 }; $lut=New-Object 'double[]' 256; for($i=0;$i -lt 256;$i++){ $c=$i/255.0; if($c -le 0.04045){ $lut[$i]=$c/12.92 } else { $lut[$i]=[Math]::Pow((($c+0.055)/1.055),2.4) } }; $bmp=New-Object System.Drawing.Bitmap -ArgumentList $src; $w=$bmp.Width; $h=$bmp.Height; $sx=[Math]::Max(1,[int]($w/256)); $sy=[Math]::Max(1,[int]($h/256)); $lr=0.0; $lg=0.0; $lb=0.0; $ur=0.0; $ug=0.0; $ub=0.0; $n=0; for($y=0;$y -lt $h;$y+=$sy){ for($x=0;$x -lt $w;$x+=$sx){ $p=$bmp.GetPixel($x,$y); $lr+=$lut[$p.R]; $lg+=$lut[$p.G]; $lb+=$lut[$p.B]; $ur+=$p.R; $ug+=$p.G; $ub+=$p.B; $n++ } }; $bmp.Dispose(); $o=[pscustomobject]@{ source=$src; width=$w; height=$h; samples=$n; mean_linear=@([Math]::Round($lr/$n,6),[Math]::Round($lg/$n,6),[Math]::Round($lb/$n,6)); mean_srgb_255=@([Math]::Round($ur/$n,2),[Math]::Round($ug/$n,2),[Math]::Round($ub/$n,2)) }; $o | ConvertTo-Json -Compress | Set-Content -Encoding ascii -Path $out; Write-Host ('SETUP_M6_TEXTURES mean colour ' + $o.mean_linear[0] + ' ' + $o.mean_linear[1] + ' ' + $o.mean_linear[2] + ' (linear, from ' + $n + ' samples) -> ' + $out)"
echo.
%UE% "%ROOT%\GrandTour.uproject" -run=pythonscript -script="%~dp0Unreal\setup_m6_textures.py" -EnablePlugins=PythonScriptPlugin -unattended -nopause -nosplash -NullRHI -stdout -log=setup_m6_textures.log
echo.
findstr /C:"SETUP_M6_TEXTURES" /C:"Error" "%ROOT%\Saved\Logs\setup_m6_textures.log"
echo.
echo Done (exit code %ERRORLEVEL%). Log: %ROOT%\Saved\Logs\setup_m6_textures.log
pause
