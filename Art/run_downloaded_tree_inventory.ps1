param([string]$Only='*')
$ErrorActionPreference='Stop'
$root='C:/GrandTour'
$base='D:/GrandTourAssets/FlippedNormals'
$out=$root+'/Art/Export/TreeInventory'
$mutex=[Threading.Mutex]::new($false,'Local\GrandTour-BenmoreProfiling');$held=$false
try {
    try {$held=$mutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$held=$true}
    if(-not $held) {throw 'Renderer slot reserved'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd,blender -ErrorAction SilentlyContinue) {throw 'Renderer already running'}
    $sources=@(
        @('flora-main','Flora_Paint_Assets_Library_v1_3_PRO/Main_Library/FloraPaint_v1_3_Library.blend'),
        @('flora-update','Flora_Paint_Assets_Library_v1_3_PRO/Main_Library/V1.1_Update/V1_1_Tree.blend'),
        @('trees-library','Trees_Assets_Library/Trees_Assets_01.blend'),
        @('lazy-assets','Lazy_Forest_Gen_Addon/Assets/Assets.blend'),
        @('lazy-generator','Lazy_Forest_Gen_Addon/Data.blend'),
        @('stylized-assets','Stylized Forest Generator Addon - Trees & Plants Assets/Stylized_Forest_Gen_Addon_v_1_0_1/Stylized_Forest_Gen_Addon/Stylized_Forest_Assets/Assets.blend'),
        @('stylized-generator','Stylized Forest Generator Addon - Trees & Plants Assets/Stylized_Forest_Gen_Addon_v_1_0_1/Stylized_Forest_Gen_Addon/Stylized_Forest.blend'),
        @('grasspaint-assets','Stylized Forest Generator Addon - Trees & Plants Assets/Assets_Pack/GrassPaint_Stylized_Forest_Assets_Pack/Stylized_Forest_Assets/Grass_Paint.blend'),
        @('grasspaint-generator','Stylized Forest Generator Addon - Trees & Plants Assets/Assets_Pack/GrassPaint_Stylized_Forest_Assets_Pack/Grass_Paint.blend'),
        @('flora-bonus-000','Flora_Paint_Bonus_Project_Files/Bonus_Project_Files/000/1116_001.blend'),
        @('flora-bonus-001','Flora_Paint_Bonus_Project_Files/Bonus_Project_Files/001/001.blend'),
        @('flora-bonus-002','Flora_Paint_Bonus_Project_Files/Bonus_Project_Files/002/Forest_20240121.blend'),
        @('sample44','Sample File_4.4_.blend'),
        @('flora-extra-assets','Flora_Paint_Assets_Library_v1_3_PRO/Other/FP_Other_Assets.blend'),
        @('flora-extra-scatter','Flora_Paint_Assets_Library_v1_3_PRO/Other/FP_Scatter_beta_01.blend'),
        @('flora-extra-wood','Flora_Paint_Assets_Library_v1_3_PRO/Other/FP_Wood_Texture.blend'),
        @('flora-extra-scatter-p0','Flora_Paint_Assets_Library_v1_3_PRO/Other/Scatter_Tool_P0.blend')
    )
    foreach($entry in $sources) {
        if($entry[0] -notlike $Only) {continue}
        $dest=$out+'/'+$entry[0];New-Item -ItemType Directory -Force $dest | Out-Null
        $source=$base+'/'+$entry[1]
        $args=@('--background','--factory-startup','--disable-autoexec','--python-exit-code','1',
            '--python',($root+'/Art/Blender/inventory_downloaded_trees.py'),'--',('"'+$source+'"'),('"'+$dest+'"'))
        $p=Start-Process 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' -ArgumentList $args -WindowStyle Hidden -PassThru -RedirectStandardOutput ($dest+'/audit.log') -RedirectStandardError ($dest+'/stderr.log')
        $null=$p.Handle;$p.WaitForExit()
        if($p.ExitCode -ne 0) {throw "Inventory failed for $($entry[0]): exit $($p.ExitCode)"}
        Write-Output ('Inventoried '+$entry[0])
    }
} finally {if($held) {$mutex.ReleaseMutex()};$mutex.Dispose()}
