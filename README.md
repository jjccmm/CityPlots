# City Plots from OSM 
This tool creates beautiful city street plots for any given address.

* [`geopy`](https://geopy.readthedocs.io/): Converts the address to a location
* [`overpy`](https://pypi.org/project/overpy/): Uses the [Overpass-Turbo](https://overpass-turbo.eu/) API to load the city data from [OpenStreetMap](https://www.openstreetmap.org) ([OSM-License](https://www.openstreetmap.org/copyright/en))
* [`utm`](https://pypi.org/project/utm/): Converts the wgs84 coordinates to utm coordinates
* [`matplotlib`](https://matplotlib.org/): Plots the utm coordinates



## How to use
Edit the location dict and insert the locations you want to have in the center:
 
`locations = [{'name': 'Trump', 'address': 'Oval Office, Washington'}]`

Set the size of the square in km:

` km_distance = 8`
             
Optional: Use the further style parameter in the `main` function to change e.g. color and line width. 


## Example
![Example Plot](ExampleOutputs/Trump.png)
_Img 1: The City Plot of Washington with the Oval Office in its center_


![Example Plot](ExampleOutputs/Home.png)
_Img 2: Random address in London_

## Parameter Description
You can change several style parameters regarding color, size, thickness and title. The following image should help you to find the parameters you want to tune. 

![Example Plot](ExampleOutputs/ParameterExample.png)
_Img 3: Description of the Style Parameter_

## Requirements
The code was tested with Python 3.6, newer versions should also work. The code was tested for compliance with Windows machines. Use the provided [`requirements.txt`](requirements.txt) in the root directory of this repository, in order to install all required modules.
`pip3 install -r /path/to/requirements.txt`. 
