# OWGameUE dependency closure - Phase 0 survey

- report ok: **True**; script wall time 2.0s; steps failed: none
- closure: **332 packages, 1117.4 MB**; first-discovery edges {'root': 90, 'hard': 196, 'soft': 46}
- packages with no .uasset/.umap on disk: 0; not in registry: 0
- STYLIZED_COZY_TREES_LICENSE.txt present: True

## Roots per rule
| rule | assets | pkgs | classes / note |
|---|---|---|---|
| DL/M_OWDressingLab | 1 | 1 | Material x1 |
| DL/MI_OWDressingLab_Style | 1 | 1 | MaterialInstanceConstant x1 |
| DL/Masters/** (recursive) | 2 | 2 | Material x2 |
| DL/OW_Meadow_LayerInfo | 1 | 1 | LandscapeLayerInfoObject x1 |
| DL/OW_Forest_LayerInfo | 1 | 1 | LandscapeLayerInfoObject x1 |
| DL/OW_Scree_LayerInfo | 1 | 1 | LandscapeLayerInfoObject x1 |
| DL/OW_Bare_LayerInfo | 1 | 1 | LandscapeLayerInfoObject x1 |
| DL/LI_OW_Meadow | 1 | 1 | LandscapeLayerInfoObject x1 |
| DL/LGT_OW* (flat) | 10 | 10 | LandscapeGrassType x10 |
| DL/Trees/** (recursive) | 25 | 25 | StaticMesh x25 |
| DL/TreeMIs/** (recursive) | 22 | 22 | MaterialInstanceConstant x22 |
| DL/SM_OWFlowerClump_* (flat) | 3 | 3 | StaticMesh x3 |
| DL/MI_OWFlower_* (flat) | 3 | 3 | MaterialInstanceConstant x3 |
| DL/PCG_OWForest | 1 | 1 | PCGGraph x1 |
| DL/PCG_OWMeadow | 1 | 1 | PCGGraph x1 |
| DL/PCG_OWScree | 1 | 1 | PCGGraph x1 |
| DL/PCG_OWAlpine | 1 | 1 | PCGGraph x1 |
| DL/PCG_OWCliff | 1 | 1 | PCGGraph x1 |
| DL/PCG_OWRoad | 1 | 1 | PCGGraph x1 |
| DL/Cliffs/** (recursive) | 1 | 1 | Blueprint x1 |
| DL/Roads/** (recursive) | 7 | 7 | Blueprint x3, MaterialInstanceConstant x4 |
| sharedassets LayerInfo Meadow* | 0 | 0 | **ZERO** |
| sharedassets LayerInfo Forest* | 0 | 0 | **ZERO** |
| sharedassets LayerInfo RoadVerge* | 0 | 0 | **ZERO** |
| sharedassets LayerInfo Alpine* | 0 | 0 | **ZERO** |
| sharedassets LayerInfo Snow* | 0 | 0 | **ZERO** |
| pkg /Game/OWGame/Dev/WorldPreview/PCG_OWWorldPreview | 1 | 1 | PCGGraph x1 |
| pkg /Game/3DAssets/SM_Beech | 1 | 1 | StaticMesh x1 |
| pkg /Game/3DAssets/SM_Birch | 1 | 1 | StaticMesh x1 |
| pkg /Game/3DAssets/SM_FirTree | 1 | 1 | StaticMesh x1 |

Total root packages: 90

## Folder sizes (closure, grouped at 4 folders below /Game)
| folder | pkgs | MB |
|---|---|---|
| ANGRY_MESH/StylizedPack_MeadowEnvironment/Textures/Rocks | 20 | 431.5 |
| ANGRY_MESH/StylizedPack_MeadowEnvironment/Textures/Trees | 13 | 172.5 |
| ANGRY_MESH/StylizedPack_MeadowEnvironment/Textures/Props | 15 | 172.3 |
| ANGRY_MESH/StylizedPack_MeadowEnvironment/Textures/Landscape | 7 | 97.3 |
| ANGRY_MESH/StylizedPack_MeadowEnvironment/Textures/Mushrooms | 6 | 96.0 |
| ANGRY_MESH/StylizedPack_MeadowEnvironment/Textures/SplineRoad | 4 | 50.5 |
| MWLandscapeAutoMaterial/Textures/Cover | 2 | 16.5 |
| ANGRY_MESH/StylizedPack_MeadowEnvironment/Meshes/Trees | 15 | 16.1 |
| MWLandscapeAutoMaterial/Textures/Plants | 2 | 15.3 |
| Textures/Trunks | 6 | 14.3 |
| OWGame/Dev/DressingLab/Trees | 25 | 12.7 |
| OWGame/Dev/DressingLab | 29 | 9.2 |
| 3DAssets | 3 | 1.7 |
| ANGRY_MESH/StylizedPack_Common/Textures | 11 | 1.6 |
| ANGRY_MESH/StylizedPack_MeadowEnvironment/Textures/CoverPlants | 1 | 1.4 |
| OWGame/Dev/DressingLab/Roads | 7 | 1.2 |
| ANGRY_MESH/StylizedPack_Common/Materials/Functions | 22 | 1.1 |
| ANGRY_MESH/StylizedPack_MeadowEnvironment/Meshes/Rocks | 12 | 1.1 |
| ANGRY_MESH/StylizedPack_MeadowEnvironment/Textures/Flowers | 2 | 0.9 |
| ANGRY_MESH/StylizedPack_MeadowEnvironment/Meshes/Props | 4 | 0.6 |
| ANGRY_MESH/StylizedPack_MeadowEnvironment/Materials/Instances | 28 | 0.6 |
| OWGame/Dev/DressingLab/TreeMIs | 22 | 0.3 |
| ANGRY_MESH/StylizedPack_MeadowEnvironment/Meshes/GroundCoverRVT | 9 | 0.3 |
| ANGRY_MESH/StylizedPack_Common/Materials/Masters | 4 | 0.3 |
| MWLandscapeAutoMaterial/Meshes/Cover | 4 | 0.2 |
| ANGRY_MESH/StylizedPack_MeadowEnvironment/Textures/Grass | 3 | 0.2 |
| OWGame/Dev/WorldPreview | 2 | 0.2 |
| MWLandscapeAutoMaterial/Materials/MASTER/Func | 4 | 0.2 |
| ANGRY_MESH/StylizedPack_MeadowEnvironment/Meshes/Flowers | 5 | 0.2 |
| ANGRY_MESH/StylizedPack_MeadowEnvironment/Meshes/Grass | 5 | 0.1 |
| ANGRY_MESH/StylizedPack_MeadowEnvironment/Meshes/Mushrooms | 2 | 0.1 |
| Textures/Leaves | 3 | 0.1 |
| ANGRY_MESH/StylizedPack_MeadowEnvironment/Meshes/CoverPlants | 4 | 0.1 |
| Materials/MaterialInstances | 6 | 0.1 |
| OWGame/Dev/DressingLab/Masters | 2 | 0.1 |
| ANGRY_MESH/StylizedPack_MeadowEnvironment/Materials/Masters | 1 | 0.1 |
| MWLandscapeAutoMaterial/Textures | 3 | 0.1 |
| Materials | 2 | 0.1 |
| Materials/MaterialFunctions | 3 | 0.1 |
| ANGRY_MESH/StylizedPack_MeadowEnvironment/Textures/Leaves | 1 | 0.1 |
| (8 more folders) | 13 | 0.2 |

## Vendor totals (disk vs closure)
| folder | disk pkgs | disk files | disk MB | closure pkgs | closure MB |
|---|---|---|---|---|---|
| ANGRY_MESH/StylizedPack_Common | 53 | 53 | 12.0 | 41 | 3.0 |
| ANGRY_MESH/StylizedPack_MeadowEnvironment | 875 | 875 | 1801.0 | 161 | 1042.1 |
| MWLandscapeAutoMaterial | 100 | 100 | 701.3 | 18 | 32.3 |
| ToonFantasyNature | 335 | 335 | 37.9 | 0 | 0.0 |
| Fantastic_Village_Pack | 645 | 645 | 1225.6 | 0 | 0.0 |

## Water hits (0)

Packages referencing a /Script or mount path containing Water: 0

## Out of scope (22 packages, 14.6 MB)

### Explicit call-outs
- **/Game/Materials**: 12 packages
  - Materials/MM_Foliage (Material) chain: 3DAssets/SM_Beech > Materials/MaterialInstances/MI_Foliage_Beech [hard] > Materials/MM_Foliage [hard]
  - Materials/MM_Trunk (Material) chain: 3DAssets/SM_Beech > Materials/MaterialInstances/MI_Trunk_Beech [hard] > Materials/MM_Trunk [hard]
  - Materials/MaterialFunctions/F_BendWind (MaterialFunction) chain: OWGame/Dev/DressingLab/Masters/M_OWFoliageMaster > Materials/MaterialFunctions/F_BendWind [hard]
  - Materials/MaterialFunctions/F_RealTimeWindIntensity (MaterialFunction) chain: OWGame/Dev/DressingLab/Masters/M_OWFoliageMaster > Materials/MaterialFunctions/F_RealTimeWindIntensity [hard]
  - Materials/MaterialFunctions/F_WindDirection (MaterialFunction) chain: OWGame/Dev/DressingLab/Masters/M_OWFoliageMaster > Materials/MaterialFunctions/F_WindDirection [hard]
  - ... 7 more
