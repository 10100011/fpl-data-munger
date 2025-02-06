import json
import csv
import boto3  # Required for AWS Lambda if storing in S3

# Define S3 bucket details (modify if writing locally)
S3_BUCKET = "fantasy-premier-league-eu-west-1"
INPUT_FILE = "fantasy_draft.json"
OUTPUT_FILE_POINTS = "fantasy_draft_points.csv"
OUTPUT_FILE_WINS = "fantasy_draft_wins.csv"
TMP = "/tmp/"

def load_json(key):
    """Load JSON data from S3 or local file system."""
    # with open(file_path, "r") as file:
        # return json.load(file)
    s3 = boto3.resource("s3")
    obj = s3.Bucket(S3_BUCKET).Object(key)
    jsonStr = obj.get()['Body'].read().decode('utf-8')
    return json.loads(jsonStr)

def transform_data(data):
    """Transform JSON match data into two structured event-wise tables (points & wins)."""

    # Extract league entries and create a mapping of ID → short_name
    league_entries = {entry["id"]: entry["short_name"] for entry in data["league_entries"] if entry["short_name"]}
    
    # Initialize two separate results dictionaries
    event_results_points = {}  # Stores total match points
    event_results_wins = {}    # Stores 3-point win system

    for match in data["matches"]:
        if not match["finished"]:
            continue  # Ignore unfinished matches

        event = match["event"]
        comp1_id, comp1_points = match["league_entry_1"], match["league_entry_1_points"]
        comp2_id, comp2_points = match["league_entry_2"], match["league_entry_2_points"]

        # Get short names
        comp1_name = league_entries.get(comp1_id)
        comp2_name = league_entries.get(comp2_id)

        if not comp1_name or not comp2_name:
            continue  # Skip if IDs are not found in league_entries

        # Initialize event row if not present
        if event not in event_results_points:
            event_results_points[event] = {name: 0 for name in league_entries.values()}
            event_results_wins[event] = {name: 0 for name in league_entries.values()}

        # Add total match points (first CSV)
        event_results_points[event][comp1_name] += comp1_points
        event_results_points[event][comp2_name] += comp2_points

        # Determine winner for the second CSV (win-based scoring)
        if comp1_points > comp2_points:
            event_results_wins[event][comp1_name] += 3
        elif comp2_points > comp1_points:
            event_results_wins[event][comp2_name] += 3
        else:  # If it's a draw, both receive 1 point
            event_results_wins[event][comp1_name] += 1
            event_results_wins[event][comp2_name] += 1

    return event_results_points, event_results_wins, league_entries

def apply_cumulative_sum(event_results, league_entries):
    """Modify event results to ensure each row accumulates previous event scores."""
    sorted_events = sorted(event_results.keys())  # Ensure events are processed in order
    short_names = sorted(league_entries.values())  # Ensure columns remain in consistent order

    cumulative_scores = {name: 0 for name in short_names}  # Initialize cumulative storage

    for event in sorted_events:
        # Add previous event's total to current event
        for name in short_names:
            cumulative_scores[name] += event_results[event].get(name, 0)
            event_results[event][name] = cumulative_scores[name]  # Update event row

    return event_results

def write_csv(output_file, event_results, league_entries):
    """Write the transformed cumulative data to a CSV file."""
    sorted_events = sorted(event_results.keys())  # Sort events in order
    short_names = sorted(league_entries.values())  # Sort columns alphabetically

    with open(output_file, "w", newline="") as file:
        writer = csv.writer(file)  # Comma-separated format

        # Write header row
        writer.writerow(["Event"] + short_names)

        # Write cumulative event rows
        for event in sorted_events:
            row = [event] + [event_results[event].get(name, 0) for name in short_names]
            writer.writerow(row)

    print(f"CSV successfully written to {output_file}")

def lambda_handler(event, context):
    """AWS Lambda entry point."""
    # Load JSON from S3 (modify to local file path for testing)
    json_data = load_json(INPUT_FILE)  # Ensure Lambda has access to JSON
    event_results_points, event_results_wins, league_entries = transform_data(json_data)

    # Apply cumulative sum to both datasets
    event_results_points = apply_cumulative_sum(event_results_points, league_entries)
    event_results_wins = apply_cumulative_sum(event_results_wins, league_entries)

    # Save both CSV outputs
    write_csv(TMP + OUTPUT_FILE_POINTS, event_results_points, league_entries)
    write_csv(TMP + OUTPUT_FILE_WINS, event_results_wins, league_entries)

    # Upload both to S3
    s3 = boto3.client("s3")
    s3.upload_file(TMP + OUTPUT_FILE_POINTS, S3_BUCKET, OUTPUT_FILE_POINTS)
    s3.upload_file(TMP + OUTPUT_FILE_WINS, S3_BUCKET, OUTPUT_FILE_WINS)

    return {"statusCode": 200, "body": f"CSV files written to {S3_BUCKET}/fantasy_draft.csv and {S3_BUCKET}/fantasy_draft_wins.csv"}
