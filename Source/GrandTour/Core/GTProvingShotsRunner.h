#pragma once

#include "CoreMinimal.h"
#include "Terrain/GTTerrainGenerator.h"

class ACameraActor;
class AStaticMeshActor;
class AGTCarPawn;
class AGTPlayerController;
class UWorld;

/**
 * L_Proving's picture mode (RIVERBED S2, 2026-09-23, VEHICLE_BUILD_SYSTEM 52): the bog_shots pattern on the Proving
 * Ground. -GTProvingShots with -RenderOffScreen (Art/proving_shots.bat; log Saved/Logs/proving_shots.log, pictures in
 * Saved/Screenshots/Proving). One step per stage's pictures; -GTShotsFrom=N starts at step N, so S3 and S4 add theirs
 * after step 1 and take them alone. Driven by AGTRunGameMode::Tick; PASS when every picture asked for was written.
 *
 * Step 1 (S2): the car parked on forda's channel bank - the channel's floor where it was Mud-dominant before section 52,
 * dry, past the ford's sheet - and left on the handbrake until its sinkage stops growing. Then a picture from each side
 * at wheel height, and for each wheel on the camera's side the drawn tyre's lowest point, the ground line under its
 * outer face and a box round the tyre's lower half, in screen pixels (GTPROVINGSHOTS wheel lines; Art/tools/
 * sample_wheels.ps1 reads the tyre's lowest visible pixel in the box against the ground line). Then the control: the
 * same car settled on a flat Dirt top (a climb's, 2 cm of relief) and shot from its sunlit side (proving_03_flat_sunlit).
 *
 * Step 2 (RIVERBED S3, VEHICLE_BUILD_SYSTEM 53): the owner's picture 2 ("the water only covers a square of the pond"). The
 * car back on the pad, out of the view; the camera at the forda station (its point and heading, eye 5 m over the ground)
 * looking across the pond, pitched at the ford's middle on the water. Along the placed box's two flow-wise ends (the
 * straight edges before S3) the runner logs pairs of screen points on the water plane 1 m inside and 1 m outside the old
 * edge, where the bed under both is under the level (edge lines; Art/tools/sample_basin.ps1 counts the water pixels).
 *
 * Step 3 (RIVERBED S4, VEHICLE_BUILD_SYSTEM 54): forda's ruts under the water. The camera on the entry bank, 3 m up and
 * 3 m to the left of the road 3 m before the entry waterline, looking at the left wheel line 2.75 m into the water; a
 * picture with the water calmed (proving_05_forda_ruts_before), then the car crosses forda at full throttle along the
 * route and is put back on the pad, the water calmed again, the same picture (proving_06_forda_ruts_after). The runner
 * logs the left wheels' path as a rutbox and the same path 2.5 m further left as a ctrlbox (untouched wet bed), both in
 * screen pixels, with the field's own rut depth under the water (GTFORDRUT); Art/tools/sample_ford_ruts.ps1 compares
 * the boxes within and between the two pictures. Then the bed patch's box edge on the approach road, hide_17's view
 * (proving_07_forda_box_edge; borderbox, mudstrip and landstrip lines for Art/tools/sample_border.ps1).
 *
 * Step 4 (LOOK L1, VEHICLE_BUILD_SYSTEM 55): the GT Paint props beside the parked car. The car on step 1's flat Dirt top
 * (the control's spot) on the handbrake; SM_TestBox 3.8 m ahead of it and SM_TestCar (the blockout copy the Blender test
 * bakes) 5.2 m behind it, both from /Game/GrandTour/Props/Painted, spawned without collision on the car's heading. A
 * picture from 9 m out on the sunlit side, 1.6 m over the top's height, with both props in M_GT_PaintedGrey
 * (proving_08_painted_before), then the same picture with each in its MI_GT_Painted_<Asset>
 * (proving_09_painted_after). For each picture the runner logs a
 * borderbox per prop - the middle of the camera-facing side, 25-75 % along it and 30-60 % up it - and one on the
 * parked car's side (its M_GT_Vehicle never changes, so it reads the exposure drift between the two); Art/tools/
 * sample_tones.ps1 reads the mean colour and the distinct tones in each. Look L1 follow-up 3: two more boxes on the
 * car itself, car_FrontDoors and car_RearPanel - the camera-side half of each panel, 25-75 % along and 30-60 % up its
 * bounds on the camera-facing face - with the panel's UsePaint logged (the owner's panel bakes, UGTBodyComponent).
 * Follow-up 5: car_Bonnet and car_Roof by the same rule.
 */
