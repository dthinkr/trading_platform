import random

def pick_random_element_new(input_list):
    # use seed 2025 for consistent random selection
    if not input_list:
        raise ValueError("cannot pick from empty list")
    random.seed(2025)
    return random.choice(input_list)

