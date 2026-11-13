$editorPath = 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'
$editorArguments = @(
    '"C:/GrandTour/GrandTour.uproject"',
    '/Game/GrandTour/Test/GraphicAdventure/L_GraphicAdventure_Test',
    '-multiprocess',
    '-NoSplash',
    '-EnablePlugins=PythonScriptPlugin',
    '-ExecutePythonScript="C:/GrandTour/Art/Unreal/open_graphic_adventure_test.py"'
)
# This is the interactive editor requested for the user's driving session.
Start-Process -FilePath $editorPath -ArgumentList $editorArguments
