# Read-only comparison of the same wet rut view with/without the water draw.
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
$outDir=Join-Path (Split-Path $PSScriptRoot) 'Export/LiveMudDrive'
$result=[ordered]@{region='x150..1299, y210..529; max RGB below 40';images=@{}}
foreach($name in @('Mud_After_Wet','Mud_Diagnostic_NoRutWater','Mud_PuddleTint_Candidate')){
    $bitmap=[System.Drawing.Bitmap]::new((Join-Path $outDir ($name+'.png')))
    try{
        $dark=0;$sum=0;$count=0
        for($y=210;$y -lt 530;$y++){
            for($x=150;$x -lt 1300;$x++){
                $c=$bitmap.GetPixel($x,$y);$v=[Math]::Max($c.R,[Math]::Max($c.G,$c.B))
                if($v -lt 40){$dark++};$sum+=$v;$count++
            }
        }
        $result.images[$name]=@{pixels=$count;dark_pixels=$dark;dark_percent=[Math]::Round(100*$dark/$count,3);mean_max_rgb=[Math]::Round($sum/$count,3)}
    }finally{$bitmap.Dispose()}
}
$json=$result|ConvertTo-Json -Depth 5
$json|Set-Content -LiteralPath (Join-Path $outDir 'water-diagnostic.json')
$json
