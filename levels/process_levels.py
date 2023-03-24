import re
import json
from pathlib import Path
import pprint

pp = pprint.PrettyPrinter(indent=2)

def _name_to_variable(name: str) -> str:
  return "_".join([x.lower().replace(".", "").replace("-", "") for x in name.split(" ")])

def join_animals(global_source: Path, chart_source: Path, debug: bool = False) -> dict:
  animal_levels = {}
  global_animals = json.load(global_source.open())
  chart_animals = json.load(chart_source.open())
  chart_animal_names = list(chart_animals.keys())
  
  for animal_name, _ in global_animals.items():
    if animal_name in chart_animal_names:
      animal_levels[animal_name] = chart_animals[animal_name]
    else:
      animal_levels[animal_name] = 999999
      
  if debug:
    pp.pprint(animal_levels)
  
  return animal_levels

def process_chart(debug = False) -> dict:
  level = re.compile(r"^LEVEL\s(\d+)$")
  
  levels = {}
  with Path("level_chart.txt").open() as file:
    current_level = 0
    for line in file:
      line = line.rstrip()
      level_match = level.match(line)
      if level_match:
        current_level = level_match.group(1)
        levels[current_level] = []
      else:
        levels[current_level].append(_name_to_variable(line))
  if debug:
    pp.pprint(levels)
  
  animal_levels = {}
  for level, animals in levels.items():
    for animal in animals:
      animal_levels[animal] = int(level)
      
  if debug:
    pp.pprint(animal_levels)
  
  return animal_levels
      
if __name__ == "__main__":
  animal_levels = process_chart(True)
  Path("level_chart_out.json").write_text(json.dumps(animal_levels, indent=2))
  animal_levels = join_animals(Path("global_animals.json"), Path("level_chart_out.json"), True)
  Path("animal_levels.json").write_text(json.dumps(animal_levels, indent=2))
  