- **/Game/OWGame (outside DressingLab)**: 1 packages
  - OWGame/Dev/WorldPreview/M_OWPreviewConifer (Material) chain: OWGame/Dev/WorldPreview/PCG_OWWorldPreview > OWGame/Dev/WorldPreview/M_OWPreviewConifer [soft]
- **/Game/Textures**: 9 packages
  - Textures/Leaves/TXT_Leaves_Beech (Texture2D) chain: OWGame/Dev/DressingLab/TreeMIs/MI_OWFoliage_Beech > Textures/Leaves/TXT_Leaves_Beech [hard]
  - Textures/Leaves/TXT_Leaves_Birch (Texture2D) chain: OWGame/Dev/DressingLab/Masters/M_OWFoliageMaster > Textures/Leaves/TXT_Leaves_Birch [hard]
  - Textures/Leaves/TXT_Leaves_FirTree (Texture2D) chain: OWGame/Dev/DressingLab/TreeMIs/MI_OWFoliage_FirTree > Textures/Leaves/TXT_Leaves_FirTree [hard]
  - Textures/Trunks/TXT_Trunk_Beech_AO (Texture2D) chain: OWGame/Dev/DressingLab/TreeMIs/MI_OWTrunk_Beech > Textures/Trunks/TXT_Trunk_Beech_AO [hard]
  - Textures/Trunks/TXT_Trunk_Beech_BaseColor (Texture2D) chain: OWGame/Dev/DressingLab/TreeMIs/MI_OWTrunk_Beech > Textures/Trunks/TXT_Trunk_Beech_BaseColor [hard]
  - ... 4 more

