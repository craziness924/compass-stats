# for making better output file names
import os.path

# loading data and config
import csv
import yaml

# for making ISO datetime strings for GIS
import datetime

# makes geolocating a given place a one-and-done affair
from functools import lru_cache

# for exporting results to GIS and spreadsheets
import geopandas as gpd
import pandas as pd
from shapely import Point

# for plots
from plots import plot_stats

yaml_file = open("config.yaml")
CONFIG = yaml.safe_load(yaml_file)
yaml_file.close()

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
    STOPS_FILE = CONFIG["files"]["stops"]

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
        t_list.append(t)

    csv_file.close()

    return t_list

# given a stop number or station name, return a Place object
@lru_cache(maxsize=128)
def geolocate_place(name: str) -> Place:
    # we're dealing with a bus tap-in
    if "Bus" in name:
        stop_code = name.split("Bus Stop ")[1]

        try:
            stop_id = STOPS_LIST[stop_code]["stop_id"]
            proper_name = STOPS_LIST[stop_code]["stop_name"]
            lat = STOPS_LIST[stop_code]["stop_lat"]
            long = STOPS_LIST[stop_code]["stop_lon"]

            place = Place(stop_code, stop_id, proper_name, lat, long)
        except KeyError:
            print(f"Error finding {name}! (couldn't find stop_code in stops.txt)")
            place = Place(-1, -1, "N/A", lat=0, long=0)
        return place
    # we're dealing with a station tap
    elif "Stn" in name or "Station" or "Quay" in name:
        station_name = name.split(" ")[0]
        
        if "Port" in name:
            station_name += f" {name.split(' ')[1]}"

            # Moody Centre's WCE station is called Port Moody and 
            # there's no Port Moody in stops.txt
            if station_name == "Port Moody":
                station_name = "Moody Centre"

        for s, v in STOPS_LIST.items():
            # train station type locations (including Lonsdale Quay) have a location_type of 1
            # buses use location_type 0
            if v["location_type"] != "1":
                continue

            i = v["stop_name"].find(station_name)
            
            # no match in stop_name so not the correct place
            if i == -1:
                continue
            
            # indicates we're at a bus bay/platform/WCE version of a train station
            # skip it and continue to the just train one
            if v["parent_station"] != '':
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
    elif "Web Order" in s:
        return ("Purchase", Place(None, None, "Internet", lat=49.28557, long=-123.11171))
    elif "AutoLoaded" in s:
        return("Loaded", Place(None, None, "Internet", lat=49.28557, long=-123.11171))
    
    place: Place = geolocate_place(split[1])

    # return action, proper station/stop name, and geometry
    return (split[0], place)
 
def calculate_stats(tap_list):
    stats = {}
    # summary of all the things that you've done
    stats["actions"] = {}
    # taps but with proper actions and coordinates
    stats["refined-taps"] = []
    # all taps in a journey into a nice neat array
    stats["journeys"] = {}
    # breakdown of actions in each place
    stats["place-breakdown"] = {}
    # summary of money spent, refunded, etc.
    stats["money"] = {}
    # a geodataframe (eventually)
    stats["gdf"] = None
    # the geometry for the gdf we'll eventually make
    gdf_geom = []

    for t in tap_list:
        # find action and create Place object of tap
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

        # create a refined tap list with more useful fields
        new_tap = t

        py_dt = datetime.datetime.strptime(t["DateTime"], "%b-%d-%Y %I:%M %p")
        new_tap["iso-datetime"] = py_dt.isoformat()

        new_tap["action"] = action

        new_tap["stop_id"] = place.stop_id
        new_tap["stop_code"] = place.stop_code
        new_tap["proper_name"] = place.proper_name

        new_tap["lat"] = place.lat
        new_tap["long"] = place.long

        new_tap["zone_id"] = t

        gdf_geom.append(place.geometry)
        
        stats["refined-taps"].append(new_tap)

        # setup place breakdown
        stats["place-breakdown"].setdefault(place.proper_name, {})
        stats["place-breakdown"][place.proper_name].setdefault(action, 0)

        stats["place-breakdown"][place.proper_name][action] += 1 

        # setup money stats
        stats["money"].setdefault("spent", 0)
        stats["money"].setdefault("loaded", 0)

        amnt = t["Amount"].split("$")
        if amnt[0] == "-":
            amnt = -1*float(amnt[1])
        else:
            amnt = float(amnt[1])

        tap_expenditure = 0
        # spent amounts are expressed as negative in the Compass csv export
        if amnt < 0:
            tap_expenditure = amnt
            stats["money"]["spent"] += tap_expenditure
        if amnt > 0:
            # money was genuinely loaded via payment
            if action == "Purchase" or action == "Loaded":
                stats["money"]["loaded"] += amnt
            # money was refunded for a trip at tap out time
            # this is necessary because Compass reserves money for full trip ahead of time
            elif action == "Tap out":
                tap_expenditure += -amnt
                stats["money"]["spent"] += -amnt

        # "loaded" and "purchased" action doesn't have a JourneyId associated, ignore it
        if action not in ["Loaded", "Purchase"]:
            stats["journeys"].setdefault(t["JourneyId"], {})

            journey = stats["journeys"][t["JourneyId"]]

            journey.setdefault("taps", [])
            journey["taps"].append(new_tap)

            # the amount that was actually spent on this journey, according to Compass
            journey["actualSpend"] = tap_expenditure

            # the amount that this app thinks the journey should've cost
            #journey["calculatedSpend"] = 0
            pass
        
    stats["gdf"] = gpd.GeoDataFrame(data=stats["refined-taps"], geometry=gdf_geom, crs="EPSG:4326")
    return stats

if __name__ == "__main__":        
    csv_files = CONFIG["files"]["csv"]

    all_stats = {}

    for c_f in csv_files:
        taps = load_tap_list(c_f)
        stats = calculate_stats(taps)
        all_stats[c_f] = stats


        # # TODO: remove eventually
        # print(f"{c_f}: {stats['actions']} {stats['money']} {stats['place-breakdown']}\n")

        OUTPUT_DIR = CONFIG["output_dir"]

        # remove original directory of data file from filename
        output_name = os.path.split(c_f)[1]
        # remove extension of original filename
        output_name = os.path.splitext(output_name)[0]
        
        output_name = os.path.join(OUTPUT_DIR, output_name)

        os.makedirs(OUTPUT_DIR, exist_ok=True)

        if (CONFIG["outputs"]["save_geojson"]):
            stats["gdf"].to_file(f"{output_name}.geojson")
        if (CONFIG["outputs"]["save_csv"]):
            buh: pd.DataFrame = stats["gdf"].drop("geometry", axis=1)
            buh.to_csv(f"{output_name}-taps.csv", index=False)
        if (CONFIG["outputs"]["show_plots"]) or (CONFIG["outputs"]["save_plots"]):
            plot_stats(stats, 
                        show_plots=CONFIG["outputs"]["show_plots"],
                        save_plots=CONFIG["outputs"]["save_plots"],
                        output_file=output_name)