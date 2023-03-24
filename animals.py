from deca.ff_rtpc import rtpc_from_binary, RtpcNode
from typing import List, Optional, Tuple
from datetime import date
from pathlib import Path
from enum import Enum
import numpy as np
import re
import json

animal_levels = json.load(Path("animal_levels.json").open())
animal_diamonds = json.load(Path("animal_diamonds.json").open())

class Animal:
  def __init__(self, name: str, data: RtpcNode) -> None:
    self.name = name
    self.data = data

class FurVariation:
  def __init__(self, animal_name: str, index: str, type: str, gender: str, rarity: str, prob: float) -> None:
    self.animal_name = animal_name
    self.index = index
    self.type = type
    self.gender = gender
    self.rarity = rarity
    self.prob = prob

class FurVariationGroup:
  def __init__(self, animal_name: str, furs: List[FurVariation]) -> None:
    self.animal_name = animal_name
    self.furs = furs

class AnimalScores:
  def __init__(self, animal_name: str, gender: str, low_score: float, high_score: float, low_weight: float, high_weight: float, data_offset = None) -> None:
    self.animal_name = animal_name
    self.gender = gender
    self.low_score = low_score
    self.high_score = high_score
    self.low_weight = low_weight
    self.high_weight = high_weight
    self.data_offset = data_offset

class Levels(int, Enum):
  TRIVIAL = 1
  MINOR = 2
  VERY_EASY = 3
  EASY = 4
  MEDIUM = 5
  HARD = 6
  VERY_HARD = 7
  MYTHICAL = 8
  LEGENDARY = 9

class AnimalGroupScores:
  level_3_quantile = [0,.57,.95,1]
  level_5_quantile = [0, 0.3, 0.6, 0.8, 0.92, 1]
  level_9_quantile = [0,0.24,0.39,0.58,0.65,0.69,0.74,0.83,.9,1]
  
  def __init__(self, animal_name: str, gendered_scores: List[AnimalScores]) -> None:
    self.animal_name = animal_name
    self.gendered_scores = gendered_scores
    self.level = animal_levels[animal_name]
    self.diamond_low_score = animal_diamonds[animal_name]
    self.diamond_high_score = None
    self.diamond_low_weight = None    
    self.diamond_high_weight = None    
    self.level_values = None    
    
  def __repr__(self) -> str:
    return f"{self.animal_name}({self.level})"
  
  def _lowest_score(self) -> float:
    return min([x.low_score for x in self.gendered_scores])  
  
  def _highest_score(self) -> float:
    return max([x.high_score for x in self.gendered_scores])  
  
  def _lowest_weight(self) -> float:
    return min([x.low_weight for x in self.gendered_scores])  
  
  def _highest_weight(self) -> float:
    return max([x.high_weight for x in self.gendered_scores])
  
  def update_levels(self) -> None:
    lowest_weight = self._lowest_weight()
    highest_weight = self._highest_weight()
    self.diamond_high_score = round(self._highest_score(), 3)
    self.diamond_high_weight = round(highest_weight, 3)
    lowest_weight = round(lowest_weight * 100)
    highest_weight = round(highest_weight * 100)    
    if self.level == 5:
      q = self.level_5_quantile      
    elif self.level == 9:
      q = self.level_9_quantile
    else:
      q = self.level_3_quantile
    cuts = np.quantile(list(range(lowest_weight, highest_weight)), q=q)
    self.diamond_low_weight = round(cuts[-2] / 100, 3)
    level_values = []
    for i in range(len(cuts) - 1):
      level_values.append((round(cuts[i] / 100, 3), round(cuts[i+1] / 100, 3)))
    self.level_values = level_values
    
    
def _group_scores(scores: List[AnimalScores]) -> List[AnimalGroupScores]:
  groups = {}
  for score in scores:
    if score.animal_name in groups:
      existing = groups[score.animal_name]
      existing.gendered_scores.append(score)
    else:
      groups[score.animal_name] = AnimalGroupScores(score.animal_name, [score])
  groups = list(groups.values())
  for group in groups:
    group.update_levels()
  return groups