### Groups (top two levels below /Game)
#### Materials/MaterialInstances - 6 pkgs, 0.1 MB
folders: Materials/MaterialInstances (6)
- Materials/MaterialInstances/MI_Foliage_Beech (MaterialInstanceConstant) chain: 3DAssets/SM_Beech > Materials/MaterialInstances/MI_Foliage_Beech [hard]
- Materials/MaterialInstances/MI_Foliage_Birch (MaterialInstanceConstant) chain: 3DAssets/SM_Birch > Materials/MaterialInstances/MI_Foliage_Birch [hard]
- Materials/MaterialInstances/MI_Foliage_FirTree (MaterialInstanceConstant) chain: 3DAssets/SM_FirTree > Materials/MaterialInstances/MI_Foliage_FirTree [hard]
- Materials/MaterialInstances/MI_Trunk_Beech (MaterialInstanceConstant) chain: 3DAssets/SM_Beech > Materials/MaterialInstances/MI_Trunk_Beech [hard]
- Materials/MaterialInstances/MI_Trunk_Birch (MaterialInstanceConstant) chain: 3DAssets/SM_Birch > Materials/MaterialInstances/MI_Trunk_Birch [hard]
- Materials/MaterialInstances/MI_Trunk_FirTree (MaterialInstanceConstant) chain: 3DAssets/SM_FirTree > Materials/MaterialInstances/MI_Trunk_FirTree [hard]
#### Textures/Trunks - 6 pkgs, 14.3 MB
folders: Textures/Trunks (6)
- Textures/Trunks/TXT_Trunk_Beech_AO (Texture2D) chain: OWGame/Dev/DressingLab/TreeMIs/MI_OWTrunk_Beech > Textures/Trunks/TXT_Trunk_Beech_AO [hard]
- Textures/Trunks/TXT_Trunk_Beech_BaseColor (Texture2D) chain: OWGame/Dev/DressingLab/TreeMIs/MI_OWTrunk_Beech > Textures/Trunks/TXT_Trunk_Beech_BaseColor [hard]
- Textures/Trunks/TXT_Trunk_Birch_AO (Texture2D) chain: OWGame/Dev/DressingLab/Masters/M_OWTrunkMaster > Textures/Trunks/TXT_Trunk_Birch_AO [hard]
- Textures/Trunks/TXT_Trunk_Birch_BaseColor (Texture2D) chain: OWGame/Dev/DressingLab/Masters/M_OWTrunkMaster > Textures/Trunks/TXT_Trunk_Birch_BaseColor [hard]
- Textures/Trunks/TXT_Trunk_FirTree_AO (Texture2D) chain: OWGame/Dev/DressingLab/TreeMIs/MI_OWTrunk_FirTree > Textures/Trunks/TXT_Trunk_FirTree_AO [hard]
- Textures/Trunks/TXT_Trunk_FirTree_BaseColor (Texture2D) chain: OWGame/Dev/DressingLab/TreeMIs/MI_OWTrunk_FirTree > Textures/Trunks/TXT_Trunk_FirTree_BaseColor [hard]
#### Materials/MaterialFunctions - 3 pkgs, 0.1 MB
folders: Materials/MaterialFunctions (3)
- Materials/MaterialFunctions/F_BendWind (MaterialFunction) chain: OWGame/Dev/DressingLab/Masters/M_OWFoliageMaster > Materials/MaterialFunctions/F_BendWind [hard]
- Materials/MaterialFunctions/F_RealTimeWindIntensity (MaterialFunction) chain: OWGame/Dev/DressingLab/Masters/M_OWFoliageMaster > Materials/MaterialFunctions/F_RealTimeWindIntensity [hard]
- Materials/MaterialFunctions/F_WindDirection (MaterialFunction) chain: OWGame/Dev/DressingLab/Masters/M_OWFoliageMaster > Materials/MaterialFunctions/F_WindDirection [hard]
#### Textures/Leaves - 3 pkgs, 0.1 MB
folders: Textures/Leaves (3)
- Textures/Leaves/TXT_Leaves_Beech (Texture2D) chain: OWGame/Dev/DressingLab/TreeMIs/MI_OWFoliage_Beech > Textures/Leaves/TXT_Leaves_Beech [hard]
- Textures/Leaves/TXT_Leaves_Birch (Texture2D) chain: OWGame/Dev/DressingLab/Masters/M_OWFoliageMaster > Textures/Leaves/TXT_Leaves_Birch [hard]
- Textures/Leaves/TXT_Leaves_FirTree (Texture2D) chain: OWGame/Dev/DressingLab/TreeMIs/MI_OWFoliage_FirTree > Textures/Leaves/TXT_Leaves_FirTree [hard]
#### Materials - 2 pkgs, 0.1 MB
folders: Materials (2)
- Materials/MM_Foliage (Material) chain: 3DAssets/SM_Beech > Materials/MaterialInstances/MI_Foliage_Beech [hard] > Materials/MM_Foliage [hard]
- Materials/MM_Trunk (Material) chain: 3DAssets/SM_Beech > Materials/MaterialInstances/MI_Trunk_Beech [hard] > Materials/MM_Trunk [hard]
#### Materials/MaterialParameterCollection - 1 pkgs, 0.0 MB
folders: Materials/MaterialParameterCollection (1)
- Materials/MaterialParameterCollection/MPC_GlobalWind (MaterialParameterCollection) chain: OWGame/Dev/DressingLab/Masters/M_OWFoliageMaster > Materials/MaterialParameterCollection/MPC_GlobalWind [hard]
#### OWGame/Dev - 1 pkgs, 0.0 MB
folders: OWGame/Dev/WorldPreview (1)
- OWGame/Dev/WorldPreview/M_OWPreviewConifer (Material) chain: OWGame/Dev/WorldPreview/PCG_OWWorldPreview > OWGame/Dev/WorldPreview/M_OWPreviewConifer [soft]

