// Wheel spray P2 (docs/WHEEL_SPRAY_PLAN.md): Niagara authored headless through UNiagaraExternalEditUtilities.
#include "FX/GTNiagaraSetupLibrary.h"

#include "NiagaraExternalSystemEditorUtilities.h"
#include "NiagaraSystem.h"
#include "NiagaraEmitter.h"
#include "NiagaraEmitterHandle.h"
#include "NiagaraTypes.h"
#include "NiagaraVariant.h"
#include "Materials/MaterialInterface.h"

namespace GTNiagaraSetup
{
	/** One build: the system, the edit context, the log. Every write goes through Guard first. */
	struct FBuild
	{
		UNiagaraSystem* System = nullptr;
		FNiagaraExternalEditContext Ctx;
		FString Log;
		bool bOk = true;

		void Line(const FString& S)
		{
			Log += S + TEXT("\n");
			UE_LOG(LogTemp, Display, TEXT("GTNIAGARASETUP %s"), *S);
		}

		bool Fail(const FString& S)
		{
			if (bOk)
			{
				Line(TEXT("FAIL ") + S);
			}
			bOk = false;
			return false;
		}

		/** Context errors become a FAIL naming the step. */
		bool Check(const FString& Step)
		{
			if (Ctx.Errors.Num() == 0)
			{
				return true;
			}
			FString All;
			for (const FText& E : Ctx.Errors)
			{
				All += E.ToString() + TEXT(" | ");
			}
			Ctx.Errors.Reset();
			return Fail(Step + TEXT(": ") + All);
		}

		bool Topology(FName Emitter, FNiagaraExt_EmitterTopology& Out)
		{
			FNiagaraExt_StackItemReference Ref(System, Emitter);
			UNiagaraExternalEditUtilities::GetEmitterTopology(Ref, Out, Ctx);
			return Check(FString::Printf(TEXT("GetEmitterTopology %s"), *Emitter.ToString()));
		}

		static const FNiagaraExt_ScriptStackTopology* Script(const FNiagaraExt_EmitterTopology& T, FName ScriptName)
		{
			for (const FNiagaraExt_ScriptStackTopology* S : { &T.EmitterSpawnScript, &T.EmitterUpdateScript, &T.ParticleSpawnScript, &T.ParticleUpdateScript })
			{
				if (S->ScriptName == ScriptName)
				{
					return S;
				}
			}
			return nullptr;
		}

		/** The crash guard (P0: a link to a wrongly named input, a static switch, crashed the editor). Read the emitter's
		 *  topology now, then assert: the script and the module exist by their exact names; the input exists in that module
		 *  by its exact name; its type is exactly Type (for an enum, any enum when Type is invalid); it is visible and
		 *  editable; and, unless bSwitchAllowed, it is not a static switch. Any miss fails with the name; nothing is written. */
		bool Guard(FName Emitter, FName ScriptName, FName Module, FName Input, const FNiagaraTypeDefinition& Type, bool bSwitchAllowed,
			FNiagaraExt_StackInputTopology* OutInput = nullptr)
		{
			if (!bOk)
			{
				return false;
			}
			FNiagaraExt_EmitterTopology T;
			if (!Topology(Emitter, T))
			{
				return false;
			}
			const FNiagaraExt_ScriptStackTopology* S = Script(T, ScriptName);
			if (!S)
			{
				return Fail(FString::Printf(TEXT("guard: no script %s in emitter %s"), *ScriptName.ToString(), *Emitter.ToString()));
			}
			const FNiagaraExt_ModuleTopology* M = S->Modules.FindByPredicate([&](const FNiagaraExt_ModuleTopology& X) { return X.ModuleName == Module; });
			if (!M)
			{
				return Fail(FString::Printf(TEXT("guard: no module %s in %s.%s"), *Module.ToString(), *Emitter.ToString(), *ScriptName.ToString()));
			}
			const FNiagaraExt_StackInputTopology* I = M->Inputs.FindByPredicate([&](const FNiagaraExt_StackInputTopology& X) { return X.Name == Input; });
			if (!I)
			{
				return Fail(FString::Printf(TEXT("guard: no input '%s' in %s.%s.%s"), *Input.ToString(), *Emitter.ToString(), *ScriptName.ToString(), *Module.ToString()));
			}
			const bool bTypeOk = Type.IsValid() ? I->Type == Type : I->Type.IsEnum();
			if (!bTypeOk)
			{
				return Fail(FString::Printf(TEXT("guard: input '%s' in %s is %s, expected %s"), *Input.ToString(), *Module.ToString(),
					*I->Type.GetName(), Type.IsValid() ? *Type.GetName() : TEXT("an enum")));
			}
			if (I->bIsStaticSwitch && !bSwitchAllowed)
			{
				return Fail(FString::Printf(TEXT("guard: input '%s' in %s is a static switch; refusing to link it"), *Input.ToString(), *Module.ToString()));
			}
			if (!I->bIsVisible || !I->bIsEditable)
			{
				return Fail(FString::Printf(TEXT("guard: input '%s' in %s is not visible/editable (visible %d editable %d)"), *Input.ToString(),
					*Module.ToString(), I->bIsVisible ? 1 : 0, I->bIsEditable ? 1 : 0));
			}
			if (OutInput)
			{
				*OutInput = *I;
			}
			return true;
		}

		FNiagaraExt_StackItemReference InputRef(FName Emitter, FName ScriptName, FName Module, FName Input) const
		{
			FNiagaraExt_StackItemReference Ref(System, Emitter, ScriptName, Module);
			Ref.InputNameStack.Add(Input);
			return Ref;
		}

