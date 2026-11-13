#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Vehicle/GTConditionComponent.h"
#include "GTBodyComponent.generated.h"

class UGTBodyStateComponent;
class UMaterialInstanceDynamic;
class UPrimitiveComponent;
class USceneComponent;
class UMaterialInterface;
class USkeletalMeshComponent;
class UStaticMesh;
class UStaticMeshComponent;
class UTexture2D;

/**
 * The car's visible body (ARCHITECTURE 6b). At BeginPlay it attaches every panel static mesh
 * from PanelFolder to the skeletal mesh at the car origin (the panels were exported with the
 * car's pivot, so their local space is car space), hides the skeletal mesh's body sections so
 * only its wheels still draw, and gives each panel its own dynamic instance of M_GT_Vehicle.
 *
 * Paint (Look L1 follow-up 3, VEHICLE_BUILD_SYSTEM 55): a panel whose name, a trailing _L/_R stripped, has the owner's
 * GT Paint bake in PaintFolder (T_GT_<Asset>_D and _M, _N optional; Art/setup_look_l1.bat's panel pass) gets them as
 * PaintAlbedo / PaintMask / PaintNormal on its instance with UsePaint 1; every other panel keeps UsePaint 0 (today's
 * BodyColour). The instance is the panel's for life: doors swing and panels detach with it, so the paint goes along.
 *
 * Dents: the condition component's impact list is written to a 32 x 2 float texture (row 0 =
 * local position and radius, row 1 = outward direction and depth) that MF_Dents reads to push
 * vertices in and bend the normal, so dents cross panel seams. Collision never deforms.
 *
 * Surface state: every tick each panel receives its region's dirt plus the body's wetness and
 * snow from UGTBodyStateComponent (Dirt, Wetness, Snow parameters).
 *
 * MudRunner MR2 (VEHICLE_BUILD_SYSTEM 80): every panel also gets CarMud (gt.Mud.CarMud), the coat's line (MudLineCm, from the
 * state's CoatLineCm), the washed band (WashCm, WashAmount), MudWet, and the regions' coats as three vectors (CoatEnds: front,
 * rear, roof, glass; CoatArches: FL, FR, RL, RR; CoatSides: left, right), which M_GT_Vehicle blends in car space so no panel
 * seam shows; MudBaseZ (the wheel bottoms) and WheelGeom (the axles' X, the hub height, the radius) from the skeleton's rest
 * pose at BeginPlay. The wheels (the skeletal mesh's KeepSkeletalSlots, M_Wheel, which drew the engine's WorldGridMaterial)
 * get a dynamic instance of M_GT_Tyre with TyreCoat per wheel.
 *
 * Doors: the four door panels hang off hinges at their front edge on the outer skin (computed from
 * each mesh's bounds, since every panel was exported about the car origin) and swing outward on
 * command with an eased angle. They block the Visibility channel (query only, no physics) so the
 * on-foot look trace can open and close them even when swung out.
 *
 * Detach: a panel whose damage region's health reaches zero is detached, given collision and
 * physics, and thrown outward with the car's velocity. Structural parts (tub, pillars) never
 * detach. A greybox windscreen plane carries M_GT_Glass with Crack = 1 - glass region health
 * and the glass region's dirt.
 */
