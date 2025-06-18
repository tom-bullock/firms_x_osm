# firms_x_osm
Code to generate OSM data associated with NASA FIRMS observations using OSMnx and the NASA FIRMS API. The code can be run from Terminal and will output three CSVs that can be used for various types of FIRMS analysis.

## Outputs

### firms_data.csv
FIRMS data for selected region and date range.

### osm_data.csv
OSM Ways data that has been effected by a FIRMS observation.

### osm_data_viz.csv
Reduced schema version of osm_data.csv for easy use in visualisations.

## Usage

### Set-up NASA FIRMS API Key
This script requires a FIRMS API key. This can be obtained for free from https://firms.modaps.eosdis.nasa.gov/api/map_key/

### Running the code
Run the code from Terminal (main.py)

For example:

`location: Kharkiv Oblast, Ukraine` <br />
`start_date (as YYYY-MM-DD): 2025-05-01` <br />
`end_date (as YYYY-MM-DD): 2025-05-07` <br />
`directory path for output data: /Users/tom/Desktop/kharkiv_test`

## Applications
The intention behind this code is to allow analysts to easily generate data to support damage assessments for natural disasters, military operations, and other events observable using FIRMS data.

### Battle Damage Assessment, Israeli Strikes on Iran, June 2025

#### Inputs

`location: Iran` <br />
`start_date (as YYYY-MM-DD): 2025-06-13` <br />
`end_date (as YYYY-MM-DD): 2025-06-18` 

Then using Pandas and Matplotlib to generate a breakdown of types of locations that contained FIRMS observations.

![Breakdown of FIRMS observations by OSM site type in Iran](https://github.com/tom-bullock/firms_x_osm/blob/main/israel-iran-strikes.png)

The data can also be used to easily visualise likely airstrikes and what they impacted.

![Visualisation of likely Israeli strikes at the Bandar Imam Power Plant](https://github.com/tom-bullock/firms_x_osm/blob/main/bandar-imam-pp.png)


## Caveats

FIRMS data can contain observations caused by any type of active fire or thermal anomaly so the data will show all types events. FIRMS data is also dependent on clear skies and cloud cover. OSM data is also open-source and does not provide total coverage of locations. It is also updated inconsistently.
