import boto3
import csv
import json
import os
import requests

OUTPUT_FILE_POINTS = "fantasy_points.csv"
OUTPUT_FILE_WINS = "fantasy_wins.csv"

def fetch_league_data(id):
    """Fetch paginated league data from Fantasy Premier League API."""
    base_url = f"https://fantasy.premierleague.com/api/leagues-h2h-matches/league/{id}/"
    page = 1
    all_matches = []
    while True:
        url = f"{base_url}?page={page}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        all_matches.extend(data["results"])
        if not data["has_next"]:
            break
        page += 1
    return all_matches

def extract_initials(name):
    """Extract initials from a player's full name."""
    return "".join([part[0].upper() for part in name.split() if part]).strip()

def transform_data(matches):
    """Transform API data into event-based structures for CSV output."""
    event_results_points = {}
    event_results_wins = {}
    player_names = {}

    for match in matches:
        if all(match[key] == 0 for key in ["entry_1_win", "entry_1_draw", "entry_1_loss", "entry_2_win", "entry_2_draw", "entry_2_loss"]):
            continue  # Skip matches that have not been played

        event = match["event"]
        entry_1_id, entry_1_points, entry_1_total = match["entry_1_entry"], match["entry_1_points"], match["entry_1_total"]
        entry_2_id, entry_2_points, entry_2_total = match["entry_2_entry"], match["entry_2_points"], match["entry_2_total"]
        entry_1_initials = extract_initials(match["entry_1_player_name"])
        entry_2_initials = extract_initials(match["entry_2_player_name"])

        player_names[entry_1_id] = entry_1_initials
        player_names[entry_2_id] = entry_2_initials

        if event not in event_results_points:
            event_results_points[event] = {}
            event_results_wins[event] = {}

        event_results_points[event][entry_1_id] = entry_1_points
        event_results_points[event][entry_2_id] = entry_2_points
        event_results_wins[event][entry_1_id] = entry_1_total
        event_results_wins[event][entry_2_id] = entry_2_total

    return event_results_points, event_results_wins, player_names

def apply_cumulative_sum(event_results, player_names):
    """Modify event results to ensure each row accumulates previous event scores."""
    sorted_events = sorted(event_results.keys())
    sorted_players = sorted(player_names.keys())
    cumulative_scores = {name: 0 for name in sorted_players}
    
    for event in sorted_events:
        for player in sorted_players:
            cumulative_scores[player] += event_results[event].get(player, 0)
            event_results[event][player] = cumulative_scores[player]
    
    return event_results

def write_csv(output_file, event_results, player_names, s3_bucket, id):
    """Write cumulative event results to a CSV file and upload to S3."""
    sorted_events = sorted(event_results.keys())
    sorted_players = sorted(player_names.keys())
    file_path = f"/tmp/{output_file}"
    
    with open(file_path, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Event"] + [player_names[p] for p in sorted_players])
        for event in sorted_events:
            row = [event] + [event_results[event].get(p, 0) for p in sorted_players]
            writer.writerow(row)
    
    s3 = boto3.client("s3")
    s3.upload_file(file_path, s3_bucket, 'fantasy/' + id + '/' + output_file, ExtraArgs={'ContentType': 'text/plain'})

def fantasy_handler(config):
    """AWS Lambda entry point."""
    s3_bucket = os.environ.get("S3_BUCKET")
    
    matches = fetch_league_data(config["id"])
    event_results_points, event_results_wins, player_names = transform_data(matches)
    
    event_results_points = apply_cumulative_sum(event_results_points, player_names)
    event_results_wins = apply_cumulative_sum(event_results_wins, player_names)
    
    write_csv(OUTPUT_FILE_POINTS, event_results_points, player_names, s3_bucket, config["id"])
    write_csv(OUTPUT_FILE_WINS, event_results_wins, player_names, s3_bucket, config["id"])
    
    return {"statusCode": 200, "body": "Fantasy complete. CSV files saved to S3."}