		/** A local value of the input's own struct (Type's script struct, so the type check below cannot mismatch). */
		void SetLocal(FName Emitter, FName ScriptName, FName Module, FName Input, const FNiagaraTypeDefinition& Type, const void* Value, bool bSwitch = false)
		{
			if (!Guard(Emitter, ScriptName, Module, Input, Type, bSwitch))
			{
				return;
			}
			FNiagaraExt_StackInputValue V;
			V.InitializeAs(Type.GetScriptStruct(), static_cast<const uint8*>(Value));
			UNiagaraExternalEditUtilities::SetStackInputData(InputRef(Emitter, ScriptName, Module, Input), V, Ctx);
			if (Check(FString::Printf(TEXT("set %s.%s"), *Module.ToString(), *Input.ToString())))
			{
				Line(FString::Printf(TEXT("  %s.%s.%s set (%s)"), *Emitter.ToString(), *Module.ToString(), *Input.ToString(), *Type.GetName()));
			}
			if (bSwitch)
			{
				Refresh();
			}
		}

		void SetFloat(FName E, FName S, FName M, FName I, float X) { FNiagaraFloat V; V.Value = X; SetLocal(E, S, M, I, FNiagaraTypeDefinition::GetFloatDef(), &V); }
		void SetBool(FName E, FName S, FName M, FName I, bool X, bool bSwitch)
		{
			FNiagaraBool V;
			V.SetValue(X);
			SetLocal(E, S, M, I, FNiagaraTypeDefinition::GetBoolDef(), &V, bSwitch);
		}
		void SetVec3(FName E, FName S, FName M, FName I, const FVector3f& X) { SetLocal(E, S, M, I, FNiagaraTypeDefinition::GetVec3Def(), &X); }
		void SetColor(FName E, FName S, FName M, FName I, const FLinearColor& X) { SetLocal(E, S, M, I, FNiagaraTypeDefinition::GetColorDef(), &X); }

		/** An enum input (a static switch or not) by its display name, asserted to exist in the enum. */
		void SetEnum(FName Emitter, FName ScriptName, FName Module, FName Input, const FString& Display)
		{
			FNiagaraExt_StackInputTopology I;
			if (!Guard(Emitter, ScriptName, Module, Input, FNiagaraTypeDefinition(), true, &I))
			{
				return;
			}
			UEnum* Enum = I.Type.GetEnum();
			int32 Found = INDEX_NONE;
			FString Names;
			for (int32 K = 0; Enum && K < Enum->NumEnums() - 1; ++K)
			{
				const FString D = Enum->GetDisplayNameTextByIndex(K).ToString();
				Names += D + TEXT(", ");
				if (D == Display)
				{
					Found = K;
				}
			}
			if (Found == INDEX_NONE)
			{
				Fail(FString::Printf(TEXT("guard: enum input '%s' in %s has no value '%s' (has %s)"), *Input.ToString(), *Module.ToString(), *Display, *Names));
				return;
			}
			FNiagaraExt_StackInputValue V;
			FNiagaraExt_StackInputData_Enum& EV = V.InitializeAs<FNiagaraExt_StackInputData_Enum>();
			EV.Enum = Enum;
			EV.EnumName = Enum->GetNameByIndex(Found);
			UNiagaraExternalEditUtilities::SetStackInputData(InputRef(Emitter, ScriptName, Module, Input), V, Ctx);
			if (Check(FString::Printf(TEXT("set enum %s.%s = %s"), *Module.ToString(), *Input.ToString(), *Display)))
			{
				Line(FString::Printf(TEXT("  %s.%s.%s = %s%s"), *Emitter.ToString(), *Module.ToString(), *Input.ToString(), *Display, I.bIsStaticSwitch ? TEXT(" (switch)") : TEXT("")));
			}
			if (I.bIsStaticSwitch)
			{
				Refresh();
			}
		}

		/** A static switch reshapes the module's inputs: a fresh context (a new system view model) so the next topology sees it. */
		void Refresh()
		{
			Ctx = FNiagaraExternalEditContext(System);
		}

		/** A link to a User parameter: the guard, never a static switch, and the User parameter exists with the same type. */
		void Link(FName Emitter, FName ScriptName, FName Module, FName Input, const TCHAR* UserName, const FNiagaraTypeDefinition& Type)
		{
			if (!Guard(Emitter, ScriptName, Module, Input, Type, false))
			{
				return;
			}
			const FNiagaraVariableBase Var(Type, FName(UserName));
			if (!System->GetExposedParameters().FindParameterOffset(Var))
			{
				Fail(FString::Printf(TEXT("guard: no User parameter %s of type %s"), UserName, *Type.GetName()));
				return;
			}
			FNiagaraExt_StackInputValue V;
			FNiagaraExt_StackInputData_Linked& L = V.InitializeAs<FNiagaraExt_StackInputData_Linked>();
			L.LinkedVariable.Name = FName(UserName);
			L.LinkedVariable.Type = Type;
			UNiagaraExternalEditUtilities::SetStackInputData(InputRef(Emitter, ScriptName, Module, Input), V, Ctx);
			if (Check(FString::Printf(TEXT("link %s.%s -> %s"), *Module.ToString(), *Input.ToString(), UserName)))
			{
				Line(FString::Printf(TEXT("  %s.%s.%s -> %s"), *Emitter.ToString(), *Module.ToString(), *Input.ToString(), UserName));
			}
		}

