def parse_matchup(matchup):
    # Handle BYE or W/O directly
    if "BYE" in matchup:
        bye_match = re.search(r"(.*?\(.*?\))\(Challenger\)|\(Challenger\)(.*?\(.*?\))", matchup)
        challenger = bye_match.group(1) or bye_match.group(2) if bye_match else "Unknown"
        return {"Challenger": challenger.strip(), "Opponent": "BYE", "Score": "No Score", "Ends": "N/A"}
    if "W/O" in matchup:
        wo_match = re.search(r"(.*?\(.*?\))W/O(.*?\(.*?\))\(Challenger\)", matchup)
        if wo_match:
            opponent = wo_match.group(1).strip()
            challenger = wo_match.group(2).strip()
            return {"Challenger": challenger, "Opponent": opponent, "Score": "Walkover", "Ends": "N/A"}

    # Identify the challenger
    challenger_match = re.search(r"(.*?\(.*?\))\(Challenger\)", matchup)
    challenger = challenger_match.group(1).strip() if challenger_match else "Unknown"

    # Clean up matchup to remove (Challenger) for next parsing
    matchup_cleaned = re.sub(r"\(Challenger\)", "", matchup)

    # Extract names and score
    score_match = re.search(r"(\d+)\s*-\s*(\d+)", matchup)
    ends_match = re.search(r"Ends:\s*(\d+)", matchup)
    ends = ends_match.group(1) if ends_match else "N/A"

    if score_match:
        score1 = score_match.group(1)
        score2 = score_match.group(2)
        # Determine order: find out if challenger score comes first or second
        parts = re.split(r"\d+\s*-\s*\d+", matchup_cleaned)
        if len(parts) == 2:
            first_player = parts[0].strip()
            second_player = parts[1].strip()
            if challenger in first_player:
                score = f"{score1} - {score2}"
                opponent = second_player
            else:
                score = f"{score2} - {score1}"
                opponent = first_player
        else:
            score = f"{score1} - {score2}"
            opponent = "Unknown"
    else:
        # No score given; identify opponent via 'V'
        opponent_match = re.search(r"(.*?\(.*?\))\s*V\s*(.*?\(.*?\))", matchup_cleaned)
        if opponent_match:
            p1 = opponent_match.group(1).strip()
            p2 = opponent_match.group(2).strip()
            opponent = p2 if p1 == challenger else p1
        else:
            opponent = "Unknown"
        score = "No Score"

    return {
        "Challenger": challenger,
        "Opponent": opponent,
        "Score": score,
        "Ends": ends
    }
