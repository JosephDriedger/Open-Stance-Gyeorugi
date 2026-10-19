#include "Menu/OpenStanceUserSettings.h"

UOpenStanceUserSettings* UOpenStanceUserSettings::Get()
{
	return Cast<UOpenStanceUserSettings>(GetGameUserSettings());
}

void UOpenStanceUserSettings::CommitChanges(bool bVideoChanged)
{
	if (bVideoChanged)
	{
		if (GIsEditor)
		{
			ApplyNonResolutionSettings();
		}
		else
		{
			ApplySettings(false);
		}
	}
	SaveSettings();
}