		/** An HLSL expression input: the guard, never a static switch. */
		void Expr(FName Emitter, FName ScriptName, FName Module, FName Input, const FNiagaraTypeDefinition& Type, const FString& Hlsl)
		{
			if (!Guard(Emitter, ScriptName, Module, Input, Type, false))
			{
				return;
			}
			FNiagaraExt_StackInputValue V;
			V.InitializeAs<FNiagaraExt_StackInputData_HlslExpression>().HlslExpression = Hlsl;
			UNiagaraExternalEditUtilities::SetStackInputData(InputRef(Emitter, ScriptName, Module, Input), V, Ctx);
			if (Check(FString::Printf(TEXT("expression %s.%s"), *Module.ToString(), *Input.ToString())))
			{
				Line(FString::Printf(TEXT("  %s.%s.%s = %s"), *Emitter.ToString(), *Module.ToString(), *Input.ToString(), *Hlsl));
			}
		}

		void AddModule(FName Emitter, FName ScriptName, const FString& Path, FName After)
		{
			if (!bOk)
			{
				return;
			}
			UNiagaraScript* Asset = LoadObject<UNiagaraScript>(nullptr, *Path);
			if (!Asset)
			{
				Fail(TEXT("no module asset ") + Path);
				return;
			}
			FNiagaraExt_StackItemReference Ref(System, Emitter, ScriptName, After);
			FNiagaraExt_ModuleTopology Out;
			UNiagaraExternalEditUtilities::AddModule(Ref, Asset, Out, Ctx);
			if (Check(TEXT("AddModule ") + Path))
			{
				Line(FString::Printf(TEXT("module %s added to %s.%s"), *Out.ModuleName.ToString(), *Emitter.ToString(), *ScriptName.ToString()));
			}
		}

		void SetEmitterJson(FName Emitter, const FString& Json)
		{
			if (!bOk)
			{
				return;
			}
			FNiagaraExt_StackItemReference Ref(System, Emitter);
			FNiagaraExt_EmitterData Data;
			Data.PropertyValues = Json;
			UNiagaraExternalEditUtilities::SetEmitterData(Ref, Data, Ctx);
			Check(FString::Printf(TEXT("SetEmitterData %s %s"), *Emitter.ToString(), *Json));
		}

		void SetRendererJson(FName Emitter, int32 Renderer, const FString& Json)
		{
			if (!bOk)
			{
				return;
			}
			FNiagaraExt_StackItemReference Ref(System, Emitter);
			Ref.RendererIndex = Renderer;
			FNiagaraExt_RendererData Data;
			Data.PropertyValues = Json;
			UNiagaraExternalEditUtilities::SetRendererData(Ref, Data, Ctx);
			Check(FString::Printf(TEXT("SetRendererData %s %s"), *Emitter.ToString(), *Json));
		}

		template <typename T>
		void AddUser(const TCHAR* Name, const FNiagaraTypeDefinition& Type, const T& Value)
		{
			if (!bOk)
			{
				return;
			}
			FNiagaraExt_UserVariable V;
			V.Name = FName(Name);
			V.Type = Type;
			V.DefaultValue.Set(Type, FNiagaraVariant(&Value, sizeof(T)));
			if (!V.DefaultValue.IsValid())
			{
				Fail(FString::Printf(TEXT("User parameter %s: the default did not initialise"), Name));
				return;
			}
			UNiagaraExternalEditUtilities::AddUserVariable(System, V, Ctx);
			Check(FString::Printf(TEXT("AddUserVariable %s"), Name));
		}

		FName AddEmitter(const FString& TemplatePath, FName Name)
		{
			if (!bOk)
			{
				return NAME_None;
			}
			UNiagaraEmitter* Template = LoadObject<UNiagaraEmitter>(nullptr, *TemplatePath);
			if (!Template)
			{
				Fail(TEXT("no template emitter ") + TemplatePath);
				return NAME_None;
			}
			FNiagaraExt_EmitterTopology T;
			UNiagaraExternalEditUtilities::AddEmitter(Template, Name, T, Ctx);
			if (!Check(TEXT("AddEmitter ") + Name.ToString()))
			{
				return NAME_None;
			}
			if (T.EmitterName != Name)
			{
				Fail(FString::Printf(TEXT("AddEmitter: asked %s, got %s"), *Name.ToString(), *T.EmitterName.ToString()));
				return NAME_None;
			}
			return T.EmitterName;
		}

		bool Create(const FString& Path, const FString& Name)
		{
			System = UNiagaraExternalEditUtilities::CreateNiagaraSystem(Name, Path, nullptr, Ctx);
			if (!Check(TEXT("CreateNiagaraSystem")) || !System)
			{
				return Fail(TEXT("CreateNiagaraSystem returned null"));
			}
			Ctx = FNiagaraExternalEditContext(System);
			return true;
		}