## Script refs to /Script/OWGameUE(Editor) (7)
- **OWGame/Dev/DressingLab/PCG_OWAlpine** [OWGameUE] chain: OWGame/Dev/DressingLab/PCG_OWAlpine
  - PCG_OWAlpine : PCGGraph; ParentClass=None; NativeParentClass=None
- **OWGame/Dev/DressingLab/PCG_OWForest** [OWGameUE] chain: OWGame/Dev/DressingLab/PCG_OWForest
  - PCG_OWForest : PCGGraph; ParentClass=None; NativeParentClass=None
- **OWGame/Dev/DressingLab/PCG_OWMeadow** [OWGameUE] chain: OWGame/Dev/DressingLab/PCG_OWMeadow
  - PCG_OWMeadow : PCGGraph; ParentClass=None; NativeParentClass=None
- **OWGame/Dev/DressingLab/PCG_OWScree** [OWGameUE] chain: OWGame/Dev/DressingLab/PCG_OWScree
  - PCG_OWScree : PCGGraph; ParentClass=None; NativeParentClass=None
- **OWGame/Dev/DressingLab/Roads/BP_OWRoad** [OWGameUE] chain: OWGame/Dev/DressingLab/Roads/BP_OWRoad
  - BP_OWRoad : Blueprint; ParentClass=/Script/CoreUObject.Class'/Script/Engine.Actor'; NativeParentClass=/Script/CoreUObject.Class'/Script/Engine.Actor'
    - components (5): None:/Game/OWGame/Dev/DressingLab/Roads/BP_OWRoad.BP_OWRoad_C, Spline:Engine.SplineComponent, Billboard:Engine.BillboardComponent, Billboard:Engine.BillboardComponent, OWRoadBed:OWGameUE.OWRoadBedComponent
