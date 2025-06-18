# firms data generation

import pandas as pd
import geopandas as gpd
from datetime import datetime, timedelta
import time
from shapely.geometry import Point
import osmnx as ox

### generate location data to filter firms on

def generate_location_filter(location):
    gdf_filter_on = ox.geocode_to_gdf(location)

    return gdf_filter_on

### get list of target dates for the firms collect
def generate_date_list(start_date: str, end_date: str) -> list:
    date_format = '%Y-%m-%d'
    start = datetime.strptime(start_date, date_format)
    end = datetime.strptime(end_date, date_format)

    date_list = []
    current_date = start
    while current_date <= end:
        date_list.append(current_date.strftime(date_format))
        current_date += timedelta(days=1)

    return date_list

### function to pause and retry csv download
def read_csv_with_retry(url, retries= 3, delay= 60):
    for attempt in range(retries):
        try:
            return pd.read_csv(url)
        except Exception as e:
            print(f'Failed to read {url}. Attempt {attempt + 1} of {retries}. Retrying in {delay} seconds...')
            time.sleep(delay)
    raise Exception(f'Failed to read {url} after {retries} attempts')
    
### function to filter csv by gdf
def filter_by_geojson(df, gdf_filter_on):
    # Convert the latitude and longitude to a GeoDataFrame
    geometry = [Point(xy) for xy in zip(df['longitude'], df['latitude'])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry)
    
    # Set the coordinate reference system (CRS) to match the geojson file
    gdf.set_crs(epsg=4326, inplace=True)
    
    # Perform the spatial join to filter the points within the polygons
    gdf_filtered = gpd.sjoin(gdf, gdf_filter_on, how= 'inner', predicate= 'intersects')
    
    # Drop the geometry column and return the result as a DataFrame
    df_filtered = gdf_filtered.drop(columns= ['geometry','osm_id', 'lat', 'lon', 'class', 'type_right', 'place_rank', 'importance', 'addresstype', 'name', 'display_name', 'index_right', 'bbox_north', 'bbox_south', 'bbox_east', 'bbox_west', 'place_id', 'osm_type'])
    
    return df_filtered


### download firms data

def download_firms_data(gdf_filter_on, date_range, firms_api_key):

    outputs = []

    for target_date in date_range:
        try:
            modis_sp = read_csv_with_retry(f'https://firms.modaps.eosdis.nasa.gov/api/area/csv/{firms_api_key}/MODIS_SP/world/1/{target_date}')
            print(f'downloaded modis_sp for {target_date}', end='\r')

            viirs_noaa20 = read_csv_with_retry(f'https://firms.modaps.eosdis.nasa.gov/api/area/csv/{firms_api_key}/VIIRS_NOAA20_NRT/world/1/{target_date}')
            print(f'downloaded viirs_noaa20 for {target_date}', end='\r')
            
            viirs_noaa21 = read_csv_with_retry(f'https://firms.modaps.eosdis.nasa.gov/api/area/csv/{firms_api_key}/VIIRS_NOAA21_NRT/world/1/{target_date}')
            print(f'downloaded viirs_noaa21 for {target_date}', end='\r')

            viirs_snpp_sp = read_csv_with_retry(f'https://firms.modaps.eosdis.nasa.gov/api/area/csv/{firms_api_key}/VIIRS_SNPP_SP/world/1/{target_date}')
            print(f'downloaded viirs_snpp_sp for {target_date}', end='\r')

        except Exception as e:
            print(f'Failed to retrieve data for {target_date}: {e}')
            continue
            
        firms_input = pd.concat([modis_sp, viirs_noaa20, viirs_noaa21, viirs_snpp_sp])
        
        firms_output = filter_by_geojson(firms_input, gdf_filter_on)
        
        if len(firms_output) != 0:
            outputs.append(firms_output)

    ### generate single df of all firms data
    if len(outputs) == 0:
        raise RuntimeError('No FIRMS data found for this location')
    
    firms_df = pd.concat(outputs)

    ### generate unique ids for firms events
    firms_df['event_id'] = ['EVENT_' + str(i).zfill(4) for i in range(1, len(firms_df) + 1)]

    ### format firms acq date/time to timestamps
    firms_df['acq_time'] = firms_df['acq_time'].astype(str).str.zfill(4)

    # Combine date and time into a single string
    firms_df['captured_at'] = pd.to_datetime(
        firms_df['acq_date'] + ' ' + firms_df['acq_time'], 
        format='%Y-%m-%d %H%M'
    )

    return firms_df

def pull_firms_data(location, start_date, end_date, firms_api_key):
    gdf_filter_on = generate_location_filter(location)

    date_range = generate_date_list(start_date, end_date)
    
    firms_df = download_firms_data(gdf_filter_on, date_range, firms_api_key)

    return firms_df