		void Describe(FName Emitter)
		{
			FNiagaraExt_EmitterTopology T;
			if (!Topology(Emitter, T))
			{
				return;
			}
			for (const FNiagaraExt_ScriptStackTopology* S : { &T.EmitterSpawnScript, &T.EmitterUpdateScript, &T.ParticleSpawnScript, &T.ParticleUpdateScript })
			{
				for (const FNiagaraExt_ModuleTopology& M : S->Modules)
				{
					Line(FString::Printf(TEXT("MODULE %s / %s"), *S->ScriptName.ToString(), *M.ModuleName.ToString()));
					for (const FNiagaraExt_StackInputTopology& I : M.Inputs)
					{
						FString Enum;
						if (UEnum* E = I.Type.GetEnum())
						{
							for (int32 K = 0; K < E->NumEnums() - 1; ++K)
							{
								Enum += E->GetDisplayNameTextByIndex(K).ToString() + TEXT("/");
							}
						}
						Line(FString::Printf(TEXT("  IN '%s' %s%s%s%s %s"), *I.Name.ToString(), *I.Type.GetName(), I.bIsStaticSwitch ? TEXT(" SWITCH") : TEXT(""),
							I.bIsVisible ? TEXT("") : TEXT(" hidden"), I.bIsEditable ? TEXT("") : TEXT(" readonly"), *Enum));
					}
				}
			}
			FNiagaraExt_StackItemReference ERef(System, Emitter);
			FNiagaraExt_EmitterData ED;
			UNiagaraExternalEditUtilities::GetEmitterData(ERef, ED, Ctx);
			Line(TEXT("EMITTER JSON ") + ED.PropertyValues.Left(4000));
			for (const FNiagaraExt_RendererRef& R : T.Renderers)
			{
				FNiagaraExt_StackItemReference RRef(System, Emitter);
				RRef.RendererIndex = R.RendererIndex;
				FNiagaraExt_RendererData RD;
				UNiagaraExternalEditUtilities::GetRendererData(RRef, RD, Ctx);
				Line(FString::Printf(TEXT("RENDERER %d JSON %s"), R.RendererIndex, *RD.PropertyValues.Left(4000)));
			}
			Check(TEXT("describe"));
		}

		void Compile()
		{
			System->RequestCompile(false);
			System->WaitForCompilationComplete(true, false);
			FNiagaraExt_SystemCompileState State;
			UNiagaraExternalEditUtilities::GetSystemCompileState(System, State, Ctx);
			Check(TEXT("GetSystemCompileState"));
			for (const FNiagaraExt_ScriptCompileInfo& S : State.Scripts)
			{
				for (const FNiagaraExt_CompileEvent& Ev : S.CompileEvents)
				{
					if (Ev.Severity != ENiagaraExt_CompileEventSeverity::Log)
					{
						Line(FString::Printf(TEXT("compile event %s.%s: %s"), *S.EmitterName.ToString(), *S.ScriptName.ToString(), *Ev.Message.Left(400)));
					}
				}
			}
			Line(FString::Printf(TEXT("compiled: valid %d ready %d errors %d warnings %d"), System->IsValid() ? 1 : 0, System->IsReadyToRun() ? 1 : 0,
				State.bHasErrors ? 1 : 0, State.bHasWarnings ? 1 : 0));
			if (!System->IsValid() || !System->IsReadyToRun() || State.bHasErrors)
			{
				Fail(TEXT("the system did not compile valid"));
			}
			System->MarkPackageDirty();
		}
	};
}

FString UGTNiagaraSetupLibrary::DescribeEmitterTemplate(const FString& AssetPath, const FString& AssetName, const FString& TemplateEmitter, const TArray<FString>& ExtraModules)
{
	GTNiagaraSetup::FBuild B;
	if (!B.Create(AssetPath, AssetName))
	{
		return B.Log;
	}
	const FName E = B.AddEmitter(TemplateEmitter, FName(TEXT("Probe")));
	for (const FString& Spec : ExtraModules)
	{
		TArray<FString> Parts;
		Spec.ParseIntoArray(Parts, TEXT("|"), false);
		if (Parts.Num() == 3)
		{
			B.AddModule(E, FName(*Parts[0]), Parts[1], Parts[2].IsEmpty() ? NAME_None : FName(*Parts[2]));
		}
	}
	B.Describe(E);
	return B.Log;
}

namespace GTNiagaraSetup
{
	static const FName EUpd(TEXT("EmitterUpdateScript"));
	static const FName PSpawn(TEXT("ParticleSpawnScript"));
	static const FName PUpd(TEXT("ParticleUpdateScript"));
	static const TCHAR* Fountain = TEXT("/Niagara/DefaultAssets/Templates/Emitters/Fountain.Fountain");
	static const TCHAR* CollisionModule = TEXT("/Niagara/Modules/Collision/Collision.Collision");
	static const TCHAR* ScaleSizeModule = TEXT("/Niagara/Modules/Update/Size/ScaleSpriteSize.ScaleSpriteSize");

	/** One sprite emitter's numbers (docs/WHEEL_SPRAY_PLAN.md P2 item 2). */
	struct FSprite
	{
		FName Name;
		const TCHAR* Rate;
		bool bGpu;
		float LifeMin, LifeMax;
		FString Size;          // Uniform Sprite Size, an HLSL expression (cm)
		float Radius;          // ShapeLocation sphere, cm
		float ConeDeg;
		FString Speed;         // Velocity Speed, an HLSL expression
		FVector3f Gravity;
		float Drag;
		UMaterialInterface* Material;
	};

