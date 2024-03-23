import matplotlib
import csv



csv_file = open("Fraser Compass Card History - Aug-01-2023 to Mar-04-2024.csv")
dr = csv.DictReader(csv_file)

t_list = []
stats = {}

for t in dr:
    t["DateTime"] = "ba"
    t_list.append(t)

csv_file.close()