- **OWGame/Dev/DressingLab/Roads/BP_OWRoad_Dusty** [OWGameUE] chain: OWGame/Dev/DressingLab/Roads/BP_OWRoad_Dusty
  - BP_OWRoad_Dusty : Blueprint; ParentClass=/Script/CoreUObject.Class'/Script/Engine.Actor'; NativeParentClass=/Script/CoreUObject.Class'/Script/Engine.Actor'
    - components (5): None:/Game/OWGame/Dev/DressingLab/Roads/BP_OWRoad_Dusty.BP_OWRoad_Dusty_C, Spline:Engine.SplineComponent, Billboard:Engine.BillboardComponent, Billboard:Engine.BillboardComponent, OWRoadBed:OWGameUE.OWRoadBedComponent
- **OWGame/Dev/DressingLab/Roads/BP_OWRoad_Gravel** [OWGameUE] chain: OWGame/Dev/DressingLab/Roads/BP_OWRoad_Gravel
  - BP_OWRoad_Gravel : Blueprint; ParentClass=/Script/CoreUObject.Class'/Script/Engine.Actor'; NativeParentClass=/Script/CoreUObject.Class'/Script/Engine.Actor'
    - components (5): None:/Game/OWGame/Dev/DressingLab/Roads/BP_OWRoad_Gravel.BP_OWRoad_Gravel_C, Spline:Engine.SplineComponent, Billboard:Engine.BillboardComponent, Billboard:Engine.BillboardComponent, OWRoadBed:OWGameUE.OWRoadBedComponent

## Unions
/Script modules (packages referencing): NavigationSystem (95), StaticMeshDescription (25), Landscape (23), InterchangeCore (9), InterchangeEngine (9), InterchangeFactoryNodes (9), InterchangePipelines (9), StructUtilsEditor (7), PCG (7), OWGameUE (7)

Mounts: /Engine (40)

/Engine top folders: Functions (30), EngineMaterials (11), EditorResources (3), EditorBlueprintResources (3), MapTemplates (2), BasicShapes (1)