	static void SpriteEmitter(FBuild& B, const FSprite& S)
	{
		const FName E = B.AddEmitter(Fountain, S.Name);
		if (!B.bOk)
		{
			return;
		}
		if (S.bGpu)
		{
			// GPU (depth-buffer collision), fixed bounds round the wheel's component: world-space particles left up to 25 m behind.
			B.SetEmitterJson(E, TEXT("{\"SimTarget\":\"GPUComputeSim\",\"CalculateBoundsMode\":\"Fixed\",\"FixedBounds\":{\"min\":{\"x\":-2500,\"y\":-2500,\"z\":-500},\"max\":{\"x\":2500,\"y\":2500,\"z\":1500},\"isValid\":true}}"));
		}
		B.Link(E, EUpd, TEXT("SpawnRate"), TEXT("SpawnRate"), S.Rate, FNiagaraTypeDefinition::GetFloatDef());
		const FName Init(TEXT("InitializeParticle"));
		B.SetEnum(E, PSpawn, Init, TEXT("Lifetime Mode"), TEXT("Random"));
		B.SetFloat(E, PSpawn, Init, TEXT("Lifetime Min"), S.LifeMin);
		B.SetFloat(E, PSpawn, Init, TEXT("Lifetime Max"), S.LifeMax);
		B.SetBool(E, PSpawn, Init, TEXT("Write Material Random"), true, false);
		B.Expr(E, PSpawn, Init, TEXT("Material Random"), FNiagaraTypeDefinition::GetFloatDef(), TEXT("rand(1.0f)"));
		B.SetEnum(E, PSpawn, Init, TEXT("Sprite Size Mode"), TEXT("Uniform"));
		B.Expr(E, PSpawn, Init, TEXT("Uniform Sprite Size"), FNiagaraTypeDefinition::GetFloatDef(), S.Size);
		B.SetEnum(E, PSpawn, Init, TEXT("Sprite Rotation Mode"), TEXT("Random"));
		const FName Shape(TEXT("ShapeLocation"));
		B.SetEnum(E, PSpawn, Shape, TEXT("Shape Primitive"), TEXT("Sphere"));
		B.SetFloat(E, PSpawn, Shape, TEXT("Sphere Radius"), S.Radius);
		const FName Vel(TEXT("AddVelocity"));
		B.SetEnum(E, PSpawn, Vel, TEXT("Velocity Mode"), TEXT("In Cone"));
		B.SetEnum(E, PSpawn, Vel, TEXT("Rotation Mode"), TEXT("None"));
		B.Expr(E, PSpawn, Vel, TEXT("Cone Axis"), FNiagaraTypeDefinition::GetVec3Def(), TEXT("normalize(User.BaseVelocity + float3(0.0f, 0.0f, 0.001f))"));
		B.SetFloat(E, PSpawn, Vel, TEXT("Cone Angle"), S.ConeDeg);
		B.Expr(E, PSpawn, Vel, TEXT("Velocity Speed"), FNiagaraTypeDefinition::GetFloatDef(), S.Speed);
		B.SetVec3(E, PUpd, TEXT("GravityForce"), TEXT("Gravity"), S.Gravity);
		B.SetBool(E, PUpd, TEXT("Drag"), TEXT("Use Linear Drag"), true, false);
		B.SetFloat(E, PUpd, TEXT("Drag"), TEXT("Drag"), S.Drag);
		// The template's colour-over-life is off: the tint is the User colour, the dust's fade is its material's.
		if (B.Guard(E, PUpd, TEXT("ScaleColor"), TEXT("Scale Mode"), FNiagaraTypeDefinition(), true))
		{
			FNiagaraExt_StackItemReference Ref(B.System, E, PUpd, FName(TEXT("ScaleColor")));
			UNiagaraExternalEditUtilities::SetModuleEnabled(Ref, false, B.Ctx);
			B.Check(TEXT("SetModuleEnabled ScaleColor"));
		}
		if (S.Material)
		{
			B.SetRendererJson(E, 0, FString::Printf(TEXT("{\"Material\":\"%s\"}"), *S.Material->GetPathName()));
		}
		B.Line(FString::Printf(TEXT("emitter %s %s"), *E.ToString(), B.bOk ? TEXT("set") : TEXT("STOPPED")));
	}
}

