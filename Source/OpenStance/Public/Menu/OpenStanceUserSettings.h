#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameUserSettings.h"
#include "OpenStanceUserSettings.generated.h"

/**
 * Player settings behind the Options screen. Video (resolution, window mode, quality, frame-rate cap, V-sync)
 * is the engine's own UGameUserSettings; this adds audio levels, the controls options in GDD 7.8 and the
 * accessibility toggles. Items the design tags Future (remapping, reduced motion, audio cues) are stored so the
 * screen can show them, but nothing reads them yet.
 *
 * Registered through GameUserSettingsClassName in DefaultEngine.ini, so UGameUserSettings::GetGameUserSettings()
 * returns this class.
 */
UCLASS(config = GameUserSettings, configdonotcheckdefaults)
class OPENSTANCE_API UOpenStanceUserSettings : public UGameUserSettings
{
	GENERATED_BODY()

public:
	static UOpenStanceUserSettings* Get();

	/**
	 * Writes everything to GameUserSettings.ini. The options screen calls it after each change, because settings
	 * save automatically. With bVideoChanged it also applies resolution, window mode, quality, frame rate and V-sync;
	 * resolution and window mode are left alone inside the editor, where changing them would resize the editor window.
	 */
	void CommitChanges(bool bVideoChanged);

	/** Volumes are percentages, 0 to 100. */
	UPROPERTY(Config, BlueprintReadWrite, Category = "Audio")
	float MasterVolume = 80.0f;

	UPROPERTY(Config, BlueprintReadWrite, Category = "Audio")
	float EffectsVolume = 90.0f;

	UPROPERTY(Config, BlueprintReadWrite, Category = "Audio")
	float RefereeVoiceVolume = 100.0f;

	UPROPERTY(Config, BlueprintReadWrite, Category = "Audio")
	float CrowdVolume = 60.0f;

	UPROPERTY(Config, BlueprintReadWrite, Category = "Audio")
	float MusicVolume = 50.0f;

	/** Future: commentary is not in v1.0. */
	UPROPERTY(Config, BlueprintReadWrite, Category = "Audio")
	float CommentaryVolume = 40.0f;

	UPROPERTY(Config, BlueprintReadWrite, Category = "Controls")
	bool bVibration = true;

	/** Skill Stick dead zone as a percentage of stick travel. */
	UPROPERTY(Config, BlueprintReadWrite, Category = "Controls")
	float SkillStickDeadZone = 15.0f;

	/** How long a stick motion has to complete, in seconds (GDD 7.8: 0.20 to 0.40). */
	UPROPERTY(Config, BlueprintReadWrite, Category = "Controls")
	float StickInputWindow = 0.25f;

	/** Future: hold-to-toggle for the held modifiers. */
	UPROPERTY(Config, BlueprintReadWrite, Category = "Controls")
	bool bHoldToToggleModifiers = false;

	UPROPERTY(Config, BlueprintReadWrite, Category = "Accessibility")
	bool bRefereeSubtitles = true;

	/** Future: the four accessibility options below are not implemented yet. */
	UPROPERTY(Config, BlueprintReadWrite, Category = "Accessibility")
	bool bReducedCameraMotion = false;

	UPROPERTY(Config, BlueprintReadWrite, Category = "Accessibility")
	bool bReducedScreenShake = false;

	UPROPERTY(Config, BlueprintReadWrite, Category = "Accessibility")
	bool bAudioCuesIncomingAttacks = false;

	UPROPERTY(Config, BlueprintReadWrite, Category = "Accessibility")
	bool bAudioCuesStaminaState = false;
};