## Landscape layers
- MaterialEditingLibrary *xpression* methods: connect_material_expressions, create_material_expression, create_material_expression_in_function, delete_all_material_expressions, delete_all_material_expressions_in_function, delete_material_expression, delete_material_expression_in_function, delete_unused_expressions, disconnect_material_expressions, duplicate_material_expression, get_input_node_output_name_for_material_expression, get_inputs_for_material_expression, get_inputs_for_material_function_expression, get_material_expression_input_names, get_material_expression_input_types, get_material_expression_node_position, get_material_expression_output_names, get_material_expressions, get_material_function_expressions, get_num_material_expressions, get_num_material_expressions_in_function, layout_material_expressions, layout_material_function_expressions
- targets loaded: 1/1 (OWGame/Dev/DressingLab/M_OWDressingLab)
- method1 (MEL getters): {'get_material_expressions=ok': 1, 'get_material_function_expressions=ERR': 1, 'get_num_material_expressions=ok': 1, 'get_num_material_expressions_in_function=ERR': 1}
- method2 find_object counts: {'LandscapeLayerSample': 17, 'LandscapeGrassOutput': 1, 'RuntimeVirtualTextureOutput': 1, 'RuntimeVirtualTextureSample': 1}
- method3 ObjectIterator counts: {'LandscapeLayerSample': 17, 'LandscapeGrassOutput': 1, 'RuntimeVirtualTextureOutput': 1, 'RuntimeVirtualTextureSample': 1}
- **OWGame/Dev/DressingLab/M_OWDressingLab**
  - LandscapeGrassOutput: MeadowGrass->OWGame/Dev/DressingLab/LGT_OWMeadowGrass, MeadowFlowers->OWGame/Dev/DressingLab/LGT_OWMeadowFlowers, MeadowDryPatches->OWGame/Dev/DressingLab/LGT_OWMeadowDryGrass, MeadowLushGrass->OWGame/Dev/DressingLab/LGT_OWMeadowLushGrass, MeadowLushFlowers->OWGame/Dev/DressingLab/LGT_OWMeadowLushFlowers, MeadowDryGrass->OWGame/Dev/DressingLab/LGT_OWMeadowDryGrass, ForestFloor->OWGame/Dev/DressingLab/LGT_OWForestFloor, ForestFloorBeech->OWGame/Dev/DressingLab/LGT_OWFloorDeciduous, ForestFloorBirch->OWGame/Dev/DressingLab/LGT_OWFloorDeciduous, ForestFloorFir->OWGame/Dev/DressingLab/LGT_OWFloorFir, ForestFloorOak->OWGame/Dev/DressingLab/LGT_OWFloorOak, AlpineGrass->OWGame/Dev/DressingLab/LGT_OWAlpineGrass
  - LandscapeLayerSample: OW_Meadow
  - LandscapeLayerSample: OW_MeadowLush
  - LandscapeLayerSample: OW_Bare
  - LandscapeLayerSample: OW_Alpine
  - LandscapeLayerSample: OW_Snow
  - LandscapeLayerSample: OW_BedGravel
  - LandscapeLayerSample: OW_BedSand
  - LandscapeLayerSample: OW_BedRock
  - LandscapeLayerSample: OW_RiverWet
  - LandscapeLayerSample: OW_MeadowDry
  - LandscapeLayerSample: OW_Forest
  - ... 8 more nodes
- layer names union: OW_Meadow (1), OW_MeadowLush (1), OW_Bare (1), OW_Alpine (1), OW_Snow (1), OW_BedGravel (1), OW_BedSand (1), OW_BedRock (1), OW_RiverWet (1), OW_MeadowDry (1), OW_Forest (1), OW_ForestBeech (1), OW_ForestBirch (1), OW_ForestFir (1), OW_ForestOak (1), OW_Scree (1), OW_RoadVerge (1)
- RVT assets: ['/Game/ANGRY_MESH/StylizedPack_Common/Textures/RVT_AM_01_Material.RVT_AM_01_Material']
- MI_OWDressingLab_Style parent chain: OWGame/Dev/DressingLab/MI_OWDressingLab_Style.MI_OWDressingLab_Style (MaterialInstanceConstant) -> OWGame/Dev/DressingLab/M_OWDressingLab.M_OWDressingLab (Material)