class FGTProvingShotsRunner
{
public:
	explicit FGTProvingShotsRunner(UWorld* InWorld);

	/** True when finished. */
	bool Tick(float DeltaSeconds, bool& bOutPass, FString& OutSummary);

private:
	void Log(const FString& Line) const;
	void Next();
	void Enter(int32 InSubStep);
	void ShowFromCamera(const FVector& Location, const FRotator& Rotation);
	void RequestShot(const FString& Name);
	bool Project(const FVector& Point, FVector2D& OutScreen) const;
	float Ground(float XCm, float YCm) const;
	bool FindBankSpot(FVector2D& OutCentre, float& OutYaw);
	void LogWheels(const FString& Picture, const FVector& Eye);
	void LogSinkage(const TCHAR* When) const;
	void TickBank(float DeltaSeconds);
	/** RIVERBED S3 (VEHICLE_BUILD_SYSTEM 53): step 2, the owner's picture 2 - forda's pond from its station. */
	void TickBasin(float DeltaSeconds);
	void LogBasinEdges(const FString& Picture);
	/** RIVERBED S4 (VEHICLE_BUILD_SYSTEM 54): step 3, forda's ruts under the water and its bed patch's box edge. */
	void TickRuts(float DeltaSeconds);
	void LogScreenBox(const FString& Name, const TArray<FVector>& Points) const;
	void LogRutField(const TCHAR* When) const;
	FVector2D RouteXY(float ArcM, FVector2D& OutLeft) const;
	/** LOOK L1 (VEHICLE_BUILD_SYSTEM 55): step 4, the painted props beside the parked car, before and after. */
	void TickPainted(float DeltaSeconds);
	bool FindFlatDirtTop(FVector2D& OutCentre, float& OutYaw) const;
	void LogPaintBoxes(const FString& Picture) const;
	void SetPaintMaterials(bool bPainted);
	int32 CompileJobs() const;

	TWeakObjectPtr<UWorld> World;
	TWeakObjectPtr<AGTPlayerController> PC;
	TWeakObjectPtr<AGTCarPawn> Car;
	TWeakObjectPtr<ACameraActor> ShotCamera;
	FGTTerrainSpec Spec;
	TArray<FString> ShotFiles;
	TArray<FString> Notes;
	int32 Step = -1;
	int32 ShotsFrom = 0;
	int32 ExpectedShots = 0;
	float Elapsed = 0.f;
	float StepTime = 0.f;
	float SubTime = 0.f;
	float LogTimer = 0.f;
	int32 SubStep = 0;
	bool bDone = false;
	bool bPass = false;
	FString Summary;

	// Step 1.
	FVector2D BankCentre = FVector2D::ZeroVector;
	float BankYaw = 0.f;
	float LastSinkSum = -1.f;
	float SinkCheckTime = 0.f;
	bool bControl = false;   // the second half of step 1: the same car on a flat Dirt top (2 cm relief), the sunlit side

	// Step 2.
	FVector BasinEye = FVector::ZeroVector;

	// Step 3.
	float FordEntryArc = -1.f;
	float FordExitArc = -1.f;
	float FordMidArc = 0.f;
	FVector RutEye = FVector::ZeroVector;
	FRotator RutLook = FRotator::ZeroRotator;
	TArray<FVector2D> LeftPath;
	float DriveTime = 0.f;

	// Step 4.
	TArray<TWeakObjectPtr<AStaticMeshActor>> PaintProps;
	TArray<FString> PaintNames;
	float PaintSide = 1.f;
};