UCLASS(ClassGroup = (GT), meta = (BlueprintSpawnableComponent))
class GRANDTOUR_API UGTBodyComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UGTBodyComponent();

	virtual void BeginPlay() override;

	/** Called by the pawn after the condition update: refreshes dents, surface state, cracks and detaches dead panels. */
	void Update(float DeltaSeconds, const UGTConditionComponent& Condition, const UGTBodyStateComponent& State, const FVector& CarVelocity);

	UFUNCTION(BlueprintPure, Category = "GT|Body")
	int32 GetPanelCount() const { return Panels.Num(); }

	UFUNCTION(BlueprintPure, Category = "GT|Body")
	int32 GetDetachedCount() const { return DetachedCount; }

	/** MR2: the wheel bottoms' height in car space, the wheel geometry (front axle X, rear axle X, hub Z, radius), the tyre slots given M_GT_Tyre. */
	UFUNCTION(BlueprintPure, Category = "GT|Body|Mud")
	float GetMudBaseZ() const { return MudBaseZ; }

	UFUNCTION(BlueprintPure, Category = "GT|Body|Mud")
	FVector4 GetWheelGeom() const { return WheelGeom; }

	UFUNCTION(BlueprintPure, Category = "GT|Body|Mud")
	int32 GetTyreSlots() const { return TyreSlots; }

	/** Workshop variants retain the original paint's texture, dents and dirt; zero is the original appearance. */
	UFUNCTION(BlueprintCallable, Category = "GT|Workshop")
	void SetWorkshopAppearance(int32 Paint, int32 Rims, int32 Tyres);
	UFUNCTION(BlueprintPure, Category = "GT|Workshop")
	bool WorkshopReady() const { return bWorkshopReady; }
	UPROPERTY(BlueprintReadOnly, Category = "GT|Workshop") int32 WorkshopPaint = 0;
	UPROPERTY(BlueprintReadOnly, Category = "GT|Workshop") int32 WorkshopRims = 0;
	UPROPERTY(BlueprintReadOnly, Category = "GT|Workshop") int32 WorkshopTyres = 0;
	UFUNCTION(BlueprintPure, Category = "GT|Workshop") bool WorkshopWheelsReady() const { return WorkshopRimComponents.Num()==4; }

	/** The lift's repair (M4): every dropped panel comes back onto the car; returns how many. Panels removed for lack of collision are gone. */
	UFUNCTION(BlueprintCallable, Category = "GT|Body")
	int32 ReattachAll();

	// ---- doors -------------------------------------------------------------------------------------
	UFUNCTION(BlueprintPure, Category = "GT|Body|Doors")
	int32 GetDoorCount() const { return Doors.Num(); }

	/** The door on a side and end, INDEX_NONE when the body has none there. */
	UFUNCTION(BlueprintPure, Category = "GT|Body|Doors")
	int32 FindDoor(bool bLeft, bool bFront) const;

	/** The front door on the driver's side (the car's DriverEyeOffset decides the side). */
	UFUNCTION(BlueprintPure, Category = "GT|Body|Doors")
	int32 GetDriverDoor() const;

	/** The door whose panel is this component, INDEX_NONE otherwise. */
	int32 DoorForComponent(const UPrimitiveComponent* Component) const;

	/** A door whose shut outline contains a car-space point on the body's side, INDEX_NONE otherwise. */
	int32 DoorAtLocalPoint(const FVector& LocalPoint) const;

	/** Swing a door open or shut, optionally after a delay in seconds. */
	UFUNCTION(BlueprintCallable, Category = "GT|Body|Doors")
	void SetDoorOpen(int32 Door, bool bOpen, float Delay = 0.f);

	/** True once the door has been told to open (it may still be swinging). */
	UFUNCTION(BlueprintPure, Category = "GT|Body|Doors")
	bool IsDoorOpen(int32 Door) const;

	/** Degrees the door stands open right now. */
	UFUNCTION(BlueprintPure, Category = "GT|Body|Doors")
	float GetDoorAngle(int32 Door) const;

	UFUNCTION(BlueprintPure, Category = "GT|Body|Doors")
	bool IsDoorDetached(int32 Door) const;

	UFUNCTION(BlueprintPure, Category = "GT|Body|Doors")
	bool IsDoorFront(int32 Door) const;

	UFUNCTION(BlueprintPure, Category = "GT|Body|Doors")
	bool IsDoorLeft(int32 Door) const;

	/** Someone can pass: the door stands at least DoorwayClearAngle open, or it is gone. */
	UFUNCTION(BlueprintPure, Category = "GT|Body|Doors")
	bool IsDoorwayClear(int32 Door) const;

	/** "front-left door". */
	UFUNCTION(BlueprintPure, Category = "GT|Body|Doors")
	FString DoorName(int32 Door) const;

	UFUNCTION(BlueprintPure, Category = "GT|Body|Doors")
	FString DescribeDoors() const;

	/** The door's outline in car space when shut. */
	FBox GetDoorClosedBounds(int32 Door) const;
	FVector GetDoorHingeLocal(int32 Door) const;
	UStaticMeshComponent* GetDoorPanel(int32 Door) const;
	USceneComponent* GetDoorHinge(int32 Door) const;

	/** A car-space spot for a capsule just behind a door's trailing edge, clear of the door when it stands open. */
	FVector GetExitSpotBehindDoor(int32 Door, float CapsuleRadius) const;

	/** Detached panels that are simulating physics right now. */
	UFUNCTION(BlueprintPure, Category = "GT|Body")
	int32 GetSimulatingCount() const;

	/** One line per panel: name, region, attached or detached; plus the texture and windscreen state. */
	UFUNCTION(BlueprintPure, Category = "GT|Body")
	FString Describe() const;

	/** Content folder holding the panel static meshes made by Art/import_rangerover.bat. */
	UPROPERTY(EditAnywhere, Category = "GT|Body")
	FString PanelFolder = TEXT("/Game/GrandTour/Vehicles/Bodies/RangeRover/Panels");

	UPROPERTY(EditAnywhere, Category = "GT|Body")
	FString PanelPrefix = TEXT("SM_RR_");

	/** Look L1 follow-up 3: the owner's GT Paint panel bakes (T_GT_<Asset>_D/_M/_N), made by Art/setup_look_l1.bat. */
	UPROPERTY(EditAnywhere, Category = "GT|Body")
	FString PaintFolder = TEXT("/Game/GrandTour/Vehicles/Bodies/RangeRover/Paint");

	/** Panel names (after the prefix) that are not body panels: the wheels are bones on the skeletal mesh. */
	UPROPERTY(EditAnywhere, Category = "GT|Body")
	TArray<FString> SkipPanels = { TEXT("Wheel") };

	/** Skeletal mesh material slots that keep drawing (everything else is replaced by the panels). */
	UPROPERTY(EditAnywhere, Category = "GT|Body")
	TArray<FName> KeepSkeletalSlots = { TEXT("M_Wheel") };

	UPROPERTY(EditAnywhere, Category = "GT|Body")
	FLinearColor BodyColour = FLinearColor(0.55f, 0.47f, 0.30f);

	UPROPERTY(EditAnywhere, Category = "GT|Body")
	FLinearColor TrimColour = FLinearColor(0.05f, 0.05f, 0.05f);

	UPROPERTY(EditAnywhere, Category = "GT|Body")
	FLinearColor InteriorColour = FLinearColor(0.12f, 0.10f, 0.09f);

	/** Outward speed (cm/s) given to a detaching panel on top of the car's velocity. */
	UPROPERTY(EditAnywhere, Category = "GT|Body")
	float DetachSpeed = 300.f;

	/** Panel names (after the prefix) that are doors; "Front" in the name makes it a front door, the bounds decide the side. */
	UPROPERTY(EditAnywhere, Category = "GT|Body|Doors")
	TArray<FString> DoorPanels = { TEXT("FrontDoors_L"), TEXT("FrontDoors_R"), TEXT("PassengerDoors_L"), TEXT("PassengerDoors_R") };

	UPROPERTY(EditAnywhere, Category = "GT|Body|Doors", meta = (ClampMin = 10, ClampMax = 90))
	float DoorOpenAngle = 65.f;

	/** Seconds for a full swing either way. */
	UPROPERTY(EditAnywhere, Category = "GT|Body|Doors", meta = (ClampMin = 0.05, ClampMax = 3))
	float DoorSwingSeconds = 0.45f;

	UPROPERTY(EditAnywhere, Category = "GT|Body|Doors", meta = (ClampMin = 5, ClampMax = 90))
	float DoorwayClearAngle = 40.f;

	/** Door panels block the Visibility channel (query only) so the look trace finds them, even swung out. */
	UPROPERTY(EditAnywhere, Category = "GT|Body|Doors")
	bool bDoorsTargetable = true;

	/** Off: the user does not want the greybox sheet in view; the glass material and crack plumbing wait for real glass. */
	UPROPERTY(EditAnywhere, Category = "GT|Body|Greybox")
	bool bBuildWindscreen = false;

	/** Windscreen plane in car space: from the dash top (x 99, z 120) up to the roof's front edge (x 63, z 166). */
	UPROPERTY(EditAnywhere, Category = "GT|Body|Greybox")
	FVector WindscreenCentre = FVector(81.f, 0.f, 143.f);

	UPROPERTY(EditAnywhere, Category = "GT|Body|Greybox")
	float WindscreenPitch = 128.f;

	/** Length along the rake, width, thickness, cm. */
	UPROPERTY(EditAnywhere, Category = "GT|Body|Greybox")
	FVector WindscreenSize = FVector(58.f, 150.f, 1.f);

	// ---- state ---------------------------------------------------------------------------------
	UPROPERTY(BlueprintReadOnly, Category = "GT|Body")
	int32 ImpactTextureCount = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Body")
	int32 HiddenSkeletalSlots = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Body")
	int32 PanelsWithoutCollision = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GT|Body")
	float WindscreenCrack = 0.f;

