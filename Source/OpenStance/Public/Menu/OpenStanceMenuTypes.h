#pragma once

#include "CoreMinimal.h"
#include "OpenStanceMenuTypes.generated.h"

/**
 * Every full screen in the menu flow (GDD 7.5 to 7.8, Docs/Prototype/menu_prototype.html).
 * Screens the design tags Future are listed so the flow is complete; they open as greyed information pages.
 */
UENUM(BlueprintType)
enum class EOpenStanceMenuScreen : uint8
{
	None,
	Title,
	Main,
	Sparring,
	Tournament,
	FighterSelect,
	Match,
	Results,
	Bracket,
	Training,
	Career,
	Customize,
	Options,
	Controls,
	Team,
	Challenges,
	Online,
	Replays,
	Broadcast,
	LongTerm,
	RefereeSetup,
	RefereeMatch,
	RefereeGrade
};

/** Which mode the player entered from the Play hub. Decides what follows fighter select and the results page. */
UENUM(BlueprintType)
enum class EOpenStanceMatchMode : uint8
{
	Sparring,
	Tournament,
	Career,
	Referee
};

/** Chung is blue and starts on the left, Hong is red and starts on the right (GDD 4.1). The game assigns sides. */
UENUM(BlueprintType)
enum class EOpenStanceSide : uint8
{
	Chung,
	Hong
};

UENUM(BlueprintType)
enum class EOpenStanceSex : uint8
{
	Male,
	Female
};

/** The four body types the fighter rig supports (GDD 5.4.2); Medium is the base and is not offered in the creator. */
UENUM(BlueprintType)
enum class EOpenStanceBodyType : uint8
{
	Compact,
	LeanTall,
	Stocky,
	Tall
};

UENUM(BlueprintType)
enum class EOpenStanceFightingStyle : uint8
{
	Counter,
	Kicker,
	Pressure
};

/** A premade fighter for Sparring and Tournament. The created fighter is Career only. */
USTRUCT(BlueprintType)
struct OPENSTANCE_API FOpenStanceFighterProfile
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Menu")
	FString Name;

	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Menu")
	EOpenStanceSex Sex = EOpenStanceSex::Male;

	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Menu")
	EOpenStanceBodyType BodyType = EOpenStanceBodyType::Compact;

	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Menu")
	EOpenStanceFightingStyle Style = EOpenStanceFightingStyle::Counter;

	/** Overall rating shown on the select screen. */
	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Menu")
	int32 Overall = 70;
};

/**
 * Look of the Career fighter. Colour rules (Docs/Character_Customization.md): skin, hair and eyes are natural
 * presets only, and the protector and helmet are only Chung blue or Hong red. Appearance never changes attributes.
 */
USTRUCT(BlueprintType)
struct OPENSTANCE_API FOpenStanceFighterAppearance
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadWrite, Category = "Open Stance|Menu")
	EOpenStanceSex Sex = EOpenStanceSex::Male;

	UPROPERTY(BlueprintReadWrite, Category = "Open Stance|Menu")
	EOpenStanceBodyType BodyType = EOpenStanceBodyType::Compact;

	UPROPERTY(BlueprintReadWrite, Category = "Open Stance|Menu")
	EOpenStanceFightingStyle Style = EOpenStanceFightingStyle::Counter;

	UPROPERTY(BlueprintReadWrite, Category = "Open Stance|Menu")
	int32 SkinIndex = 1;

	UPROPERTY(BlueprintReadWrite, Category = "Open Stance|Menu")
	int32 HairIndex = 0;

	UPROPERTY(BlueprintReadWrite, Category = "Open Stance|Menu")
	int32 EyeIndex = 0;

	UPROPERTY(BlueprintReadWrite, Category = "Open Stance|Menu")
	EOpenStanceSide ProtectorSide = EOpenStanceSide::Chung;

	/** Preview with the protective gear on or the plain dobok. */
	UPROPERTY(BlueprintReadWrite, Category = "Open Stance|Menu")
	bool bGearOn = true;
};

/** The choices a player made on the setup and fighter select screens, handed to the match when it starts. */
USTRUCT(BlueprintType)
struct OPENSTANCE_API FOpenStanceMatchSetup
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Menu")
	EOpenStanceMatchMode Mode = EOpenStanceMatchMode::Sparring;

	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Menu")
	FOpenStanceFighterProfile Chung;

	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Menu")
	FOpenStanceFighterProfile Hong;

	/** Setup row values as shown on screen: Players, Ruleset, AI difficulty, Arena, Bracket size. */
	UPROPERTY(BlueprintReadOnly, Category = "Open Stance|Menu")
	TMap<FName, FString> Choices;
};

/** What the menu remembers between screens, like the prototype's state object. Not reflected: it only lives in the menu subsystem. */
struct FOpenStanceMenuSession
{
	EOpenStanceMatchMode Mode = EOpenStanceMatchMode::Sparring;

	/** Roster tab on the fighter select screen; sets which sex of premade fighters is listed. */
	EOpenStanceSex Category = EOpenStanceSex::Male;

	/** Indices into the premade roster. */
	int32 ChungFighter = 0;
	int32 HongFighter = 1;

	/** Selected value index per setup or options row, keyed by row id. */
	TMap<FName, int32> Choices;

	int32 MainHubIndex = 0;
	int32 OptionsTabIndex = 0;
	int32 ControlsTabIndex = 0;

	FString CareerName = TEXT("Jae-won Choi");
	FOpenStanceFighterAppearance CareerAppearance;
};
