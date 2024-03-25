import csv
import datetime
import yaml

import matplotlib.pyplot as plt

import geopandas as gpd
from shapely import Point



CSV_FILE = "Fraser Compass Card History - Aug-25-2023 to Mar-03-2024.csv"
STOPS_FILE = ""
CONFIG = yaml.load_all("config.yaml", yaml.BaseLoader)

def get_tap_list():
    csv_file = open(CSV_FILE)
    dr = csv.DictReader(csv_file)

    t_list = []

    for t in dr:
        t["DateTime"] = datetime.datetime.strptime(t["DateTime"], "%b-%d-%Y %I:%M %p")
        t_list.append(t)

    csv_file.close()

    return t_list

# given a stop number or station name, return the proper name and latitude and longitude
def geolocate_place(name):
    # if it's a bus stuff tap-in then try to use parent station or some thing
    
    proper_name = ""
    lat = None
    long = None

    
    return (proper_name, Point(long, lat))

# given a "Transaction" string, return the action, place, and geometry
def get_action_and_place(s: str):
    split = s.split(" at ")

    # no reasonable place to put a missed tap out, discard it
    if s == "Missing Tap out":
        return ("Missed Tap Out", "N/A", Point(0, 0))
    # purchased card at the translink customer service centre, use that location
    elif "Purchase" in s and "WalkIn Centre" in s:
        return ("Purchase", "Customer Service Centre", Point(-123.11171, 49.28557))
    
    proper_name, point = geolocate_place(split[2])

    # return action, proper station/stop name
    return (split[0], proper_name, )

    
    

def calculate_stats(tap_list):
    stats = {}
    stats["General"] = {}
    stats["spatial"] = []

    for t in tap_list:
        # find place_name then interact with favouriteplaces dict
        action_place_geom = get_action_and_place(t["Transaction"])

        pass

    pass


t = get_tap_list()
stats = calculate_stats(t)

