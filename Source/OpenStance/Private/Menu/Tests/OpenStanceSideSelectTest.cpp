#include "Menu/OpenStanceMenuContent.h"
#include "Menu/OpenStanceMenuTypes.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FOpenStanceSideSelectFlowTest, "OpenStance.Menu.SideSelectFlow", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FOpenStanceSideSelectFlowTest::RunTest(const FString& Parameters)
{
	// Sparring picks a side first, then a fighter; Tournament goes straight to fighter select.
	const OpenStanceMenuContent::FSetupDefinition* Sparring = OpenStanceMenuContent::FindSetup(EOpenStanceMenuScreen::Sparring);
	if (TestNotNull(TEXT("the Sparring setup exists"), Sparring))
	{
		TestEqual(TEXT("Sparring continues to Side Select"), Sparring->Next, EOpenStanceMenuScreen::SideSelect);
		TestEqual(TEXT("and the button says so"), Sparring->ContinueLabel, FString(TEXT("Continue to Side Select")));
	}
	const OpenStanceMenuContent::FSetupDefinition* Tournament = OpenStanceMenuContent::FindSetup(EOpenStanceMenuScreen::Tournament);
	if (TestNotNull(TEXT("the Tournament setup exists"), Tournament))
	{
		TestEqual(TEXT("Tournament continues to Fighter Select"), Tournament->Next, EOpenStanceMenuScreen::FighterSelect);
	}

	// The session starts with the player on Chung, the blue side on the left.
	FOpenStanceMenuSession Session;
	TestEqual(TEXT("the default side is Chung"), Session.PlayerSide, EOpenStanceSide::Chung);
	FOpenStanceMatchSetup Setup;
	TestEqual(TEXT("and so is the match setup's"), Setup.PlayerSide, EOpenStanceSide::Chung);
	return true;
}

#endif