private:
    void BuildWorkshopEquipment(USkeletalMeshComponent* Mesh);
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> WorkshopEquipmentComponents;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> WorkshopEquipmentMaterials;
    TArray<int32> WorkshopEquipmentMaterialParts;
public:
    UPROPERTY(BlueprintReadOnly, Category="GT|Workshop") int32 WorkshopEquipment=0;
    UFUNCTION(BlueprintPure, Category="GT|Workshop") bool WorkshopEquipmentReady() const { return WorkshopEquipmentComponents.Num()==3; }
    UFUNCTION(BlueprintCallable, Category="GT|Workshop") void SetWorkshopEquipment(int32 Mask);
private:
	bool bWorkshopReady = false;
	void BuildWorkshopWheels(USkeletalMeshComponent* Mesh);
	void ApplyWorkshopWheels(int32 Rims, int32 Tyres);
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMesh>> WorkshopRimMeshes;
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMesh>> WorkshopTyreMeshes;
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> WorkshopRimComponents;
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> WorkshopTyreComponents;
	UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> WorkshopWheelMaterials;
	TArray<int32> WorkshopMaterialWheels;
	struct FPanel
	{
		FString Name;
		EGTDamageRegion Region = EGTDamageRegion::None;
		int32 Index = -1;   // into PanelComponents and PanelMaterials
		bool bDetached = false;
		bool bHasCollision = false;
		int32 DoorIndex = INDEX_NONE;   // into Doors
	};

	struct FDoor
	{
		int32 PanelSlot = INDEX_NONE;   // into Panels
		bool bFront = true;
		bool bLeft = true;
		FVector HingeLocal = FVector::ZeroVector;
		FBox ClosedBounds = FBox(ForceInit);
		float Phase = 0.f;              // 0 shut .. 1 open, eased into the angle
		bool bTargetOpen = false;
		float PendingDelay = -1.f;      // seconds until bPendingOpen applies, < 0 none
		bool bPendingOpen = false;
	};

	void UpdateDoors(float DeltaSeconds);
	void ConfigureDoorCollision(UStaticMeshComponent* Component) const;

	static EGTDamageRegion RegionForPanel(const FString& Name, const FBox& LocalBounds);
	static FVector OutwardDirection(EGTDamageRegion Region);
	void AttachPanels(USkeletalMeshComponent* Mesh);
	void HideSkeletalSections(USkeletalMeshComponent* Mesh);
	void BuildWindscreen(USkeletalMeshComponent* Mesh);
	void UpdateImpactTexture(const UGTConditionComponent& Condition);
	/** MR2: MudBaseZ and WheelGeom from the movement's wheel setups and the skeleton's rest pose. */
	void ComputeWheelGeometry(USkeletalMeshComponent* Mesh);
	/** MR2: M_GT_Tyre on the wheels' slots. */
	void DressTyres(USkeletalMeshComponent* Mesh);
	/** MR2: the mud's parameters into every panel, the tyres and the windscreen. */
	void PushMud(const UGTBodyStateComponent& State);
	void Detach(FPanel& Panel, const FVector& CarVelocity, const FTransform& CarTransform);
	UMaterialInstanceDynamic* MakePanelMaterial(FName SlotName);

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> VehicleMaterial;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> GlassMaterial;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> WindscreenMaterial;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> TyreMaterial;

	UPROPERTY(Transient)
	TObjectPtr<UTexture2D> ImpactTexture;

	UPROPERTY(Transient)
	TObjectPtr<UStaticMeshComponent> Windscreen;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> PanelComponents;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> PanelMaterials;

	/** One hinge per door, parallel to Doors. */
	UPROPERTY(Transient)
	TArray<TObjectPtr<USceneComponent>> DoorHinges;

	TArray<FDoor> Doors;

	TArray<FPanel> Panels;
	int32 LastImpactsVersion = -1;
	int32 DetachedCount = 0;
	// MR2
	float MudBaseZ = 0.f;
	FVector4 WheelGeom = FVector4(140.f, -146.f, 38.f, 38.f);
	int32 TyreSlots = 0;
	/** The values last pushed (CarMud, line, wash, wash amount, wet, the ten coats, the four tyres): a push only when one moved. */
	TArray<float> PushedMud;
};
