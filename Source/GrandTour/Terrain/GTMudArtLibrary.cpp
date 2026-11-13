#include "Terrain/GTMudArtLibrary.h"

#include "Engine/Texture.h"
#include "Engine/Texture2D.h"
#include "Engine/Texture2DArray.h"
#include "PixelFormat.h"

int32 UGTMudArtLibrary::BuildTextureArray(UTexture2DArray* Array, const TArray<UTexture2D*>& Slices, FString& OutMessage)
{
#if WITH_EDITOR
	if (!Array)
	{
		OutMessage = TEXT("no array");
		return -1;
	}
	if (Slices.Num() == 0 || Slices.Contains(nullptr))
	{
		OutMessage = TEXT("no slices, or a missing one");
		return -1;
	}
	Array->Modify();
	Array->SourceTextures.Reset();
	for (UTexture2D* Slice : Slices)
	{
		Array->SourceTextures.Add(Slice);
	}
	if (!Array->CheckArrayTexturesCompatibility())
	{
		OutMessage = TEXT("the slices differ in size or pixel format (CheckArrayTexturesCompatibility)");
		return -1;
	}
	if (!Array->UpdateSourceFromSourceTextures(true))
	{
		OutMessage = TEXT("UpdateSourceFromSourceTextures failed");
		return -1;
	}
	Array->PostEditChange();
	Array->MarkPackageDirty();
	const int32 NumSlices = static_cast<int32>(Array->Source.GetNumSlices());
	OutMessage = FString::Printf(TEXT("%d slices of %d x %d"), NumSlices, static_cast<int32>(Array->Source.GetSizeX()), static_cast<int32>(Array->Source.GetSizeY()));
	return NumSlices;
#else
	OutMessage = TEXT("editor only");
	return 0;
#endif
}

int32 UGTMudArtLibrary::TextureArraySourceSlices(UTexture2DArray* Array, int32& OutSizeX, int32& OutSizeY)
{
	OutSizeX = 0;
	OutSizeY = 0;
#if WITH_EDITOR
	if (!Array || !Array->Source.IsValid())
	{
		return 0;
	}
	OutSizeX = static_cast<int32>(Array->Source.GetSizeX());
	OutSizeY = static_cast<int32>(Array->Source.GetSizeY());
	return Array->Source.GetNumSlices();
#else
	return 0;
#endif
}

int64 UGTMudArtLibrary::TextureAllMipsBytes(UTexture* Texture, FString& OutFormat)
{
	if (!Texture)
	{
		OutFormat = TEXT("none");
		return 0;
	}
#if WITH_EDITOR
	// The editor builds textures asynchronously: until a texture's build finishes it reports a placeholder (0 bytes).
	Texture->BlockOnAnyAsyncBuild();
	Texture->FinishCachePlatformData();
#endif
	FTexturePlatformData** Data = Texture->GetRunningPlatformData();
	OutFormat = (Data && *Data) ? FString(GPixelFormats[(*Data)->PixelFormat].Name) : FString(TEXT("unknown"));
	return static_cast<int64>(Texture->CalcTextureMemorySizeEnum(TMC_AllMips));
}
