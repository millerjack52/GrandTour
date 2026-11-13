// Isolated DustLab authoring. Guard helper copied from GTNiagaraSetupLibrary so the
// shared spray builder remains untouched during concurrent Benmore work.
#include "FX/GTDustLabSetupLibrary.h"

#include "NiagaraExternalSystemEditorUtilities.h"
#include "NiagaraSystem.h"
#include "NiagaraEmitter.h"
#include "NiagaraEmitterHandle.h"
#include "NiagaraTypes.h"
#include "NiagaraVariant.h"
#include "Materials/MaterialInterface.h"

namespace GTDustLabSetup
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

FString UGTDustLabSetupLibrary::BuildMudFlick(const FString& AssetPath, const FString& AssetName, UMaterialInterface* Material)
{
    using namespace GTDustLabSetup;
    FBuild B;
    if (!AssetPath.StartsWith(TEXT("/Game/GrandTour/ArtTests/DustLab/")) || !Material) return TEXT("FAIL private path and material required");
    if (!B.Create(AssetPath,AssetName)) return B.Log;
    const auto& F=FNiagaraTypeDefinition::GetFloatDef();
    const auto& V=FNiagaraTypeDefinition::GetVec3Def();
    const auto& C=FNiagaraTypeDefinition::GetColorDef();
    B.AddUser(TEXT("User.MudRate"),F,0.f);
    B.AddUser(TEXT("User.BaseVelocity"),V,FVector3f(0,0,300));
    B.AddUser(TEXT("User.MudTint"),C,FLinearColor(0.12f,0.07f,0.035f));
    const FName EU(TEXT("EmitterUpdateScript")),PS(TEXT("ParticleSpawnScript")),PU(TEXT("ParticleUpdateScript")),Init(TEXT("InitializeParticle"));
    for (int32 Layer=0; Layer<2; ++Layer)
    {
        const FName E=B.AddEmitter(TEXT("/Niagara/DefaultAssets/Templates/Emitters/Fountain.Fountain"),Layer?TEXT("FineSpatter"):TEXT("MudFlecks"));
        if (!B.bOk) break;
        B.SetEmitterJson(E,TEXT("{\"bLocalSpace\":false,\"SimTarget\":\"CPUSim\",\"CalculateBoundsMode\":\"Dynamic\"}"));
        B.Expr(E,EU,TEXT("SpawnRate"),TEXT("SpawnRate"),F,Layer?TEXT("User.MudRate * 0.65f"):TEXT("User.MudRate"));
        B.SetEnum(E,PS,Init,TEXT("Lifetime Mode"),TEXT("Random"));
        B.SetFloat(E,PS,Init,TEXT("Lifetime Min"),0.65f);
        B.SetFloat(E,PS,Init,TEXT("Lifetime Max"),1.6f);
        B.SetBool(E,PS,Init,TEXT("Write Material Random"),true,false);
        B.Expr(E,PS,Init,TEXT("Material Random"),F,TEXT("rand(1.0f)"));
        B.SetEnum(E,PS,Init,TEXT("Sprite Size Mode"),TEXT("Uniform"));
        B.Expr(E,PS,Init,TEXT("Uniform Sprite Size"),F,Layer?TEXT("1.5f + 3.0f * rand(1.0f)"):TEXT("3.5f + 8.5f * pow(rand(1.0f),2.0f)"));
        B.SetEnum(E,PS,Init,TEXT("Sprite Rotation Mode"),TEXT("Random"));
        B.SetEnum(E,PS,Init,TEXT("Color Mode"),TEXT("Direct Set"));
        B.Expr(E,PS,Init,TEXT("Color"),C,TEXT("float4(User.MudTint.rgb*(0.8f+0.4f*rand(1.0f)),1.0f)"));
        B.SetEnum(E,PS,TEXT("ShapeLocation"),TEXT("Shape Primitive"),TEXT("Sphere"));
        B.SetFloat(E,PS,TEXT("ShapeLocation"),TEXT("Sphere Radius"),8.f);
        B.SetEnum(E,PS,TEXT("AddVelocity"),TEXT("Velocity Mode"),TEXT("In Cone"));
        B.SetEnum(E,PS,TEXT("AddVelocity"),TEXT("Rotation Mode"),TEXT("None"));
        B.Expr(E,PS,TEXT("AddVelocity"),TEXT("Cone Axis"),V,TEXT("normalize(User.BaseVelocity+float3(0,0,0.001f))"));
        B.SetFloat(E,PS,TEXT("AddVelocity"),TEXT("Cone Angle"),Layer?22.f:14.f);
        B.Expr(E,PS,TEXT("AddVelocity"),TEXT("Velocity Speed"),F,TEXT("length(User.BaseVelocity)*(0.55f+0.7f*rand(1.0f))"));
        B.SetVec3(E,PU,TEXT("GravityForce"),TEXT("Gravity"),FVector3f(0,0,-980));
        B.SetBool(E,PU,TEXT("Drag"),TEXT("Use Linear Drag"),true,false);
        B.SetFloat(E,PU,TEXT("Drag"),TEXT("Drag"),Layer?0.65f:0.22f);
        if (B.Guard(E,PU,TEXT("ScaleColor"),TEXT("Scale Mode"),FNiagaraTypeDefinition(),true))
        {
            FNiagaraExt_StackItemReference Ref(B.System,E,PU,TEXT("ScaleColor"));
            UNiagaraExternalEditUtilities::SetModuleEnabled(Ref,false,B.Ctx); B.Check(TEXT("disable ScaleColor"));
        }
        // CPU scene traces keep collision independent of the camera's depth buffer.
        B.AddModule(E,PU,TEXT("/Niagara/Modules/Collision/Collision.Collision"),TEXT("SolveForcesAndVelocity"));
        B.SetFloat(E,PU,TEXT("Collision"),TEXT("Restitution"),0.f);
        B.SetBool(E,PU,TEXT("Collision"),TEXT("KillOnCollision"),true,false);
        FNiagaraInt32 Hits; Hits.Value=1;
        B.SetLocal(E,PU,TEXT("Collision"),TEXT("Kill On Collision"),FNiagaraTypeDefinition::GetIntDef(),&Hits);
        B.SetRendererJson(E,0,FString::Printf(TEXT("{\"Material\":\"%s\",\"SortMode\":\"None\"}"),*Material->GetPathName()));
    }
    if (B.bOk) B.Compile();
    B.Line(B.bOk?TEXT("BUILD OK"):TEXT("BUILD FAILED"));
    return B.Log;
}

