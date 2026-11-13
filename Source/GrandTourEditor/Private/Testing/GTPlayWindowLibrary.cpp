#include "GTPlayWindowLibrary.h"

#include "Editor.h"
#include "Editor/EditorEngine.h"
#include "PlayInEditorDataTypes.h"
#include "Settings/LevelEditorPlaySettings.h"
#include "UObject/Package.h"

bool UGTPlayWindowLibrary::RequestPlayInNewWindow(int32 Width, int32 Height)
{
	if (!GEditor || GEditor->IsPlaySessionInProgress() || Width <= 0 || Height <= 0)
	{
		return false;
	}
	ULevelEditorPlaySettings* Settings = DuplicateObject<ULevelEditorPlaySettings>(GetDefault<ULevelEditorPlaySettings>(), GetTransientPackage());
	Settings->NewWindowWidth = Width;
	Settings->NewWindowHeight = Height;
	Settings->CenterNewWindow = true;
	FRequestPlaySessionParams Params;
	Params.WorldType = EPlaySessionWorldType::PlayInEditor;
	Params.EditorPlaySettings = Settings;
	// No DestinationSlateViewport: the editor opens the session in a new window of the settings' size.
	GEditor->RequestPlaySession(Params);
	UE_LOG(LogTemp, Display, TEXT("GTPlayWindowLibrary: Play In Editor requested in a new %d x %d window"), Width, Height);
	return true;
}
