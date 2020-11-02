# City Plots from OSM 
This tool uses the overpass turbo api to extract the roads and rivers around a specified location and saves it as png. 

## How to use
Edit the location dict and insert the locations you want to have in the center:
 
`locations = [{'name': 'Trump', 'address': 'Oval Office, Washington'}]`

Set the size of the square in km:

` km_distance = 8`
             
Optional: Use the further style parameter in the `main` function to change color and line width. 


## Example
City Plots from OSM
![Example Plot](ExampleOutputs/Trump.png)
_Example 1: The City Plot of Washington with the Oval Office in its center"_

## Requirements
The code was tested with Python 3.6, newer versions should also work. The code was tested for compliance with Windows machines. Use the provided [`requirements.txt`](requirements.txt) in the root directory of this repository, in order to install all required modules.
`pip3 install -r /path/to/requirements.txt`. 