FString UGTDustLabSetupLibrary::BuildDust(const FString& AssetPath, const FString& AssetName, UMaterialInterface* Material)
{
    using namespace GTDustLabSetup;
    FBuild B;
    if (!AssetPath.StartsWith(TEXT("/Game/GrandTour/ArtTests/DustLab/"))) return TEXT("FAIL DustLab path required");
    if (!Material) return TEXT("FAIL DustLab material required");
    if (!B.Create(AssetPath, AssetName)) return B.Log;
    const auto& F = FNiagaraTypeDefinition::GetFloatDef();
    const auto& V = FNiagaraTypeDefinition::GetVec3Def();
    const auto& C = FNiagaraTypeDefinition::GetColorDef();
    B.AddUser(TEXT("User.ContactRate"), F, 0.f);
    B.AddUser(TEXT("User.WakeRate"), F, 0.f);
    B.AddUser(TEXT("User.TrailRate"), F, 0.f);
    B.AddUser(TEXT("User.BaseVelocity"), V, FVector3f(0, 0, 95));
    B.AddUser(TEXT("User.Wind"), V, FVector3f::ZeroVector);
    B.AddUser(TEXT("User.DustTint"), C, FLinearColor(0.29f, 0.27f, 0.22f));
    struct FLayer { const TCHAR* Name; const TCHAR* Rate; float LifeMin, LifeMax, Radius, Drag, Lift, Speed, Alpha; const TCHAR* Size; const TCHAR* Growth; };
    const FLayer Layers[] = {
        {TEXT("ContactDust"), TEXT("User.ContactRate"), 0.6f, 1.3f, 8.f, 2.5f, 12.f, 1.f, 0.75f,
            TEXT("22.0f + 40.0f * pow(rand(1.0f), 1.7f)"), TEXT("1.0f + 1.4f * Particles.NormalizedAge")},
        {TEXT("NearWake"), TEXT("User.WakeRate"), 3.5f, 6.f, 25.f, 1.1f, 30.f, 0.75f, 0.65f,
            TEXT("110.0f + 110.0f * pow(rand(1.0f), 1.8f)"), TEXT("1.0f + 2.2f * Particles.NormalizedAge")},
        {TEXT("LingeringTrail"), TEXT("User.TrailRate"), 7.f, 12.f, 30.f, 0.45f, 16.f, 0.4f, 0.4f,
            TEXT("160.0f + 160.0f * pow(rand(1.0f), 1.5f)"), TEXT("1.0f + 2.8f * Particles.NormalizedAge")}
    };
    const FName EU(TEXT("EmitterUpdateScript")), PS(TEXT("ParticleSpawnScript")), PU(TEXT("ParticleUpdateScript")), Init(TEXT("InitializeParticle"));
    for (const FLayer& L : Layers)
    {
        const FName E = B.AddEmitter(TEXT("/Niagara/DefaultAssets/Templates/Emitters/Fountain.Fountain"), FName(L.Name));
        if (!B.bOk) break;
        // CPU simulation here gives particle-derived bounds for the long world-space tail.
        // The population is bounded by the driver's capped rates and finite lifetimes.
        B.SetEmitterJson(E, TEXT("{\"bLocalSpace\":false,\"SimTarget\":\"CPUSim\",\"CalculateBoundsMode\":\"Dynamic\"}"));
        B.Link(E, EU, TEXT("SpawnRate"), TEXT("SpawnRate"), L.Rate, F);
        B.SetEnum(E, PS, Init, TEXT("Lifetime Mode"), TEXT("Random"));
        B.SetFloat(E, PS, Init, TEXT("Lifetime Min"), L.LifeMin);
        B.SetFloat(E, PS, Init, TEXT("Lifetime Max"), L.LifeMax);
        B.SetBool(E, PS, Init, TEXT("Write Material Random"), true, false);
        B.Expr(E, PS, Init, TEXT("Material Random"), F, TEXT("rand(1.0f)"));
        B.SetEnum(E, PS, Init, TEXT("Sprite Size Mode"), TEXT("Uniform"));
        B.Expr(E, PS, Init, TEXT("Uniform Sprite Size"), F, L.Size);
        B.SetEnum(E, PS, Init, TEXT("Sprite Rotation Mode"), TEXT("Random"));
        B.SetEnum(E, PS, Init, TEXT("Color Mode"), TEXT("Direct Set"));
        B.Expr(E, PS, Init, TEXT("Color"), C, FString::Printf(TEXT("float4(User.DustTint.rgb * (0.9f + 0.2f * rand(1.0f)), %ff)"), L.Alpha));
        B.SetEnum(E, PS, TEXT("ShapeLocation"), TEXT("Shape Primitive"), TEXT("Sphere"));
        B.SetFloat(E, PS, TEXT("ShapeLocation"), TEXT("Sphere Radius"), L.Radius);
        B.SetEnum(E, PS, TEXT("AddVelocity"), TEXT("Velocity Mode"), TEXT("In Cone"));
        B.SetEnum(E, PS, TEXT("AddVelocity"), TEXT("Rotation Mode"), TEXT("None"));
        B.Expr(E, PS, TEXT("AddVelocity"), TEXT("Cone Axis"), V, TEXT("normalize(User.BaseVelocity + float3(0.0f,0.0f,0.001f))"));
        B.SetFloat(E, PS, TEXT("AddVelocity"), TEXT("Cone Angle"), 38.f);
        B.Expr(E, PS, TEXT("AddVelocity"), TEXT("Velocity Speed"), F, FString::Printf(TEXT("length(User.BaseVelocity) * %ff * (0.6f + 0.8f * rand(1.0f))"), L.Speed));
        B.Expr(E, PU, TEXT("GravityForce"), TEXT("Gravity"), V, FString::Printf(TEXT("User.Wind * %ff + float3(0.0f,0.0f,%ff)"), L.Drag, L.Lift));
        B.SetBool(E, PU, TEXT("Drag"), TEXT("Use Linear Drag"), true, false);
        B.SetFloat(E, PU, TEXT("Drag"), TEXT("Drag"), L.Drag);
        if (B.Guard(E, PU, TEXT("ScaleColor"), TEXT("Scale Mode"), FNiagaraTypeDefinition(), true))
        {
            FNiagaraExt_StackItemReference ColorRef(B.System, E, PU, TEXT("ScaleColor"));
            UNiagaraExternalEditUtilities::SetModuleEnabled(ColorRef, false, B.Ctx);
            B.Check(TEXT("disable template ScaleColor"));
        }
        B.AddModule(E, PU, TEXT("/Niagara/Modules/Update/Size/ScaleSpriteSize.ScaleSpriteSize"), TEXT("Drag"));
        B.SetEnum(E, PU, TEXT("ScaleSpriteSize"), TEXT("Scale Sprite Size Mode"), TEXT("Uniform"));
        B.Expr(E, PU, TEXT("ScaleSpriteSize"), TEXT("Uniform Scale Factor"), F, L.Growth);
        B.SetRendererJson(E, 0, FString::Printf(TEXT("{\"Material\":\"%s\",\"SortMode\":\"ViewDistance\"}"), *Material->GetPathName()));
    }
    if (B.bOk) B.Compile();
    B.Line(B.bOk ? TEXT("BUILD OK") : TEXT("BUILD FAILED"));
    return B.Log;
}


