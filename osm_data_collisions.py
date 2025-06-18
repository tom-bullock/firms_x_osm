#### generate bounding boxes based on FIRMS data hits to minimise big searches in OSMNX

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon, MultiPolygon, MultiLineString, MultiPoint
import osmnx as ox
from osmnx._errors import InsufficientResponseError

### osm_tags

tags = {
    'building': True,
    'landuse': True,
    'amenity': True,
    'leisure': True,
    'natural': True,
    'boundary': True,
    'place': True,
    'military': True,
    'man_made': True
}

def cluster_points_with_buffer(firms_df, buffer_m= 3000, grid_size_km= 5):
    # Convert buffer and grid size from meters to degrees
    deg_per_km = 1 / 111.0
    buffer_deg = buffer_m / 1000 * deg_per_km
    grid_size_deg = grid_size_km * deg_per_km

    # Assign each point to a lat/lon grid cell
    firms_df = firms_df.copy()
    firms_df['lat_bin'] = (firms_df['latitude'] // grid_size_deg).astype(float) * grid_size_deg
    firms_df['lon_bin'] = (firms_df['longitude'] // grid_size_deg).astype(float) * grid_size_deg

    # Create a unique set of bins
    bins = firms_df[['lat_bin', 'lon_bin']].drop_duplicates().reset_index(drop=True)
    bins['bbox_id'] = ['bbox_{:05d}'.format(i) for i in range(len(bins))]

    # Merge bbox_id into point data
    firms_df = firms_df.merge(bins, on=['lat_bin', 'lon_bin'], how='left').drop(columns=['lat_bin', 'lon_bin'])

    # Calculate bounding boxes with buffer
    bins['north'] = bins['lat_bin'] + grid_size_deg + buffer_deg
    bins['south'] = bins['lat_bin'] - buffer_deg
    bins['east'] = bins['lon_bin'] + grid_size_deg + buffer_deg
    bins['west'] = bins['lon_bin'] - buffer_deg

    bin_bboxes = bins[['bbox_id', 'north', 'south', 'east', 'west']]

    return firms_df, bin_bboxes

### function to convert osmnx points to polygons with a 25 m buffer

def buffer_non_polygons(gdf, buffer_distance= 25):
    # Reproject to a metric CRS (e.g., UTM or Web Mercator) if needed
    if gdf.crs is None or gdf.crs.to_epsg() != 3857:
        gdf = gdf.to_crs(epsg=3857)

    def buffer_geom(geom):
        if geom is None:
            return None
        if isinstance(geom, (Point, LineString, MultiPoint, MultiLineString)):
            return geom.buffer(buffer_distance)
        elif isinstance(geom, (Polygon, MultiPolygon)):
            return geom
        else:
            return None  # Skip or log unusual geometry types

    gdf = gdf.copy()
    gdf['geometry_back_up'] = gdf['geometry']
    gdf['geometry'] = gdf['geometry'].apply(buffer_geom)

    # Return to original CRS if needed
    return gdf.to_crs(epsg=4326)

def query_filter_osmnx(firms_bboxes, firms_df_clusters, tags= tags):

    outputs = []
    
    for idx, row in firms_bboxes.iterrows():
        bbox_id = row['bbox_id']
        
        print(f'pulling data for {bbox_id}', end= '\r')

        firms_df_clusters_filtered = firms_df_clusters[firms_df_clusters['bbox_id'] == bbox_id]

        north, south, east, west = row['north'], row['south'], row['east'], row['west']

        try:
            gdf_features = buffer_non_polygons(
                ox.features_from_bbox(north, south, east, west, tags)
            ).reset_index()
        except InsufficientResponseError:
            print(f'No data for bbox {bbox_id} with tags {tags}')
            continue  # or handle accordingly
        
        gdf_features = gdf_features[gdf_features['element_type'] == 'way']
        
        points = gpd.GeoDataFrame(
            firms_df_clusters_filtered[['event_id']],  # retain the event_id column
            geometry=[Point(lon, lat) for lat, lon in zip(firms_df_clusters_filtered['latitude'], firms_df_clusters_filtered['longitude'])],
            crs='EPSG:4326'
        )
        
        # Perform spatial join to get the index of polygons that contain the points
        joined = gpd.sjoin(points, gdf_features, how='inner', predicate='within')

        # Group the results by the polygon index and collect all associated event_ids
        event_ids_by_polygon = joined.groupby('index_right')['event_id'].agg(list)

        # Add a new column to gdf_features to store the list of event_ids per polygon
        gdf_features = gdf_features.copy()
        gdf_features['event_ids'] = gdf_features.index.map(event_ids_by_polygon)

        # Optional: filter only the matching polygons with attached event_ids
        matching_polygons = gdf_features.loc[event_ids_by_polygon.index]

        outputs.append(matching_polygons)
    
    osm_x_firms_df = gpd.GeoDataFrame(pd.concat(outputs, ignore_index= False))


    ### reset geometries to originals
    osm_x_firms_df['geometry'] = osm_x_firms_df['geometry_back_up']
    del osm_x_firms_df['geometry_back_up']
    
    ### generate stripped down data version for visuals

    columns_to_keep = [
        'element_type', 'osmid', 'source', 'geometry', 'name', 'landuse', 'man_made', 'event_ids']

    # Filter columns: keep only those that are present in the GeoDataFrame
    osm_x_firms_df_viz = osm_x_firms_df[[col for col in columns_to_keep if col in osm_x_firms_df.columns]]

    return osm_x_firms_df, osm_x_firms_df_viz