from draft import *
from fantasy import *

def get_config(event, key, subkey):
    """Retrieve configuration value from event data."""
    config = event.get(key, None)
    if config:
        config_sub = config.get(subkey, None)
        if (config_sub and config_sub.get('id', None) and config_sub.get('include_total_points', None)):
            return config_sub
    return None

def lambda_handler(event, context):
    draft_h2h = get_config(event, 'draft', 'h2h')
    if draft_h2h:
        draft_handler(draft_h2h)
    fantasy_h2h = get_config(event, 'fantasy', 'h2h')
    if fantasy_h2h:
        fantasy_handler(fantasy_h2h)
    
    return {"statusCode": 200, "body": "Processing complete."}
