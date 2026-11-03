#include "Menu/OpenStanceMenuContent.h"

#include "Menu/OpenStanceMenuTheme.h"

using namespace OpenStanceMenu;

namespace OpenStanceMenuContent
{
	namespace
	{
		FOpenStanceFighterProfile MakeFighter(const TCHAR* Name, EOpenStanceSex Sex, EOpenStanceBodyType BodyType, EOpenStanceFightingStyle Style, int32 Overall)
		{
			FOpenStanceFighterProfile Profile;
			Profile.Name = Name;
			Profile.Sex = Sex;
			Profile.BodyType = BodyType;
			Profile.Style = Style;
			Profile.Overall = Overall;
			return Profile;
		}

		FHubTile MakeTile(const TCHAR* Title, const TCHAR* Subtitle, EOpenStanceMenuScreen Target, uint32 From, uint32 To, bool bKick, bool bFuture = false)
		{
			FHubTile Tile;
			Tile.Title = Title;
			Tile.Subtitle = Subtitle;
			Tile.Target = Target;
			Tile.From = Hex(From);
			Tile.To = Hex(To);
			Tile.bKick = bKick;
			Tile.bFuture = bFuture;
			return Tile;
		}

		FChoiceRow MakeRow(const TCHAR* Id, const TCHAR* Label, TArray<FString> Values, int32 DefaultIndex = 0)
		{
			FChoiceRow Row;
			Row.Id = Id;
			Row.Label = Label;
			Row.Values = MoveTemp(Values);
			Row.DefaultIndex = DefaultIndex;
			return Row;
		}

		FControlRow MakeControl(const TCHAR* Action, const TCHAR* Input, const TCHAR* Notes)
		{
			return { Action, Input, Notes };
		}

		FControlTab MakeTab(const TCHAR* Name, const TCHAR* Column0, const TCHAR* Column1, const TCHAR* Column2, TArray<FControlRow> Rows, bool bFuture = false)
		{
			FControlTab Tab;
			Tab.Name = Name;
			Tab.Columns[0] = Column0;
			Tab.Columns[1] = Column1;
			Tab.Columns[2] = Column2;
			Tab.Rows = MoveTemp(Rows);
			Tab.bFuture = bFuture;
			return Tab;
		}

		TArray<FString> RulesetValues()
		{
			return { TEXT("World Taekwondo"), TEXT("Casual (No Gam-jeom)"), TEXT("Golden Point"), TEXT("Custom Rules [Future]"), TEXT("Historical WT Rules [Future]"), TEXT("Para Taekwondo [Future]") };
		}

		TArray<FString> DifficultyValues()
		{
			return { TEXT("Easy"), TEXT("Normal"), TEXT("Hard"), TEXT("Master") };
		}

		TArray<FInfoCard> RulesCards(const TCHAR* Title, const TCHAR* Summary, const TCHAR* Detail)
		{
			return
			{
				{ Title, { Summary, Detail } },
				{ TEXT("Ruleset Note"),
					{
						TEXT("Rounds are 3 × 2:00 with 1:00 breaks. A 12-point gap ends the match. Head kicks score more than body kicks; turning kicks score more than straight ones."),
						TEXT("Values tagged [Future] come after v1.0.")
					} }
			};
		}
	}