## Sharedassets listing (24 assets)
| folder | name | class | root |
|---|---|---|---|
| L_OWDressingLab_sharedassets | OW_BedGravel_LayerInfo | LandscapeLayerInfoObject | no |
| L_OWDressingLab_sharedassets | OW_BedRock_LayerInfo | LandscapeLayerInfoObject | no |
| L_OWDressingLab_sharedassets | OW_BedSand_LayerInfo | LandscapeLayerInfoObject | no |
| L_OWDressingLab_sharedassets | OW_ForestBeech_LayerInfo | LandscapeLayerInfoObject | no |
| L_OWDressingLab_sharedassets | OW_ForestBirch_LayerInfo | LandscapeLayerInfoObject | no |
| L_OWDressingLab_sharedassets | OW_ForestFir_LayerInfo | LandscapeLayerInfoObject | no |
| L_OWDressingLab_sharedassets | OW_ForestOak_LayerInfo | LandscapeLayerInfoObject | no |
| L_OWDressingLab_sharedassets | OW_MeadowDry_LayerInfo | LandscapeLayerInfoObject | no |
| L_OWDressingLab_sharedassets | OW_MeadowLush_LayerInfo | LandscapeLayerInfoObject | no |
| L_OWDressingLab_sharedassets | OW_RiverWet_LayerInfo | LandscapeLayerInfoObject | no |
| L_OWDressingLab_sharedassets | OW_RoadVerge_LayerInfo | LandscapeLayerInfoObject | no |
| L_OWWorldCanvas_sharedassets | OW_Alpine_LayerInfo | LandscapeLayerInfoObject | no |
| L_OWWorldCanvas_sharedassets | OW_Bare_LayerInfo | LandscapeLayerInfoObject | no |
| L_OWWorldCanvas_sharedassets | OW_ForestBeech_LayerInfo | LandscapeLayerInfoObject | no |
| L_OWWorldCanvas_sharedassets | OW_ForestBirch_LayerInfo | LandscapeLayerInfoObject | no |
| L_OWWorldCanvas_sharedassets | OW_ForestFir_LayerInfo | LandscapeLayerInfoObject | no |
| L_OWWorldCanvas_sharedassets | OW_ForestOak_LayerInfo | LandscapeLayerInfoObject | no |
| L_OWWorldCanvas_sharedassets | OW_Forest_LayerInfo | LandscapeLayerInfoObject | no |
| L_OWWorldCanvas_sharedassets | OW_MeadowDry_LayerInfo | LandscapeLayerInfoObject | no |
| L_OWWorldCanvas_sharedassets | OW_MeadowLush_LayerInfo | LandscapeLayerInfoObject | no |
| L_OWWorldCanvas_sharedassets | OW_Meadow_LayerInfo | LandscapeLayerInfoObject | no |
| L_OWWorldCanvas_sharedassets | OW_RoadVerge_LayerInfo | LandscapeLayerInfoObject | no |
| L_OWWorldCanvas_sharedassets | OW_Scree_LayerInfo | LandscapeLayerInfoObject | no |
| L_OWWorldCanvas_sharedassets | OW_Snow_LayerInfo | LandscapeLayerInfoObject | no |

## Left behind in DressingLab (10 assets not in closure)
| subfolder | count | classes |
|---|---|---|
| River | 7 | StaticMesh x4, MaterialInstanceConstant x1, Material x1, Texture2D x1 |
| (DressingLab root) | 3 | MaterialInstanceConstant x1, Material x1, PCGGraph x1 |

River-ish left-behind names (10): OWGame/Dev/DressingLab/MI_OWWaterVillage, OWGame/Dev/DressingLab/M_OWWaterVillage, OWGame/Dev/DressingLab/PCG_OWRiver, OWGame/Dev/DressingLab/River/SM_OWRiverPlane, OWGame/Dev/DressingLab/River/MI_OWRiverWater, OWGame/Dev/DressingLab/River/M_OWRiverWater, OWGame/Dev/DressingLab/River/T_OWFoamStreaks, OWGame/Dev/DressingLab/River/Gorge/SM_OWGorgeBlock_A, OWGame/Dev/DressingLab/River/Gorge/SM_OWGorgeBlock_B, OWGame/Dev/DressingLab/River/Gorge/SM_OWGorgeBlock_C

## Zero-match rules and step failures
- zero-match rules: ['sharedassets LayerInfo Meadow*', 'sharedassets LayerInfo Forest*', 'sharedassets LayerInfo RoadVerge*', 'sharedassets LayerInfo Alpine*', 'sharedassets LayerInfo Snow*']
- step timings: registry 0.53s (1), roots 0.05s (90), closure 0.18s (332), water 0.0s (0), out_of_scope 0.0s (22), script_refs 0.33s (7), unions 0.0s (10), landscape 0.8s (20), sizes 0.13s (48), left_behind 0.0s (10)