/** The build, for the emitters in Mask (1 MudDroplets, 2 GravelGrit, 4 GravelDust). */
static FString BuildSprayMasked(const FString& AssetPath, const FString& AssetName, UMaterialInterface* MudMaterial,
	UMaterialInterface* GritMaterial, UMaterialInterface* DustMaterial, uint32 Mask)
{
	using namespace GTNiagaraSetup;
	FBuild B;
	if (!B.Create(AssetPath, AssetName))
	{
		return B.Log;
	}
	const bool bMud = (Mask & 1) != 0, bGrit = (Mask & 2) != 0, bDust = (Mask & 4) != 0;
	// User parameters (P2 item 2). UGTSprayComponent sets them per wheel every tick; these defaults are a still system
	// in the ground's palette (Art/Export/WheelSpray/manifest.json palette_linear).
	const FNiagaraTypeDefinition& F = FNiagaraTypeDefinition::GetFloatDef();
	const FNiagaraTypeDefinition& C = FNiagaraTypeDefinition::GetColorDef();
	B.AddUser(TEXT("User.MudRate"), F, 0.f);
	B.AddUser(TEXT("User.GritRate"), F, 0.f);
	B.AddUser(TEXT("User.DustRate"), F, 0.f);
	B.AddUser(TEXT("User.BaseVelocity"), FNiagaraTypeDefinition::GetVec3Def(), FVector3f(0.f, 0.f, 200.f));
	B.AddUser(TEXT("User.MudTint"), C, FLinearColor(0.0564f, 0.0321f, 0.0149f, 1.f));
	B.AddUser(TEXT("User.GritTintA"), C, FLinearColor(0.1582f, 0.1844f, 0.1933f, 1.f));
	B.AddUser(TEXT("User.GritTintB"), C, FLinearColor(0.2941f, 0.2933f, 0.2617f, 1.f));
	B.AddUser(TEXT("User.DustTint"), C, FLinearColor(0.2193f, 0.2292f, 0.2113f, 1.f));
	B.AddUser(TEXT("User.SizeScale"), F, 1.f);
	B.AddUser(TEXT("User.GritSizeMin"), F, 1.f);    // Benmore B1c: the grit's size range, cm (UGTSprayComponent: 1.5 + 2.5 on a gravel surface)
	B.AddUser(TEXT("User.GritSizeSpan"), F, 2.f);
	B.AddUser(TEXT("User.ClumpSeed"), F, 1.f);   // P2d: per wheel (UGTSprayComponent), so two wheels' clumps differ

	// MudDroplets: 2-8 cm (power law; P2c, P2 1-6), gravity 980, drag 0.3, 0.6-1.4 s, killed on the depth buffer. P2d, a rooster
	// tail: the droplets leave in clumps of about ten (MudRate / 10 clumps a second: those born in one clump's window share its
	// velocity) - BaseVelocity with its upward part x1.3 (P2c), the clump's direction within 15 deg of it and its speed +-20 %, each
	// droplet +-8 % (a 4.6 deg cone, its speed x0.92-1.08) - and the speed capped so the upward launch is at most 700 cm/s.
	const TCHAR* Spread = TEXT("length(User.BaseVelocity) * (0.6f + 0.8f * rand(1.0f))");
	if (bMud) SpriteEmitter(B, { FName(TEXT("MudDroplets")), TEXT("User.MudRate"), true, 0.6f, 1.4f,
		TEXT("User.SizeScale * (2.0f + 6.0f * pow(rand(1.0f), 2.5f))"), 6.f, 35.f, Spread, FVector3f(0.f, 0.f, -980.f), 0.3f, MudMaterial });
	if (bMud)
	{
		// The clump: K counts MudRate / 10 windows a second (Emitter.Age); its hashes H1-H4 are shared by the droplets born in it.
		const FString K = TEXT("floor(Emitter.Age * max(User.MudRate, 1.0f) * 0.1f)");
		auto Hash = [&K](const TCHAR* A, const TCHAR* B, const TCHAR* C)
		{
			return FString::Printf(TEXT("frac(sin(%s * %s + User.ClumpSeed * %s) * %s)"), *K, A, B, C);
		};
		const FString V = TEXT("(User.BaseVelocity * float3(1.0f, 1.0f, 1.3f))");
		const FString A0 = FString::Printf(TEXT("normalize(%s + float3(0.0f, 0.0f, 0.001f))"), *V);
		const FString U = FString::Printf(TEXT("(float3(%s, %s, %s) * 2.0f - 1.0f)"), *Hash(TEXT("12.9898f"), TEXT("78.233f"), TEXT("43758.5453f")),
			*Hash(TEXT("39.3468f"), TEXT("11.135f"), TEXT("24634.6345f")), *Hash(TEXT("73.156f"), TEXT("52.235f"), TEXT("96321.854f")));
		// tan 15 deg x the part of U across the axis, |U| at most sqrt 3: the clump's direction within 15 deg.
		const FString Dir = FString::Printf(TEXT("normalize(%s + 0.268f * 0.577f * (%s - dot(%s, %s) * %s))"), *A0, *U, *U, *A0, *A0);
		const FString Speed = FString::Printf(TEXT("min(length(%s) * (0.8f + 0.4f * %s) * (0.92f + 0.16f * rand(1.0f)), 700.0f / max((%s).z, 0.05f))"),
			*V, *Hash(TEXT("27.619f"), TEXT("63.761f"), TEXT("51729.38f")), *Dir);
		const FName Vel(TEXT("AddVelocity"));
		B.Expr(FName(TEXT("MudDroplets")), PSpawn, Vel, TEXT("Cone Axis"), FNiagaraTypeDefinition::GetVec3Def(), Dir);
		B.SetFloat(FName(TEXT("MudDroplets")), PSpawn, Vel, TEXT("Cone Angle"), 4.6f);
		B.Expr(FName(TEXT("MudDroplets")), PSpawn, Vel, TEXT("Velocity Speed"), FNiagaraTypeDefinition::GetFloatDef(), Speed);
	}
	// GravelGrit: 1-3 cm (P2b; P2 0.5-2; Benmore B1c: GritSizeMin + GritSizeSpan, 1 + 2 by default), one bounce (restitution 0.3) and then death, 0.8-1.5 s. Its colour is the material's lerp of the two
	// stone tints (the User colours reach it as the particle colour, GritTintA, and the random range's other end, GritTintB).
	if (bGrit) SpriteEmitter(B, { FName(TEXT("GravelGrit")), TEXT("User.GritRate"), true, 0.8f, 1.5f,
		TEXT("User.SizeScale * (User.GritSizeMin + User.GritSizeSpan * pow(rand(1.0f), 2.5f))"), 8.f, 40.f, Spread, FVector3f(0.f, 0.f, -980.f), 0.3f, GritMaterial });
	// GravelDust: 60-200 cm (P2b; P2 30-120) growing x2.5, drag 1.5, rising about 20 cm/s (a 30 cm/s2 lift over drag 1.5), 1.5-3 s, CPU (no collision).
	if (bDust) SpriteEmitter(B, { FName(TEXT("GravelDust")), TEXT("User.DustRate"), false, 1.5f, 3.0f,
		TEXT("User.SizeScale * (60.0f + 140.0f * pow(rand(1.0f), 2.0f))"), 20.f, 60.f, TEXT("length(User.BaseVelocity) * 0.25f * (0.6f + 0.8f * rand(1.0f))"),
		FVector3f(0.f, 0.f, 30.f), 1.5f, DustMaterial });

	// Colours: mud and dust straight from their User tint; grit a random point between its two tints, per particle.
	const FName Init(TEXT("InitializeParticle"));
	if (bMud)
	{
		B.SetEnum(FName(TEXT("MudDroplets")), PSpawn, Init, TEXT("Color Mode"), TEXT("Direct Set"));
		B.Link(FName(TEXT("MudDroplets")), PSpawn, Init, TEXT("Color"), TEXT("User.MudTint"), C);
	}
	if (bDust)
	{
		B.SetEnum(FName(TEXT("GravelDust")), PSpawn, Init, TEXT("Color Mode"), TEXT("Direct Set"));
		B.Link(FName(TEXT("GravelDust")), PSpawn, Init, TEXT("Color"), TEXT("User.DustTint"), C);
	}
	if (bGrit)
	{
		B.SetEnum(FName(TEXT("GravelGrit")), PSpawn, Init, TEXT("Color Mode"), TEXT("Random Range"));
		B.SetEnum(FName(TEXT("GravelGrit")), PSpawn, Init, TEXT("Color Channel Mode"), TEXT("Link RGBA"));
		B.Link(FName(TEXT("GravelGrit")), PSpawn, Init, TEXT("Color Minimum"), TEXT("User.GritTintA"), C);
		B.Link(FName(TEXT("GravelGrit")), PSpawn, Init, TEXT("Color Maximum"), TEXT("User.GritTintB"), C);
	}

	// Collision on the depth buffer: mud dies at its first hit; grit bounces once (restitution 0.3) and dies at its second.
	for (const TCHAR* Name : { TEXT("MudDroplets"), TEXT("GravelGrit") })
	{
		const FName E(Name);
		const bool bIsGrit = E == FName(TEXT("GravelGrit"));
		if (!(bIsGrit ? bGrit : bMud))
		{
			continue;
		}
		B.AddModule(E, PUpd, CollisionModule, FName(TEXT("SolveForcesAndVelocity")));
		const FName Col(TEXT("Collision"));
		B.SetEnum(E, PUpd, Col, TEXT("GPU Collision Type"), TEXT("GPU Depth Buffer"));
		// P2b: a droplet hidden from the camera (behind the tyre, under the bumper) or off the screen lives its life; only a hit kills.
		B.SetBool(E, PUpd, Col, TEXT("Kill Occluded Particles"), false, false);
		B.SetBool(E, PUpd, Col, TEXT("Kill Offscreen Particles"), false, false);
		B.SetFloat(E, PUpd, Col, TEXT("Restitution"), bIsGrit ? 0.3f : 0.05f);
		B.SetBool(E, PUpd, Col, TEXT("KillOnCollision"), true, false);
		FNiagaraInt32 Hits;
		Hits.Value = bIsGrit ? 2 : 1;
		B.SetLocal(E, PUpd, Col, TEXT("Kill On Collision"), FNiagaraTypeDefinition::GetIntDef(), &Hits);
	}
	// The dust grows x2.5 over its life.
	const FName Dust(TEXT("GravelDust"));
	if (bDust)
	{
		B.AddModule(Dust, PUpd, ScaleSizeModule, FName(TEXT("Drag")));
		B.SetEnum(Dust, PUpd, FName(TEXT("ScaleSpriteSize")), TEXT("Scale Sprite Size Mode"), TEXT("Uniform"));
		B.Expr(Dust, PUpd, FName(TEXT("ScaleSpriteSize")), TEXT("Uniform Scale Factor"), FNiagaraTypeDefinition::GetFloatDef(), TEXT("1.0f + 1.5f * Particles.NormalizedAge"));
		B.SetRendererJson(Dust, 0, TEXT("{\"SortMode\":\"ViewDistance\"}"));
	}

	if (B.bOk)
	{
		B.Compile();
	}
	B.Line(B.bOk ? TEXT("BUILD OK") : TEXT("BUILD FAILED"));
	return B.Log;
}

