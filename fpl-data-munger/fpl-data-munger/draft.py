import boto3
import csv
import json
import os
import requests

# Define S3 bucket details
S3_BUCKET = os.environ.get('S3_BUCKET')
OUTPUT_FILE_POINTS = "fantasy_draft_points.csv"
OUTPUT_FILE_WINS = "fantasy_draft_wins.csv"
TMP = "/tmp/"

def load_json(id):
    """Load JSON data from a remote HTTPS source."""
    url = "https://draft.premierleague.com/api/league/{id}/details"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def transform_data(data):
    """Transform JSON match data into two structured event-wise tables (points & wins)."""
    league_entries = {entry["id"]: entry["short_name"] for entry in data["league_entries"] if entry["short_name"]}
    event_results_points = {}
    event_results_wins = {}

    for match in data["matches"]:
        if not match["finished"]:
            continue

        event = match["event"]
        comp1_id, comp1_points = match["league_entry_1"], match["league_entry_1_points"]
        comp2_id, comp2_points = match["league_entry_2"], match["league_entry_2_points"]
        comp1_name = league_entries.get(comp1_id)
        comp2_name = league_entries.get(comp2_id)
        if not comp1_name or not comp2_name:
            continue

        if event not in event_results_points:
            event_results_points[event] = {name: 0 for name in league_entries.values()}
            event_results_wins[event] = {name: 0 for name in league_entries.values()}

        event_results_points[event][comp1_name] += comp1_points
        event_results_points[event][comp2_name] += comp2_points
        
        if comp1_points > comp2_points:
            event_results_wins[event][comp1_name] += 3
        elif comp2_points > comp1_points:
            event_results_wins[event][comp2_name] += 3
        else:
            event_results_wins[event][comp1_name] += 1
            event_results_wins[event][comp2_name] += 1

    return event_results_points, event_results_wins, league_entries

def apply_cumulative_sum(event_results, league_entries):
    """Modify event results to ensure each row accumulates previous event scores."""
    sorted_events = sorted(event_results.keys())
    short_names = sorted(league_entries.values())
    cumulative_scores = {name: 0 for name in short_names}
    for event in sorted_events:
        for name in short_names:
            cumulative_scores[name] += event_results[event].get(name, 0)
            event_results[event][name] = cumulative_scores[name]
    return event_results

def write_csv(output_file, event_results, league_entries, id):
    """Write event results to a CSV file and upload to S3."""
    sorted_events = sorted(event_results.keys())
    short_names = sorted(league_entries.values())
    file_path = os.path.join(TMP, output_file)
    
    with open(file_path, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Event"] + short_names)
        for event in sorted_events:
            row = [event] + [event_results[event].get(name, 0) for name in short_names]
            writer.writerow(row)
    
    s3 = boto3.client("s3")
    s3.upload_file(file_path, S3_BUCKET, 'draft/' . id . '/' . output_file, ExtraArgs={'ContentType': 'text/plain'})

def draft_handler(config):
    json_data = load_json(config["id"])
    event_results_points, event_results_wins, league_entries = transform_data(json_data)

    event_results_wins = apply_cumulative_sum(event_results_wins, league_entries)
    write_csv(OUTPUT_FILE_WINS, event_results_wins, league_entries, config["id"])
    
    event_results_points = apply_cumulative_sum(event_results_points, league_entries)
    write_csv(OUTPUT_FILE_POINTS, event_results_points, league_entries, config["id"])
    
    return {"statusCode": 200, "body": "Draft complete. CSV files saved to S3."}
