# global-population

This is an experimental repository for exploring the global population file in COTW. Right now it can do two things: process the `global_animal_types.blo` RTPC file and extract the fur popularity and animal score range. Limited at the moment, but if the data is indeed accurate, then it is useful.

Check out the `animals.py` file for the main logic. For example, to load the fur rarity:

```python
animal_list = _open_rtpc("global_animal_types.blo")
animals = _get_animals(animal_list, True)
fur_variations = _process_fur_variations(animals, debug=False)
_show_group_furs(fur_variations)
```