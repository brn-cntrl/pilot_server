import json
import inflect

p = inflect.engine()

start = 1059 # Change this to your desired starting number
subtract = 17 # Change this to your desired subtracting number

output = []

current = start

while current > 9:  # stop when it's a single digit
    next_value = current - subtract

    number_str = str(next_value)
    number_words = p.number_to_words(next_value).replace(",", "")
    
    answers = [
        number_str,
        number_words,
        number_words,
        ' '.join([p.number_to_words(digit) for digit in number_str]),
        '-'.join([p.number_to_words(digit) for digit in number_str]),
        ' '.join(list(number_str)),
        ' '.join([c if c != '0' else 'zero' for c in number_str])
    ]
    
    obj = {
        "question": f"{current} - {subtract}",
        "answer": answers
    }
    
    output.append(obj)
    current = next_value

# This will always create a new json file. Change the name to "task_data_1.json" or "task_data_2.json" 
# if you want to overwrite the existing file.
with open("new_questions.json", "w") as f:
    json.dump(output, f, indent=4)

print("Done!")