FString UGTNiagaraSetupLibrary::BuildWheelSpray(const FString& AssetPath, const FString& AssetName, UMaterialInterface* MudMaterial,
	UMaterialInterface* GritMaterial, UMaterialInterface* DustMaterial)
{
	return BuildSprayMasked(AssetPath, AssetName, MudMaterial, GritMaterial, DustMaterial, 7);
}

namespace GTNiagaraSetup
{
	/** A template module switched off - only when the emitter's topology lists it in that script (else a FAIL, nothing written). */
	static void DisableModule(FBuild& B, FName Emitter, FName ScriptName, FName Module)
	{
		if (!B.bOk)
		{
			return;
		}
		FNiagaraExt_EmitterTopology T;
		if (!B.Topology(Emitter, T))
		{
			return;
		}
		const FNiagaraExt_ScriptStackTopology* S = FBuild::Script(T, ScriptName);
		if (!S || !S->Modules.FindByPredicate([&](const FNiagaraExt_ModuleTopology& X) { return X.ModuleName == Module; }))
		{
			B.Fail(FString::Printf(TEXT("guard: no module %s in %s.%s to switch off"), *Module.ToString(), *Emitter.ToString(), *ScriptName.ToString()));
			return;
		}
		FNiagaraExt_StackItemReference Ref(B.System, Emitter, ScriptName, Module);
		UNiagaraExternalEditUtilities::SetModuleEnabled(Ref, false, B.Ctx);
		if (B.Check(FString::Printf(TEXT("SetModuleEnabled %s off"), *Module.ToString())))
		{
			B.Line(FString::Printf(TEXT("  %s.%s.%s off"), *Emitter.ToString(), *ScriptName.ToString(), *Module.ToString()));
		}
	}
}

