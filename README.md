# APL - Anime Priority List

## What is APL?

APL is an automated anime watch priority list tool that helps you decide what to watch next from your AniList planning list.

## How does APL work?

APL connects to AniList's API to fetch your anime lists, calculates a priority score for each anime in your planning list, and displays results in a sortable table GUI. No external spreadsheet or Google account needed.

## What is the purpose of APL?

As I have over 250+ anime planning to watch I usually can't decide what to watch first so I created a spreadsheet by hand to sort which anime I should watch first. This program is just to add a quality of life change for me and stop me from staying up making spreadsheets by hand.

## Setup

1. Install Python 3.7+
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `python GUI.py`
4. Enter your AniList username and click **Generate**

CLI mode is also available: `python APL.py`

## Features

- **Sortable table** - click any column header to sort
- **Double-click** any anime to open its AniList page
- **API caching** - responses cached to disk to avoid rate limits (lists: 1hr, relations: 7 days)
- **Clear Cache** button to force fresh data
- **Progress bar** with per-anime status during fetch
- **Sequel detection** with relation type display (e.g. "Sequel of Attack on Titan")
- **All-list matching** - checks COMPLETED, CURRENT, and REPEATING lists for relation matching
- **Save User** persists your username between sessions

***

## APL Score v3

### Factors

**P-Factor (Previous Season)**
Bonus applied when an anime is related to something you've completed or are currently watching. Uses the highest-weighted matching relation.

| Relation Type | Bonus |
|---------------|-------|
| Sequel        | 0.15  |
| Prequel       | 0.10  |
| Side Story    | 0.08  |
| Parent        | 0.08  |
| Spin Off      | 0.05  |
| Alternative   | 0.03  |
| Character     | 0.02  |

**B-Factor (Bingability)**
Bonus based on episode count - shorter anime are easier to commit to.

| Episodes | Bonus                        |
|----------|------------------------------|
| 1-13     | 0.06                         |
| 14-26    | (score - 70) x 0.002, min 0  |
| 27-52    | (score - 80) x 0.001, min 0  |
| 53+      | 0                            |

### Formula

```text
APL = Score x (1 + P x 0.6 + B x 0.4)
```

- **Score** = AniList average score (0-100)
- **P** = Previous season factor (0 to 0.15)
- **B** = Bingability factor (0 to 0.06)
- P-weight = 0.6 (sequel bonus weighted higher as a stronger recommendation signal)
- B-weight = 0.4

***

## Caching

API responses are cached locally in `.cache/` to avoid rate limiting:

- **User list data**: cached for 1 hour
- **Relation data**: cached for 7 days (anime relations rarely change)
- Use the **Clear Cache** button or delete the `.cache/` folder to force fresh data

***

## WIP / Future Ideas

- [ ] Export table to CSV
- [ ] Include movies, OVAs, and ONAs in planning list (currently TV/TV_SHORT only)
- [ ] Popularity factor - weight by AniList popularity/trending data
- [ ] User score influence - factor in personal scores from completed anime when boosting sequels
- [ ] Configurable weights - let users adjust P/B weights and thresholds in the GUI
- [ ] Genre preference scoring - learn preferred genres from completed list
- [ ] Seasonal filter - option to filter by release season/year
- [ ] Multi-user comparison - compare planning lists between friends
- [ ] Airing status support - include currently airing anime with estimated completion
- [ ] Discord bot

***

## Changelog

### v3

- Removed Google Sheets dependency - results displayed in built-in sortable table
- Added disk-based API caching to avoid rate limits
- Fetches all lists in a single API call (was 2 separate calls)
- Relation queries now fetch for planning anime instead of all completed anime
- Added relation type detection (SEQUEL, PREQUEL, SIDE_STORY, etc.) with weighted scoring
- Fixed bFactor: short anime (1-13 eps) now correctly get highest bingability bonus
- Fixed useless loop bugs in bFactor and aplCalc functions
- Rebalanced weights: P-Factor 0.6 / B-Factor 0.4 (sequel signal weighted higher)
- Added progress bar and error handling in GUI
- Dark themed UI with clickable AniList links
- CLI mode prints formatted table

### v2

- Initial Google Sheets integration
- Basic APL scoring with bFactor and pFactor
