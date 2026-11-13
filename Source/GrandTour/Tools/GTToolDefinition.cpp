#include "Tools/GTToolDefinition.h"

TArrayView<const UGTToolDefinition::FDefault> UGTToolDefinition::DefaultTools()
{
	static const FDefault Rows[] = {
		{TEXT("DA_Tool_Cutter"), TEXT("Cutter"), TEXT("Cutter"), TEXT("Tool.Cut"), 1.f, FVector(28.f, 8.f, 5.f), FLinearColor(0.85f, 0.35f, 0.1f)},
		{TEXT("DA_Tool_PryBar"), TEXT("PryBar"), TEXT("Pry bar"), TEXT("Tool.Pry"), 1.f, FVector(60.f, 4.f, 4.f), FLinearColor(0.25f, 0.25f, 0.3f)},
		{TEXT("DA_Tool_RepairKit"), TEXT("RepairKit"), TEXT("Repair kit"), TEXT("Tool.Repair"), 1.f, FVector(24.f, 16.f, 10.f), FLinearColor(0.7f, 0.1f, 0.1f)},
	};
	return TArrayView<const FDefault>(Rows, UE_ARRAY_COUNT(Rows));
}

void UGTToolDefinition::ApplyDefault(const FDefault& Row)
{
	ToolId = Row.Id;
	DisplayName = FText::FromString(Row.Name);
	GrantedTag = FGameplayTag::RequestGameplayTag(Row.Tag);
	UseTimeScale = Row.UseTimeScale;
	GreyboxSize = Row.Size;
	GreyboxColour = Row.Colour;
}