	const TArray<FOpenStanceFighterProfile>& GetRoster()
	{
		static const TArray<FOpenStanceFighterProfile> Roster =
		{
			MakeFighter(TEXT("Min-jun Park"), EOpenStanceSex::Male, EOpenStanceBodyType::Compact, EOpenStanceFightingStyle::Counter, 74),
			MakeFighter(TEXT("Dae-ho Kim"), EOpenStanceSex::Male, EOpenStanceBodyType::Stocky, EOpenStanceFightingStyle::Pressure, 77),
			MakeFighter(TEXT("Marcus Bell"), EOpenStanceSex::Male, EOpenStanceBodyType::Tall, EOpenStanceFightingStyle::Kicker, 80),
			MakeFighter(TEXT("Tomas Silva"), EOpenStanceSex::Male, EOpenStanceBodyType::LeanTall, EOpenStanceFightingStyle::Counter, 76),
			MakeFighter(TEXT("Sofia Reyes"), EOpenStanceSex::Female, EOpenStanceBodyType::LeanTall, EOpenStanceFightingStyle::Kicker, 81),
			MakeFighter(TEXT("Amara Okafor"), EOpenStanceSex::Female, EOpenStanceBodyType::Tall, EOpenStanceFightingStyle::Counter, 79),
			MakeFighter(TEXT("Aiko Tanaka"), EOpenStanceSex::Female, EOpenStanceBodyType::Compact, EOpenStanceFightingStyle::Pressure, 75),
			MakeFighter(TEXT("Hana Lee"), EOpenStanceSex::Female, EOpenStanceBodyType::Stocky, EOpenStanceFightingStyle::Counter, 73)
		};
		return Roster;
	}

	TArray<int32> GetRosterIndices(EOpenStanceSex Sex)
	{
		TArray<int32> Indices;
		const TArray<FOpenStanceFighterProfile>& Roster = GetRoster();
		for (int32 Index = 0; Index < Roster.Num(); ++Index)
		{
			if (Roster[Index].Sex == Sex)
			{
				Indices.Add(Index);
			}
		}
		return Indices;
	}

	FString GetBodyTypeName(EOpenStanceBodyType BodyType)
	{
		switch (BodyType)
		{
		case EOpenStanceBodyType::LeanTall:
			return TEXT("Lean Tall");
		case EOpenStanceBodyType::Stocky:
			return TEXT("Stocky");
		case EOpenStanceBodyType::Tall:
			return TEXT("Tall");
		default:
			return TEXT("Compact");
		}
	}

	FString GetStyleName(EOpenStanceFightingStyle Style)
	{
		switch (Style)
		{
		case EOpenStanceFightingStyle::Kicker:
			return TEXT("Kicker");
		case EOpenStanceFightingStyle::Pressure:
			return TEXT("Pressure");
		default:
			return TEXT("Counter");
		}
	}

	FString GetSexName(EOpenStanceSex Sex)
	{
		return Sex == EOpenStanceSex::Female ? TEXT("Female") : TEXT("Male");
	}

	const TArray<FLinearColor>& GetSkinPresets()
	{
		static const TArray<FLinearColor> Presets = { Hex(0xf1d3b8), Hex(0xd9a97f), Hex(0xb9825a), Hex(0x8a5a3a), Hex(0x5a3a26) };
		return Presets;
	}

	const TArray<FLinearColor>& GetHairPresets()
	{
		static const TArray<FLinearColor> Presets = { Hex(0x1b1410), Hex(0x3a2618), Hex(0x6b4a2c), Hex(0xa8793c), Hex(0x8a8a8a) };
		return Presets;
	}

	const TArray<FLinearColor>& GetEyePresets()
	{
		static const TArray<FLinearColor> Presets = { Hex(0x3a2618), Hex(0x5b4a2a), Hex(0x2f6b4a), Hex(0x3a6a9a), Hex(0x6a6a6a) };
		return Presets;
	}