def _open_rtpc(filename: str) -> RtpcNode:
  with open(filename, 'rb') as f:
    data = rtpc_from_binary(f) 
  root = data.root_node
  return root.child_table[0]  

def _format_name(animal: str) -> str:
  return " ".join([a.capitalize() for a in animal.split("_")])

def _sort_animals(items: list) -> list:
  return sorted(items, key = lambda x: x.animal_name)

def _map_gender(value: int) -> str:
  if value == 0:
    return "both"
  elif value == 1:
    return "male"
  else:
    return "female"

def _show_group_furs(furs: List[FurVariationGroup]) -> None:
  print("###### ANIMAL FURS ######n")
  print(f"(captured on {date.today()})")
  print("(does not include Great Ones)")
  for fur in furs:
    print("\n", _format_name(fur.animal_name))
    for fur_i in fur.furs:
      _pretty_variation(fur_i)
  
def _pretty_variation(fur: FurVariation) -> None:
  gender_flag = ""
  if fur.gender == "male":
    gender_flag = "(male only)"
  elif fur.gender == "female":
    gender_flag = "(female only)"

  print("%5s %-15s %5.2f%% %10s" % (
    "", 
    fur.type, 
    fur.prob,
    gender_flag
  ))  

def _debug_variation(fur: FurVariation) -> None:
  print("%5s %-15s %-7s %-15s %5.2f" % (
    fur.index, 
    fur.type, 
    fur.gender, 
    fur.rarity,
    fur.prob
  ))  

def _pretty_scoring(score: AnimalScores) -> None:  
  print("%10s %8.2f %8.2f %8.2f %8.2f" % (
    score.gender,
    score.low_score,
    score.high_score,
    score.low_weight,
    score.high_weight
  ))    

def _pretty_levels(scores: AnimalGroupScores) -> None:
  print("\n    *** DIFFICULTY RATINGS ***")
  for i in range(scores.level):
    print(f"{Levels(i+1).name:>19s}", end="")
  print()

  for i in range(scores.level):
    x, y = scores.level_values[i]
    value = f"({round(x,1)}, {round(y,1)})"
    print(f"{value:>19s}", end="") 
  print() 

def _show_group_scores(group_scores: List[AnimalGroupScores]) -> None:
  print("###### ANIMAL SCORING #######")
  print(f"(captured on {date.today()})")
  print("(does not include Great Ones)")
  
  for group_score in group_scores:
    print("\n\n",f"{_format_name(group_score.animal_name)}")
    print("    *** GENERAL INFORMATION ***")
    print(f"    LEVEL: {group_score.level}")
    print(f"    Diamond Weight: {group_score.diamond_low_weight}")
    print(f"    Diamond Score: {group_score.diamond_low_score}")
    print()
    print("%10s %8s %8s %8s %8s" % (
      "gender",
      "l_score",
      "h_score",
      "l_weight",
      "h_weight"
    ))       
    print("%10s %8s %8s %8s %8s" % (
      "======",
      "========",
      "========",
      "========",
      "========"
    ))          
    for score in group_score.gendered_scores:
      _pretty_scoring(score)  
    print()
    _pretty_levels(group_score)

def _create_animal_level_dict(scores: List[AnimalGroupScores]) -> None:
  levels = {}
  for score in scores:
    levels[score.animal_name] = 0
  return levels

def _create_animal_details(group_score: AnimalGroupScores) -> dict:
  return {
    "diamonds": {
      "score_low": group_score.diamond_low_score,
      "score_high": group_score.diamond_high_score,
      "weight_low": group_score.diamond_low_weight,
      "weight_high": group_score.diamond_high_weight,
      "furs": {}
    }
  }

def _create_all_animal_details(group_scores: List[AnimalGroupScores]) -> dict:
  animal_details = {}
  for group_score in group_scores:
    animal_details[group_score.animal_name] = _create_animal_details(group_score)
  return animal_details

