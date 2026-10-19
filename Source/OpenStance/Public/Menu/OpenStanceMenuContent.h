#pragma once

#include "CoreMinimal.h"
#include "Menu/OpenStanceMenuTypes.h"

/**
 * The words and tables the menu screens show, taken from the prototype (Docs/Prototype/menu_prototype.html) and the
 * GDD it follows. Names, ratings and sample lists are placeholders the design marks as example content; they live
 * here, apart from the screen code, so the real roster and ruleset can replace them in one place.
 */
namespace OpenStanceMenuContent
{
	// Fighters

	OPENSTANCE_API const TArray<FOpenStanceFighterProfile>& GetRoster();

	/** Roster indices of the premade fighters of one sex, in list order. */
	OPENSTANCE_API TArray<int32> GetRosterIndices(EOpenStanceSex Sex);

	OPENSTANCE_API FString GetBodyTypeName(EOpenStanceBodyType BodyType);
	OPENSTANCE_API FString GetStyleName(EOpenStanceFightingStyle Style);
	OPENSTANCE_API FString GetSexName(EOpenStanceSex Sex);

	/** Natural skin, hair and eye presets for the creator; the protector offers Chung blue or Hong red only. */
	OPENSTANCE_API const TArray<FLinearColor>& GetSkinPresets();
	OPENSTANCE_API const TArray<FLinearColor>& GetHairPresets();
	OPENSTANCE_API const TArray<FLinearColor>& GetEyePresets();

	// Main menu

	struct FHubTile
	{
		FString Title;
		FString Subtitle;
		/** The screen it opens; None with bQuit set asks to quit to the title screen. */
		EOpenStanceMenuScreen Target = EOpenStanceMenuScreen::None;
		bool bQuit = false;
		bool bFuture = false;
		bool bKick = false;
		FLinearColor From;
		FLinearColor To;
	};

	struct FHub
	{
		FString Name;
		TArray<FHubTile> Tiles;
	};

	OPENSTANCE_API const TArray<FHub>& GetHubs();

	// Setup, referee setup and information pages

	struct FChoiceRow
	{
		FName Id;
		FString Label;
		TArray<FString> Values;
		int32 DefaultIndex = 0;
	};

	struct FInfoCard
	{
		FString Title;
		TArray<FString> Paragraphs;
		bool bFutureTag = false;
	};

	struct FSetupDefinition
	{
		EOpenStanceMenuScreen Screen = EOpenStanceMenuScreen::None;
		FString Kicker;
		FString Title;
		bool bFuture = false;
		TArray<FChoiceRow> Rows;
		FString ContinueLabel;
		EOpenStanceMenuScreen Next = EOpenStanceMenuScreen::None;
		TArray<FInfoCard> Cards;
	};

	/** Sparring, Tournament and Referee setup; null for any other screen. */
	OPENSTANCE_API const FSetupDefinition* FindSetup(EOpenStanceMenuScreen Screen);

	struct FListItem
	{
		FString Label;
		FString Detail;
	};

	struct FListDefinition
	{
		FString Kicker;
		FString Title;
		float WidthUnits = 46.0f;
		TArray<FListItem> Items;
		TArray<FInfoCard> Cards;
	};

	/** The Future information pages: Team, Challenges, Online, Replays, Broadcast and Long-term career. */
	OPENSTANCE_API const FListDefinition* FindList(EOpenStanceMenuScreen Screen);

	// Controls

	struct FControlRow
	{
		FString Action;
		/** Button tokens (LS, RT, D-pad ...) and stick gestures in braces, e.g. "RS {qf}, down". */
		FString Input;
		FString Notes;
	};

	struct FControlTab
	{
		FString Name;
		FString Columns[3];
		TArray<FControlRow> Rows;
		bool bFuture = false;
	};

	OPENSTANCE_API const TArray<FControlTab>& GetControlTabs();

	/** Index of the tab with this name, or INDEX_NONE. */
	OPENSTANCE_API int32 FindControlTab(const FString& Name);
}
