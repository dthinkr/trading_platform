import random
from typing import TypeVar, List

T = TypeVar('T')

def pick_random_element(input_list: List[T]) -> T:
    """
    Pick an element where the selection is determined by the elements themselves,
    not their positions. Same elements will always generate the same selection.
    """
    if not input_list:
        raise ValueError("Cannot pick from an empty list")
    
    element_scores = []
    for element in input_list:
        random.seed(str(element) + "1234")
        element_scores.append((random.random(), element))
    
    return max(element_scores)[1]

def main():
    try:
        list1 = [400, 200, 201, 220]
        list2 = [200, 400, 223, 201]
        
        print("=== List 1 ===")
        print(f"Original: {list1}")
        picked1 = pick_random_element(list1)
        print(f"Picked: {picked1}")
        
        print("\n=== List 2 ===")
        print(f"Original: {list2}")
        picked2 = pick_random_element(list2)
        print(f"Picked: {picked2}")
        
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()