def _find_child_node(tables: List[RtpcNode], class_name: str, index: int = 0) -> Optional[RtpcNode]:
  for child in tables:
    class_value = child.prop_table[index].data
    if isinstance(class_value, bytes):
      table_class = child.prop_table[index].data.decode("utf-8")
    else:
      continue
    if table_class == class_name:
      return child
  return None

def _find_child_nodes(tables: List[RtpcNode], class_name: str, index: int = 0) -> List[RtpcNode]:
  classes = []
  for child in tables:
    class_value = child.prop_table[index].data
    if isinstance(class_value, bytes):
      table_class = child.prop_table[index].data.decode("utf-8")
    else:
      continue
    if table_class == class_name:
      classes.append(child)   
  return classes

def _get_animals(animal_list: RtpcNode, debug = False) -> List[Animal]:
  animals = []
  for animal in animal_list.child_table:
    LARGE_ANIMAL = 87
    MEDIUM_ANIMAL = 86
    SHORT_ANIMAL = 84
    if animal.prop_count == MEDIUM_ANIMAL:
      animal_name_index = 75
    elif animal.prop_count == LARGE_ANIMAL and isinstance(animal.prop_table[76].data, bytes):
      animal_name_index = 76
    elif animal.prop_count == LARGE_ANIMAL and isinstance(animal.prop_table[75].data, bytes):
      animal_name_index = 75
    elif animal.prop_count == SHORT_ANIMAL:
      animal_name_index = 73
    else:
      if debug:
        print("skipping animal with unknown format", animal.prop_count, animal.data_offset, animal.prop_table[76].data)
      continue
    
    animal_name = animal.prop_table[animal_name_index].data.decode("utf-8")
    if animal_name == "unknown" or animal_name == "homo_sapien":
      continue
    animals.append(Animal(animal_name, animal))
  return animals

def _process_scores(animals: List[Animal], only_animal: str = None, debug = False) -> list:
  animal_scores = []
  for animal in animals:
    if only_animal and animal.name != only_animal:
      continue
    
    score_settings = _find_child_node(animal.data.child_table, "CAnimalTypeScoringSettings")
    if not score_settings:
      if debug:
        print("%5sno score settings found for %10s" % ("", animal.name))
      continue

    distribution_settings = _find_child_nodes(score_settings.child_table, "SAnimalTypeScoringDistributionSettings", index=1)
    LOW_SCORE_INDEX = 0
    HIGH_SCORE_INDEX = 11
    SCORE_TYPE_INDEX = 9
    LOW_WEIGHT_INDEX = 5
    HIGH_WEIGHT_INDEX = 2
    MALE_TYPE = re.compile(r"^male_", re.RegexFlag.I)
    FEMALE_TYPE = re.compile(r"^female_", re.RegexFlag.I)
    GO_TYPE = re.compile(r".*greatone.*", re.RegexFlag.I)

    for distribution_setting in distribution_settings:
      gender = distribution_setting.prop_table[SCORE_TYPE_INDEX].data.decode("utf-8")
      if GO_TYPE.match(gender):
        continue
      elif MALE_TYPE.match(gender):
        gender = "male"
      elif FEMALE_TYPE.match(gender):
        gender = "female"
      else:
        if debug:
          print(f"{gender} is an unknown score type")
          continue
      low_score = distribution_setting.prop_table[LOW_SCORE_INDEX].data
      high_score = distribution_setting.prop_table[HIGH_SCORE_INDEX].data
      low_weight = distribution_setting.prop_table[LOW_WEIGHT_INDEX].data
      high_weight = distribution_setting.prop_table[HIGH_WEIGHT_INDEX].data
      scores = AnimalScores(animal.name, gender, low_score, high_score, low_weight, high_weight, distribution_setting.data_offset)
      animal_scores.append(scores)
  return _sort_animals(animal_scores)