	const TArray<FHub>& GetHubs()
	{
		static const TArray<FHub> Hubs =
		{
			{ TEXT("Play"),
				{
					MakeTile(TEXT("Sparring"), TEXT("Local match, 1P or 2P"), EOpenStanceMenuScreen::Sparring, 0x1e56c8, 0x0a1d4a, true),
					MakeTile(TEXT("Tournament"), TEXT("8, 16 or 32 fighter bracket"), EOpenStanceMenuScreen::Tournament, 0xc8323a, 0x4a0c12, false),
					MakeTile(TEXT("Team Championship"), TEXT("Tag-team format, shared score"), EOpenStanceMenuScreen::Team, 0x6a35c8, 0x1c0c4a, false, true),
					MakeTile(TEXT("Challenges"), TEXT("Set scenarios, medals"), EOpenStanceMenuScreen::Challenges, 0xc8841f, 0x4a2c08, true, true),
					MakeTile(TEXT("Referee Mode"), TEXT("Call the match"), EOpenStanceMenuScreen::RefereeSetup, 0x1f8a62, 0x082c20, false, true)
				} },
			{ TEXT("Progress"),
				{
					MakeTile(TEXT("Career"), TEXT("Your created fighter: seasons and events"), EOpenStanceMenuScreen::Career, 0x1e56c8, 0x0a1d4a, true),
					MakeTile(TEXT("Training"), TEXT("Lessons, drills and free practice"), EOpenStanceMenuScreen::Training, 0x1f8a62, 0x082c20, false)
				} },
			{ TEXT("Connected"),
				{
					MakeTile(TEXT("Online"), TEXT("Casual, ranked, clubs"), EOpenStanceMenuScreen::Online, 0x1e56c8, 0x0a1d4a, true, true),
					MakeTile(TEXT("Replays"), TEXT("Watch, photo mode, share"), EOpenStanceMenuScreen::Replays, 0xc8323a, 0x4a0c12, false, true),
					MakeTile(TEXT("Broadcast"), TEXT("Tools for community tournaments"), EOpenStanceMenuScreen::Broadcast, 0x2a6fa0, 0x0b2236, false, true)
				} },
			{ TEXT("Options"),
				{
					MakeTile(TEXT("Options"), TEXT("Audio, video and controls"), EOpenStanceMenuScreen::Options, 0x2a6fa0, 0x0b2236, false),
					MakeTile(TEXT("Controls"), TEXT("Every input, by group"), EOpenStanceMenuScreen::Controls, 0x1e56c8, 0x0a1d4a, false),
					[]()
					{
						FHubTile Quit = MakeTile(TEXT("Quit"), TEXT("Back to the title screen"), EOpenStanceMenuScreen::None, 0x8a2a2a, 0x2a0a0a, false);
						Quit.bQuit = true;
						return Quit;
					}()
				} }
		};
		return Hubs;
	}

