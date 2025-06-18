import os
import sys
import json
import datetime
from firms_data_gen import pull_firms_data
from osm_data_collisions import cluster_points_with_buffer, query_filter_osmnx

def get_input(prompt, allow_empty=False):
    while True:
        value = input(prompt)
        if not value and not allow_empty:
            print('input cannot be empty. please try again.')
        else:
            return value

def get_date(prompt):
    while True:
        date_str = input(prompt)
        try:
            return datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            print('Invalid date format. Please enter date as YYYY-MM-DD.')

def get_api_key(config_path):
    '''
    Retrieve the API key from a local config file or prompt and save it for future use.
    '''
    # Try loading existing key
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                cfg = json.load(f)
            key = cfg.get('firms_api_key')
            if key:
                return key
        except Exception as e:
            print(f'Warning: could not read API key file: {e}')
    # Prompt for key if missing
    key = get_input('your firms API key: ')
    # Ensure directory exists
    config_dir = os.path.dirname(config_path)
    if config_dir and not os.path.exists(config_dir):
        try:
            os.makedirs(config_dir, exist_ok=True)
        except OSError as e:
            print(f'Error creating config dir \'{config_dir}\': {e}')
            sys.exit(1)
    # Save key with restrictive permissions
    try:
        with open(config_path, 'w') as f:
            json.dump({'firms_api_key': key}, f)
        os.chmod(config_path, 0o600)
    except Exception as e:
        print(f'Warning: could not save API key file: {e}')
    return key

def main():
    # Paths
    home = os.path.expanduser('~')
    config_path = os.path.join(home, '.firms_data_config.json')

    # Retrieve or prompt for API key
    firms_api_key = get_api_key(config_path)

    # Gather and validate other inputs
    location = get_input('location: ')
    start_date = get_date('start_date (as YYYY-MM-DD): ')
    end_date = get_date('end_date (as YYYY-MM-DD): ')

    dir_path = get_input('directory path for output data: ')
    try:
        os.makedirs(dir_path, exist_ok=True)
    except OSError as e:
        print(f'Error creating directory \'{dir_path}\': {e}')
        sys.exit(1)

    # Pull and process data
    try:
        firms_df = pull_firms_data(location, str(start_date), str(end_date), firms_api_key)
    except Exception as e:
        print(f'Error pulling firms data: {e}')
        sys.exit(1)

    try:
        firms_df_clusters, firms_bboxes = cluster_points_with_buffer(firms_df)
        osm_x_firms_df, osm_x_firms_df_viz = query_filter_osmnx(firms_bboxes, firms_df_clusters)
    except Exception as e:
        print(f'Error processing OSM data: {e}')
        sys.exit(1)

    # Save data to CSV files
    try:
        base_name = f'{location}_{start_date}-{end_date}'
        firms_df_clusters.to_csv(os.path.join(dir_path, f'{base_name}_firms_data.csv'), index=False)
        osm_x_firms_df.to_csv(os.path.join(dir_path, f'{base_name}_osm_data.csv'), index=False)
        osm_x_firms_df_viz.to_csv(os.path.join(dir_path, f'{base_name}_osm_data_viz.csv'), index=False)
    except Exception as e:
        print(f'Error saving data files: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()