def _process_fur_variations(animals: List[Animal], only_animal: str = None, debug = False) -> List[FurVariationGroup]:
  fur_name = re.compile(r"animal_visual_variation_(\w+)$")

  animal_furs = []
  for animal in animals:
    if only_animal and animal.name != only_animal:
      continue

    visual_settings = _find_child_node(animal.data.child_table, "CAnimalTypeVisualVariationSettings")
    
    gender_index = 0
    LONG_VARIATION = 15
    MEDIUM_VARIATION = 14
    SHORT_VARIATION = 13
    variation_details = []
    male_prob_total = 0
    female_prob_total = 0
    both_prob_total = 0    
    for variation in visual_settings.child_table:
      if MEDIUM_VARIATION == variation.prop_count:
        gender_index = 4
        index_index = 5
        rarity_index = 7
        prob_index = 11
        name_index = 13
      elif SHORT_VARIATION == variation.prop_count:
        gender_index = 3
        index_index = 4
        rarity_index = 6
        prob_index = 10
        name_index = 12      
      elif LONG_VARIATION == variation.prop_count:
        gender_index = 4
        index_index = 5
        rarity_index = 7
        prob_index = 11
        name_index = 14
      else:
        if debug:
          print("skipping variation with unknown format", variation.data_offset)
        continue

      gender = _map_gender(variation.prop_table[gender_index].data)
      index = variation.prop_table[index_index].data
      rarity = variation.prop_table[rarity_index].data
      if rarity == 0:
        rarity = "very common"
      elif rarity == 1:
        rarity = "common"        
      elif rarity == 2:
        rarity = "rare"
      elif rarity == 3:
        rarity = "very rare"
      else:
        rarity = "uknown"
      fur_type = fur_name.match(variation.prop_table[name_index].data.decode("utf-8")).group(1)
      if "great_one" in fur_type:
        continue

      fur_type = _format_name(fur_type)

      prob = variation.prop_table[prob_index].data
      if prob == 0:
        continue

      if gender == "male":
        male_prob_total += prob
      elif gender == "female":
        female_prob_total += prob
      else:
        male_prob_total += prob
        female_prob_total += prob  
      both_prob_total += prob

      variation_details.append(FurVariation(
        animal.name,
        index,
        fur_type,
        gender,
        rarity,
        float(prob)
      ))
    
    for variation in variation_details:
      gender = variation.gender
      prob = variation.prob
      prob_percent = 0
      demoniator = 0
      if gender == "male":
        demoniator = male_prob_total
      elif gender == "female":
        demoniator = female_prob_total
      else:
        demoniator = both_prob_total
      prob_percent = round((prob / demoniator) * 100, 2)
      variation.prob = prob_percent

    furs = {}
    for variation in variation_details:
      fur_already_processed = variation.type in furs      
      if fur_already_processed:
        existing = furs[variation.type]
        furs[variation.type] = FurVariation( 
          animal.name,
          f"{variation.index}+{existing.index}", 
          variation.type,
          "both", 
          variation.rarity, 
          variation.prob
        )
      else: 
        furs[variation.type] = variation
    
    furs = [v for _,v in furs.items()]
    furs = sorted(furs, key = lambda x: x.prob, reverse = True)  
    animal_furs.append(FurVariationGroup(animal.name, furs))
  return _sort_animals(animal_furs)

if __name__ == "__main__":
  animal_list = _open_rtpc("global_animal_types.blo")
  animals = _get_animals(animal_list, True)
  # fur_variations = _process_fur_variations(animals, debug=False)
  # _show_group_furs(fur_variations)
  # scores = _process_scores(animals, only_animal="wild_turkey", debug=False)
  scores = _process_scores(animals, debug=False)
  scores = _group_scores(scores)
  animal_details = _create_all_animal_details(scores)
  # Path("animal_details.json").write_text(json.dumps(animal_details, indent=2))
  _show_group_scores(scores)  
  # Path("levels/global_animals.json").write_text(json.dumps(_create_animal_level_dict(scores), indent=2))  