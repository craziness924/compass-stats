import csv
import datetime
import yaml

import matplotlib.pyplot as plt

import geopandas as gpd
from shapely import Point



CSV_FILE = "Fraser Compass Card History - Aug-25-2023 to Mar-03-2024.csv"
CONFIG = yaml.load_all("config.yaml", yaml.BaseLoader)

STOPS_FILE = "stops.txt"

class Place():
    def __init__(self, stop_code, proper_name, lat, long) -> None:
        self.stop_code = stop_code
        self.proper_name = proper_name
        self.lat = lat
        self.long = long
        
        self.geometry = Point(long, lat)

def load_stops():
    stops = {}
    csv_file = open(STOPS_FILE)
    dr = csv.DictReader(csv_file)

    for s in dr:
        # use stop_name if stop_code is unavailable (for non bus-stops), otherwise use stop_code
        if s["stop_code"] == '':
            stops[s["stop_name"]] = s
            pass
        else:
            stops[s["stop_code"]] = s
            pass

    return stops

STOPS_LIST = load_stops()

def load_tap_list():
    csv_file = open(CSV_FILE)
    dr = csv.DictReader(csv_file)

    t_list = []

    for t in dr:
        t["DateTime"] = datetime.datetime.strptime(t["DateTime"], "%b-%d-%Y %I:%M %p")
        
        # could add a timezone but then DST must be accounted for :(
        # t["DateTime"].tzinfo.utcoffset("-7")
        t_list.append(t)

    csv_file.close()

    return t_list

# given a stop number or station name, return a Place object
def geolocate_place(name) -> Place:
    # if it's a bus stuff tap-in then try to use parent station or something
    proper_name = ""
    lat = None
    long = None

    # we're dealing with a bus tap-in
    if "Bus" in name:
        stop_code = name.split("Bus Stop ")[1]
        
        proper_name = STOPS_LIST[stop_code]["stop_name"]
        lat = STOPS_LIST[stop_code]["stop_lat"]
        long = STOPS_LIST[stop_code]["stop_lon"]

        place = Place(stop_code, proper_name, lat, long)
    else:
        pass

    return place

# given a "Transaction" string, return the action, place, and geometry
def get_action_and_place(s: str) -> tuple[str, Place]:
    split = s.split(" at ")

    # no reasonable place to put a missed tap out, discard it
    if s == "Missing Tap out":
        return ("Missed Tap Out", "N/A", Point(0, 0))
    # purchased card at the translink customer service centre, use that location
    elif "Purchase" in s and "WalkIn Centre" in s:
        return ("Purchase", "Customer Service Centre", Point(-123.11171, 49.28557))
    
    place: Place = geolocate_place(split[1])

    # return action, proper station/stop name, and geometry
    return (split[0], place)
 
def calculate_stats(tap_list):
    stats = {}
    stats["General"] = {}
    stats["spatial"] = []

    for t in tap_list:
        # find place_name then interact with favouriteplaces dict
        action_place_geom = get_action_and_place(t["Transaction"])

        pass
    pass

t = load_tap_list()
stats = calculate_stats(t)