	const FSetupDefinition* FindSetup(EOpenStanceMenuScreen Screen)
	{
		static const TArray<FSetupDefinition> Setups = []()
		{
			TArray<FSetupDefinition> Result;

			FSetupDefinition Sparring;
			Sparring.Screen = EOpenStanceMenuScreen::Sparring;
			Sparring.Kicker = TEXT("Play");
			Sparring.Title = TEXT("Sparring Setup");
			Sparring.Rows =
			{
				MakeRow(TEXT("Players"), TEXT("Players"), { TEXT("1P vs AI"), TEXT("1P vs 2P"), TEXT("Online [Future]") }),
				MakeRow(TEXT("Ruleset"), TEXT("Ruleset"), RulesetValues()),
				MakeRow(TEXT("Difficulty"), TEXT("AI Difficulty"), DifficultyValues(), 1),
				MakeRow(TEXT("Arena"), TEXT("Arena"), { TEXT("Training Dojang"), TEXT("Club Dojang"), TEXT("National Arena"), TEXT("Olympic Arena"), TEXT("World Games Stadium [Future]") })
			};
			Sparring.ContinueLabel = TEXT("Continue to Side Select");
			Sparring.Next = EOpenStanceMenuScreen::SideSelect;
			Sparring.Cards = RulesCards(TEXT("Sparring"), TEXT("Players, ruleset, difficulty and arena."),
				TEXT("You pick your side next: Chung is on the left in blue and Hong is on the right in red."));
			Result.Add(Sparring);

			FSetupDefinition Tournament;
			Tournament.Screen = EOpenStanceMenuScreen::Tournament;
			Tournament.Kicker = TEXT("Play");
			Tournament.Title = TEXT("Tournament Setup");
			Tournament.Rows =
			{
				MakeRow(TEXT("BracketSize"), TEXT("Bracket Size"), { TEXT("8"), TEXT("16"), TEXT("32") }),
				MakeRow(TEXT("Ruleset"), TEXT("Ruleset"), RulesetValues()),
				MakeRow(TEXT("Difficulty"), TEXT("AI Difficulty"), DifficultyValues(), 1),
				MakeRow(TEXT("Arena"), TEXT("Arena"), { TEXT("Club Dojang"), TEXT("National Arena"), TEXT("Olympic Arena"), TEXT("World Games Stadium [Future]") })
			};
			Tournament.ContinueLabel = TEXT("Continue to Fighter Select");
			Tournament.Next = EOpenStanceMenuScreen::FighterSelect;
			Tournament.Cards = RulesCards(TEXT("Tournament"), TEXT("Bracket, ruleset, difficulty and arena."),
				TEXT("Between matches a bracket view shows results and the next pairing."));
			Result.Add(Tournament);

			FSetupDefinition Referee;
			Referee.Screen = EOpenStanceMenuScreen::RefereeSetup;
			Referee.Kicker = TEXT("Play");
			Referee.Title = TEXT("Referee Mode Setup");
			Referee.bFuture = true;
			Referee.Rows =
			{
				MakeRow(TEXT("Match"), TEXT("Match"), { TEXT("Two AI Fighters"), TEXT("Two Local Players"), TEXT("Online [Future]") }),
				MakeRow(TEXT("Camera"), TEXT("Camera"), { TEXT("Over-the-Shoulder"), TEXT("Side-On") }),
				MakeRow(TEXT("Ruleset"), TEXT("Ruleset"), { TEXT("World Taekwondo"), TEXT("Casual (No Gam-jeom)") }),
				MakeRow(TEXT("Arena"), TEXT("Arena"), { TEXT("Club Dojang"), TEXT("National Arena"), TEXT("Olympic Arena") })
			};
			Referee.ContinueLabel = TEXT("Start as Referee");
			Referee.Next = EOpenStanceMenuScreen::RefereeMatch;
			Referee.Cards =
			{
				{ TEXT("Calls Decide the Match"), { TEXT("Only the penalties you declare are applied. Automatic detection runs only as the answer key for your grade.") } },
				{ TEXT("Players"), { TEXT("Up to three controllers: Chung, Hong and the referee. The referee has its own layout (Controls, Referee Mode).") } }
			};
			Result.Add(Referee);
			return Result;
		}();

		return Setups.FindByPredicate([Screen](const FSetupDefinition& Setup) { return Setup.Screen == Screen; });
	}

