# loading data and config
import csv
import yaml

# for making ISO datetime strings for GIS
import datetime

# makes geolocating a given place a one-and-done affair
from functools import lru_cache

# for graphics
import matplotlib.pyplot as plt

# for exporting result to GIS
import geopandas as gpd
from shapely import Point

yaml_file = open("config.yaml")
CONFIG = yaml.safe_load(yaml_file)
yaml_file.close()

STOPS_FILE = CONFIG["files"]["stops"]

class Place():
    def __init__(self, stop_code, stop_id, proper_name, lat, long) -> None:
        # stop_id field included to be able to block stat calculation 
        # of taps at hidden stations since all tappable places have a stop_id
        self.stop_id = stop_id

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

def load_tap_list(file_name):
    csv_file = open(file_name)
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
@lru_cache(maxsize=128)
def geolocate_place(name) -> Place:
    # we're dealing with a bus tap-in
    if "Bus" in name:
        stop_code = name.split("Bus Stop ")[1]

        stop_id = STOPS_LIST[stop_code]["stop_id"]
        proper_name = STOPS_LIST[stop_code]["stop_name"]
        lat = STOPS_LIST[stop_code]["stop_lat"]
        long = STOPS_LIST[stop_code]["stop_lon"]

        place = Place(stop_code, stop_id, proper_name, lat, long)
        return place
    # we're dealing with a station tap
    elif "Stn" in name or "Station" in name:
        station_name = name.split(" ")[0]
        for s, v in STOPS_LIST.items():
            # stations don't have stop_codes, so don't do anything until we find one without a stop_code
            # exception added for WCE stations, which have stop_codes and stop_ids but are not bus stops
            if v["stop_code"] != "" and "WCE" not in v["zone_id"]:
                continue
            i = v["stop_name"].find(station_name)
            
            if i == -1:
                continue

            place = Place(stop_code=None, stop_id=v["stop_id"], proper_name=v["stop_name"], lat=v["stop_lat"], long=v["stop_lon"])
            return place
        else:
            print(f"Couldn't find {name} station!")
            return Place(-1, -1, "N/A", 0, 0)
    else:
        print(f"Don't know how to parse {name}! (couldn't classify it as a bus stop or station)")
        return Place(-1, -1, "N/A", 0, 0)

# given a "Transaction" string, return the action, place, and geometry
def get_action_and_place(s: str) -> tuple[str, Place]:
    split = s.split(" at ")

    # no reasonable place to put a missed tap out, put it at point null
    if s == "Missing Tap out":
        return ("Missed Tap Out", Place(None, None, "N/A", lat=0, long=0))
    # purchased card at the translink customer service centre, use that location
    elif "Purchase" in s and "WalkIn Centre" in s:
        return ("Purchase", Place(None, None, "Customer Service Centre", lat=49.28557, long=-123.11171))
    
    place: Place = geolocate_place(split[1])

    # return action, proper station/stop name, and geometry
    return (split[0], place)
 
def calculate_stats(tap_list):
    stats = {}
    # summary of all the things that you've done
    stats["actions"] = {}
    # taps but with proper actions and Place objects
    stats["refined-taps"] = []
    # summary of money spent, refunded, etc.
    stats["money"] = {}
    # a geodataframe
    stats["gdf"] = gpd.GeoDataFrame()

    for t in tap_list:
        # find place_name then interact with favouriteplaces dict
        action, place = get_action_and_place(t["Transaction"])

        # a stop_id of -1 indicates a failure to find the place
        if place.stop_id == -1:
            continue
        # don't add hidden places to stats!
        elif place.stop_id and place.stop_id in str(CONFIG["hidden-places"]):
            continue

        # if action hasn't been added yet, this will add it with a value of 0
        # if it has been added, it will return the value of the key (which is thrown out)
        stats["actions"].setdefault(action, 0)
        stats["actions"][action] += 1

        # create a refined tap with more useful fields
        new_tap = t

        new_tap["datetime"] = t["DateTime"].isoformat()
        new_tap["action"] = action

        new_tap["stop_id"] = place.stop_id
        new_tap["stop_code"] = place.stop_code
        new_tap["proper_name"] = place.proper_name

        new_tap["lat"] = place.lat
        new_tap["long"] = place.long
        
        stats["refined-taps"].append(new_tap)

    return stats

csv_files = CONFIG["files"]["csv"]

all_stats = {}

for c_f in csv_files:
    taps = load_tap_list(c_f)
    stats = calculate_stats(taps)
    all_stats[c_f] = stats

    # TODO: remove eventually
    print(f"{c_f}: {stats['actions']}")
