# loading data and config
import csv
import yaml

# for making ISO datetime strings for GIS
import datetime

# makes geolocating a given place a one-and-done affair
from functools import lru_cache

# for exporting result to GIS
import geopandas as gpd
from shapely import Point

# for plots
from plots import plot_stats

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

        new_tap["iso-datetime"] = t["DateTime"].isoformat()
        new_tap["action"] = action

        new_tap["stop_id"] = place.stop_id
        new_tap["stop_code"] = place.stop_code
        new_tap["proper_name"] = place.proper_name

        new_tap["lat"] = place.lat
        new_tap["long"] = place.long

        gdf_geom.append(place.geometry)
        
        stats["refined-taps"].append(new_tap)

        # setup journeys

        # "loaded" and "purchased" action doesn't have a JourneyId associated, ignore it
        if action not in ["Loaded", "Purchase"]:
            stats["journeys"].setdefault(t["JourneyId"], [])
            stats["journeys"][t["JourneyId"]].append(new_tap)

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

        # spent amounts are expressed as negative in the Compass csv export
        if amnt < 0:
            stats["money"]["spent"] += amnt*-1
        if amnt > 0:
            # money was genuinely loaded via payment
            if action == "Purchase" or action == "Loaded":
                stats["money"]["loaded"] += amnt
            # money was refunded for a trip at tap out time
            # this is necessary because Compass reserves money for full trip ahead of time
            elif action == "Tap out":
                stats["money"]["spent"] += -amnt
                pass
    stats["gdf"] = gpd.GeoDataFrame(data=stats["refined-taps"], geometry=gdf_geom, crs="EPSG:4326")
    print(stats["gdf"].head())
    return stats

csv_files = CONFIG["files"]["csv"]

all_stats = {}

for c_f in csv_files:
    taps = load_tap_list(c_f)
    stats = calculate_stats(taps)
    all_stats[c_f] = stats


    # # TODO: remove eventually
    print(f"{c_f}: {stats['actions']} {stats['money']} {stats['place-breakdown']}\n")

    if (CONFIG["outputs"]["save_geojson"]):
        stats["gdf"].to_file(f"{c_f}.geojson")
    # if (CONFIG["outputs"]["save_csv"]):
    #     stats["gdf"].drop(["DateTime"], axis=1)
    #     stats["gdf"].to_file(f"{c_f}-stats.csv")
    if (CONFIG["outputs"]["show_plots"]):
        plot_stats(stats, CONFIG)