FString UGTNiagaraSetupLibrary::BuildWaterRings(const FString& AssetPath, const FString& AssetName, UMaterialInterface* RingMaterial)
{
	using namespace GTNiagaraSetup;
	FBuild B;
	if (!B.Create(AssetPath, AssetName))
	{
		return B.Log;
	}
	const FNiagaraTypeDefinition& F = FNiagaraTypeDefinition::GetFloatDef();
	// User parameters: UGTMudWaterSubsystem sets RingRate for the one step that spawns its rings (rings / step), RingScale 1.
	B.AddUser(TEXT("User.RingRate"), F, 0.f);
	B.AddUser(TEXT("User.RingScale"), F, 1.f);
	const FName E = B.AddEmitter(Fountain, FName(TEXT("WaterRings")));
	if (!B.bOk)
	{
		B.Line(TEXT("BUILD FAILED"));
		return B.Log;
	}
	// CPU (the template's): a few sprites, simulated with the scene rendered or not.
	B.Link(E, EUpd, TEXT("SpawnRate"), TEXT("SpawnRate"), TEXT("User.RingRate"), F);
	const FName Init(TEXT("InitializeParticle"));
	B.SetEnum(E, PSpawn, Init, TEXT("Lifetime Mode"), TEXT("Random"));
	B.SetFloat(E, PSpawn, Init, TEXT("Lifetime Min"), 1.2f);
	B.SetFloat(E, PSpawn, Init, TEXT("Lifetime Max"), 2.0f);
	B.SetBool(E, PSpawn, Init, TEXT("Write Material Random"), true, false);
	B.Expr(E, PSpawn, Init, TEXT("Material Random"), F, TEXT("rand(1.0f)"));
	B.SetEnum(E, PSpawn, Init, TEXT("Sprite Size Mode"), TEXT("Uniform"));
	// 10 cm (8-12) at birth; ScaleSpriteSize below takes it x12 (to 1.2 m), fast at first and slowing.
	B.Expr(E, PSpawn, Init, TEXT("Uniform Sprite Size"), F, TEXT("User.RingScale * (8.0f + 4.0f * rand(1.0f))"));
	B.SetEnum(E, PSpawn, Init, TEXT("Sprite Rotation Mode"), TEXT("Random"));
	// The rings stay where they were born: no shape offset, no launch, no gravity or drag; the template's colour fade off (the
	// material fades by the particle's age).
	DisableModule(B, E, PSpawn, FName(TEXT("ShapeLocation")));
	DisableModule(B, E, PSpawn, FName(TEXT("AddVelocity")));
	DisableModule(B, E, PUpd, FName(TEXT("GravityForce")));
	DisableModule(B, E, PUpd, FName(TEXT("Drag")));
	DisableModule(B, E, PUpd, FName(TEXT("ScaleColor")));
	// Flat on the water: Particles.SpriteFacing (0, 0, 1) from a SetParameters module after InitializeParticle; the renderer faces
	// the sprites along it (CustomFacingVector, Unaligned: the random rotation spins them in the water's plane).
	if (B.bOk)
	{
		FNiagaraExt_SetParameterEntry Facing;
		Facing.Variable.Name = FName(TEXT("Particles.SpriteFacing"));
		Facing.Variable.Type = FNiagaraTypeDefinition::GetVec3Def();
		const FVector3f Up(0.f, 0.f, 1.f);
		Facing.DefaultValue.Set(Facing.Variable.Type, FNiagaraVariant(&Up, sizeof(Up)));
		FNiagaraExt_StackItemReference Ref(B.System, E, PSpawn, Init);
		FNiagaraExt_ModuleTopology Out;
		UNiagaraExternalEditUtilities::AddSetParametersModule(Ref, { Facing }, Out, B.Ctx);
		if (B.Check(TEXT("AddSetParametersModule Particles.SpriteFacing")))
		{
			FString Inputs;
			for (const FNiagaraExt_StackInputTopology& I : Out.Inputs)
			{
				Inputs += FString::Printf(TEXT("'%s' %s; "), *I.Name.ToString(), *I.Type.GetName());
			}
			B.Line(FString::Printf(TEXT("module %s added to %s.ParticleSpawnScript (set-parameters %d): %s"), *Out.ModuleName.ToString(), *E.ToString(),
				Out.bIsSetParametersModule ? 1 : 0, *Inputs));
			// The value again through the guard, on the input the topology names (the entry's default may not carry over).
			const FNiagaraExt_StackInputTopology* In = Out.Inputs.FindByPredicate([](const FNiagaraExt_StackInputTopology& X) { return X.Name.ToString().Contains(TEXT("SpriteFacing")); });
			if (In)
			{
				B.SetVec3(E, PSpawn, Out.ModuleName, In->Name, Up);
			}
			else
			{
				B.Fail(TEXT("guard: the SetParameters module shows no SpriteFacing input"));
			}
		}
	}
	// Growth: x1 to x12 over the life, eased out (a ring slows as it spreads).
	B.AddModule(E, PUpd, ScaleSizeModule, FName(TEXT("Drag")));
	B.SetEnum(E, PUpd, FName(TEXT("ScaleSpriteSize")), TEXT("Scale Sprite Size Mode"), TEXT("Uniform"));
	B.Expr(E, PUpd, FName(TEXT("ScaleSpriteSize")), TEXT("Uniform Scale Factor"), F,
		TEXT("1.0f + 11.0f * (1.0f - (1.0f - Particles.NormalizedAge) * (1.0f - Particles.NormalizedAge))"));
	if (RingMaterial)
	{
		B.SetRendererJson(E, 0, FString::Printf(TEXT("{\"Material\":\"%s\",\"FacingMode\":\"CustomFacingVector\",\"Alignment\":\"Unaligned\"}"), *RingMaterial->GetPathName()));
	}
	if (B.bOk)
	{
		B.Describe(E);
		B.Compile();
	}
	B.Line(B.bOk ? TEXT("BUILD OK") : TEXT("BUILD FAILED"));
	return B.Log;
}
