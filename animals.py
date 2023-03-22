from deca.ff_rtpc import rtpc_from_binary, RtpcNode
from typing import List, Optional
from datetime import date
import re

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
  def __init__(self, animal_name: str, gender: str, low_score: float, high_score: float, data_offset = None) -> None:
    self.animal_name = animal_name
    self.gender = gender
    self.low_score = low_score
    self.high_score = high_score
    self.data_offset = data_offset

class AnimalGroupScores:
  def __init__(self, animal_name: str, scores: List[AnimalScores]) -> None:
    self.animal_name = animal_name
    self.scores = scores

def _group_scores(scores: List[AnimalScores]) -> List[AnimalGroupScores]:
  groups = {}
  for score in scores:
    if score.animal_name in groups:
      existing = groups[score.animal_name]
      existing.scores.append(score)
    else:
      groups[score.animal_name] = AnimalGroupScores(score.animal_name, [score])
  return groups.values()

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

def _show_group_scores(scores: List[AnimalGroupScores]) -> None:
  print("###### ANIMAL SCORING ######n")
  print(f"(captured on {date.today()})")
  print("(does not include Great Ones)")
  print(f"\n(gender, low_score, high_score)")
  for score in scores:
    print("\n",_format_name(score.animal_name))
    for score_i in score.scores:
      _pretty_scoring(score_i)

def _pretty_scoring(score: AnimalGroupScores) -> None:  
  print("%10s %8.2f %8.2f" % (
    score.gender,
    score.low_score,
    score.high_score
  ))      

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
      scores = AnimalScores(animal.name, gender, low_score, high_score, distribution_setting.data_offset)
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
  fur_variations = _process_fur_variations(animals, debug=False)
  _show_group_furs(fur_variations)
  # scores = _process_scores(animals, debug=False)
  # scores = _group_scores(scores)
  # _show_group_scores(scores)