	const FListDefinition* FindList(EOpenStanceMenuScreen Screen)
	{
		static const TMap<EOpenStanceMenuScreen, FListDefinition> Lists = []()
		{
			TMap<EOpenStanceMenuScreen, FListDefinition> Result;

			FListDefinition Team;
			Team.Kicker = TEXT("Play");
			Team.Title = TEXT("Team Championship");
			Team.Items =
			{
				{ TEXT("Team Type"), TEXT("Club or national") },
				{ TEXT("Format"), TEXT("Tag team: fighters rotate in and out") },
				{ TEXT("Team Size"), TEXT("Up to three local players per team") },
				{ TEXT("Match Result"), TEXT("One shared team score decides it") }
			};
			Team.Cards =
			{
				{ TEXT("About"), { TEXT("Modelled on WT team events. Fighters rotate in and out during a bout, and a shared team score decides the match.") } },
				{ TEXT("Fighters"), { TEXT("Teams are built from the premade men’s and women’s fighters.") } }
			};
			Result.Add(EOpenStanceMenuScreen::Team, Team);

			FListDefinition Challenges;
			Challenges.Kicker = TEXT("Play");
			Challenges.Title = TEXT("Challenges");
			Challenges.Items =
			{
				{ TEXT("Win the Round from 5 Points Down"), TEXT("30 seconds left") },
				{ TEXT("Score a Spin Hook Kick"), TEXT("Right after switching sides") },
				{ TEXT("Counter Three Kicks in One Round"), TEXT("Sample") },
				{ TEXT("Finish a Round with No Penalties"), TEXT("Sample") }
			};
			Challenges.Cards =
			{
				{ TEXT("Medals"), { TEXT("Each challenge awards a medal. Medals unlock cosmetics.") } },
				{ TEXT("Scenarios"), { TEXT("Short scenarios with a goal. The first two are from the design; the others are samples.") } }
			};
			Result.Add(EOpenStanceMenuScreen::Challenges, Challenges);

			FListDefinition Online;
			Online.Kicker = TEXT("Connected");
			Online.Title = TEXT("Online");
			Online.Items =
			{
				{ TEXT("Casual Match"), TEXT("Quick match") },
				{ TEXT("Private Room"), TEXT("Invite code, rematch") },
				{ TEXT("Ranked"), TEXT("Seasons with a skill rating, Equal Terms on") },
				{ TEXT("Community Tournaments"), TEXT("Brackets and check-in") },
				{ TEXT("Clubs"), TEXT("Online dojangs, ladders, club vs club") }
			};
			Online.Cards =
			{
				{ TEXT("Season Rank"), { TEXT("Silver II · rating 1,540 (sample). Shown on a nameplate, never as a belt.") } },
				{ TEXT("Fair Play"), { TEXT("Disconnect penalties, report tools, name and emblem moderation. PC and consoles share one player pool.") } }
			};
			Result.Add(EOpenStanceMenuScreen::Online, Online);

			FListDefinition Replays;
			Replays.Kicker = TEXT("Connected");
			Replays.Title = TEXT("Replays");
			Replays.Items =
			{
				{ TEXT("Chung 14–7 Hong"), TEXT("Club Dojang · Today") },
				{ TEXT("Chung 9–11 Hong"), TEXT("National Arena · Yesterday") },
				{ TEXT("Chung 12–2 Hong"), TEXT("Training Dojang · 2 Days Ago") }
			};
			Replays.Cards =
			{
				{ TEXT("Viewer"), { TEXT("Saved matches replay from inputs and scoring events, with a free camera, slow motion and clips of scoring exchanges.") } },
				{ TEXT("Photo Mode and Sharing"), { TEXT("Take a photo at any moment of a replay, then share it.") }, true }
			};
			Result.Add(EOpenStanceMenuScreen::Replays, Replays);

			FListDefinition Broadcast;
			Broadcast.Kicker = TEXT("Connected");
			Broadcast.Title = TEXT("Broadcast");
			Broadcast.Items =
			{
				{ TEXT("Director Camera"), FString() },
				{ TEXT("Live Scoreboard Overlays"), FString() },
				{ TEXT("Instant Replay"), FString() },
				{ TEXT("Bracket Display"), FString() }
			};
			Broadcast.Cards = { { TEXT("About"), { TEXT("Spectator and commentator tools for community tournaments.") } } };
			Result.Add(EOpenStanceMenuScreen::Broadcast, Broadcast);

			FListDefinition LongTerm;
			LongTerm.Kicker = TEXT("Career");
			LongTerm.Title = TEXT("Long-Term Career");
			LongTerm.Items =
			{
				{ TEXT("Age Divisions"), TEXT("Cadet 12–14, junior 15–17, senior") },
				{ TEXT("Aging"), TEXT("Peak years, gradual decline, retirement") },
				{ TEXT("Fatigue and Minor Injuries"), TEXT("Rest and physio choices, never graphic") },
				{ TEXT("Hall of Fame"), TEXT("Records, medals, signature techniques") },
				{ TEXT("World Games"), TEXT("Career tier 7, every four years") }
			};
			LongTerm.Cards =
			{
				{ TEXT("Hall of Fame"), { TEXT("Retired fighters’ records, medals and signature techniques are kept here.") } },
				{ TEXT("Aging"), { TEXT("Attributes peak, then decline gradually over a long Career.") } }
			};
			Result.Add(EOpenStanceMenuScreen::LongTerm, LongTerm);
			return Result;
		}();

		return Lists.Find(Screen);
	}

	const TArray<FControlTab>& GetControlTabs()
	{
		static const TArray<FControlTab> Tabs =
		{
			MakeTab(TEXT("Movement and Guards"), TEXT("Action"), TEXT("Input"), TEXT("Notes"),
			{
				MakeControl(TEXT("Movement"), TEXT("LS"), TEXT("Move around the mat")),
				MakeControl(TEXT("Switch Sides"), TEXT("A"), TEXT("Swap lead and back leg")),
				MakeControl(TEXT("Dash / Clinch"), TEXT("B"), TEXT("Dash 1 m; dashing into contact starts a clinch")),
				MakeControl(TEXT("High Guard"), TEXT("D-pad ↑"), TEXT("")),
				MakeControl(TEXT("Cross Guard"), TEXT("D-pad ←"), TEXT("")),
				MakeControl(TEXT("Mixed Guard"), TEXT("D-pad →"), TEXT("")),
				MakeControl(TEXT("Low Guard"), TEXT("D-pad ↓"), TEXT("A normal guard, never a foul"))
			}),
			MakeTab(TEXT("Modifiers"), TEXT("Modifier"), TEXT("Input"), TEXT("Effect"),
			{
				MakeControl(TEXT("Back Leg"), TEXT("Hold RT"), TEXT("Throw with the back leg")),
				MakeControl(TEXT("Head"), TEXT("Hold RB"), TEXT("Aim at the head, not the trunk")),
				MakeControl(TEXT("Fake"), TEXT("Hold LB"), TEXT("Feint; see the Fakes tab for each kick")),
				MakeControl(TEXT("Jump"), TEXT("Tap Y before the kick"), TEXT("Throw the kick airborne")),
				MakeControl(TEXT("Active Defense"), TEXT("Hold LT"), TEXT("RS defends instead of attacks")),
				MakeControl(TEXT("Stand or Slide"), TEXT("LS neutral or held"), TEXT("Neutral roots you; held slides you"))
			}),
			MakeTab(TEXT("Standing Kicks"), TEXT("Technique"), TEXT("Input"), TEXT("Points"),
			{
				MakeControl(TEXT("Side Kick"), TEXT("RS ↑"), TEXT("Body 2 · Head 3")),
				MakeControl(TEXT("Side Kick, Back Leg"), TEXT("Hold RT + RS ↑"), TEXT("Body 2 · Head 3")),
				MakeControl(TEXT("Roundhouse"), TEXT("RS ←/→ toward the lead leg"), TEXT("Body 2")),
				MakeControl(TEXT("Roundhouse, Back Leg"), TEXT("Hold RT + RS ←/→ toward the back leg"), TEXT("Body 2 · Head 3")),
				MakeControl(TEXT("Roundhouse, Head"), TEXT("Hold RB + RS ←/→ toward the lead leg"), TEXT("Head 3")),
				MakeControl(TEXT("Hook Kick"), TEXT("RS ←/→ away from the lead leg"), TEXT("Body 2 · Head 3")),
				MakeControl(TEXT("Axe Kick"), TEXT("RS ←/→ {qf}, ↓"), TEXT("Head 3"))
			}),
			MakeTab(TEXT("Spinning and Jump Kicks"), TEXT("Technique"), TEXT("Input"), TEXT("Points"),
			{
				MakeControl(TEXT("Spin Side Kick"), TEXT("RS ↓, ↑"), TEXT("Body 4 · Head 6")),
				MakeControl(TEXT("Spin Hook Kick"), TEXT("Hold RT + RS ←/→ {h}"), TEXT("Body 4 · Head 6")),
				MakeControl(TEXT("Tornado Kick"), TEXT("Y, RS ←/→ {h}, {hu}"), TEXT("Body 4 · Head 6")),
				MakeControl(TEXT("Jump Side Kick"), TEXT("Y, RS ↑"), TEXT("Body 2 · Head 3")),
				MakeControl(TEXT("Jump Roundhouse"), TEXT("Y, RS ←/→ toward the lead leg"), TEXT("Body 2 · Head 3")),
				MakeControl(TEXT("Jump Hook Kick"), TEXT("Y, RS ←/→ away from the lead leg"), TEXT("Body 2 · Head 3")),
				MakeControl(TEXT("Jump Axe Kick"), TEXT("Y, RS ←/→ {qf}, ↓"), TEXT("Head 3")),
				MakeControl(TEXT("Jump Spin Hook"), TEXT("Y, Hold RT + RS ←/→ {h}"), TEXT("Body 4 · Head 6"))
			}),
			MakeTab(TEXT("Fakes"), TEXT("Fake"), TEXT("Input"), TEXT("Result"),
			{
				MakeControl(TEXT("Fake, No Kick"), TEXT("Hold LB"), TEXT("Feint without choosing a kick")),
				MakeControl(TEXT("Fake Side Kick"), TEXT("Hold LB + RS ↑"), TEXT("Startup plays, no score")),
				MakeControl(TEXT("Fake Roundhouse"), TEXT("Hold LB + RS ←/→ toward the lead leg"), TEXT("Startup plays, no score")),
				MakeControl(TEXT("Fake Hook Kick"), TEXT("Hold LB + RS ←/→ away from the lead leg"), TEXT("Startup plays, no score")),
				MakeControl(TEXT("Fake Axe Kick"), TEXT("Hold LB + RS ←/→ {qf}, ↓"), TEXT("Startup plays, no score")),
				MakeControl(TEXT("Fake Spin Side Kick"), TEXT("Hold LB + RS ↓, ↑"), TEXT("Startup plays, no score")),
				MakeControl(TEXT("Fake Spin Hook Kick"), TEXT("Hold LB + RT + RS ←/→ {h}"), TEXT("Startup plays, no score")),
				MakeControl(TEXT("Fake Tornado Kick"), TEXT("Y, Hold LB + RS ←/→ {h}, {hu}"), TEXT("Startup plays, no score")),
				MakeControl(TEXT("Fake a Jump Kick"), TEXT("Y, Hold LB + the kick’s RS input"), TEXT("Startup plays, no score"))
			}),
			MakeTab(TEXT("Punches and Defense"), TEXT("Action"), TEXT("Input"), TEXT("Effect"),
			{
				MakeControl(TEXT("Punch"), TEXT("X"), TEXT("Trunk 1 point")),
				MakeControl(TEXT("High Block"), TEXT("Hold LT, RS ↑"), TEXT("Stops head-height attacks")),
				MakeControl(TEXT("Body Block"), TEXT("Hold LT"), TEXT("Blocks punches and body kicks")),
				MakeControl(TEXT("Leg Check"), TEXT("Hold LT, RS ↓"), TEXT("Stops a body kick; held too long is a penalty")),
				MakeControl(TEXT("Sway or Step"), TEXT("Hold LT, RS ←/→"), TEXT("Move out of range, no block"))
			}),
			MakeTab(TEXT("Referee Mode"), TEXT("Action"), TEXT("Input"), TEXT("Command"),
			{
				MakeControl(TEXT("Move, Look"), TEXT("LS, RS"), TEXT("Step around the fighters")),
				MakeControl(TEXT("Select a Fighter"), TEXT("LB for Chung, RB for Hong"), TEXT("")),
				MakeControl(TEXT("Start or Continue"), TEXT("A"), TEXT("SHI-JAK, KYE-SOK")),
				MakeControl(TEXT("Break"), TEXT("B"), TEXT("KAL-YEO")),
				MakeControl(TEXT("Penalty"), TEXT("Hold X, RS, release"), TEXT("GAM-JEOM, reason on the wheel")),
				MakeControl(TEXT("Stop"), TEXT("Y"), TEXT("KEU-MAN")),
				MakeControl(TEXT("Knockdown Count"), TEXT("Hold LT"), TEXT("")),
				MakeControl(TEXT("Raise the Winner’s Hand"), TEXT("RT"), TEXT("After the final KEU-MAN")),
				MakeControl(TEXT("Attention, Bow, Ready"), TEXT("D-pad ↑, D-pad ↓"), TEXT("CHARYEOT, KYEONGRYE, JOON-BI"))
			}, true)
		};
		return Tabs;
	}

	int32 FindControlTab(const FString& Name)
	{
		return GetControlTabs().IndexOfByPredicate([&Name](const FControlTab& Tab) { return Tab.Name == Name; });
	}
}
