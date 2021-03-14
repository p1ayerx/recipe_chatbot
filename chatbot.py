import nltk
import recipe_parser
import validators
import requests
from bs4 import BeautifulSoup
import re
from text_to_num import alpha2digit

while True:
    user = input("User: ")

    tokens = nltk.word_tokenize(user)
    validate = validators.url(user)

    finish_words = ["done", "finish"]
    s = set(tokens)
    if [x for x in finish_words if x in s]:
        print("Bye!")
        break

    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Max-Age': '3600',
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'
    }

    if "recipe" in tokens:
        print("Bot: Sure. Please specify a URL")
    elif validate == True:
        print("Bot: URL: "+user+" Please wait. It may take a while.")

        req = requests.get(user, headers)
        soup = BeautifulSoup(req.content, 'html.parser')

        title = soup.find("h1", class_="headline heading-content").get_text().lstrip().rstrip()

        ingredients_dict,tools_list,methods_list,instructions_lst= recipe_parser.parse_url(user)

        print("Bot: Recipe is "+title)
        recipe_content = True

        ingredient_words = ["ingredients","ingredient"]
        tool_words = ["tool","tools"]
        method_words = ["method","methods"]
        instruction_words = ["instructions","instruction"]
        finish_words = ["done","finish"]
        back_step_words = ["previous","back"]
        next_words = ["next"]
        step_counter = 1

        print("Bot: What do you want to know the ingredients or tools or methods or instructions of the recipe?")

        while recipe_content:
            user = input("User: ")

            tokens = nltk.word_tokenize(user)
            s = set(tokens)
            if [x for x in ingredient_words if x in s]:
                print("Ingredients:")
                for k in ingredients_dict.keys():
                    print("\t" + k + ": " + ingredients_dict[k])
            elif [x for x in tool_words if x in s]:
                print("Tools:")
                for t in tools_list:
                    print("\t" + t)
            elif [x for x in method_words if x in s]:
                for m in methods_list:
                    print("\t" + m)
            elif [x for x in instruction_words if x in s] or [x for x in back_step_words if x in s] or [x for x in next_words if x in s] or "step" in tokens:
                user = alpha2digit(user, "en")
                if "first" in tokens:
                    step_counter = 1
                    print("Bot: Step " + str(step_counter) + ": " + instructions_lst[step_counter - 1])
                elif "second" in tokens:
                    if len(instructions_lst) < 2:
                        print("Bot: Step is out of bounds.")
                        continue
                    step_counter = 2
                    print("Bot: Step " + str(step_counter) + ": " + instructions_lst[step_counter - 1])
                elif "third" in tokens:
                    if len(instructions_lst) < 3:
                        print("Bot: Step is out of bounds.")
                        continue
                    step_counter = 3
                    print("Bot: Step " + str(step_counter) + ": " + instructions_lst[step_counter - 1])
                elif re.search("\d+",user):
                    if len(instructions_lst) >= int(re.search("\d+",user)[0]) > 0:
                        step_counter = int(re.search("\d+",user)[0])
                        print("Bot: Step " + str(step_counter) + ": " + instructions_lst[step_counter - 1])
                    else:
                        print("Bot: Step is out of bounds.")
                elif "next" in tokens:
                    step_counter += 1
                    if step_counter > len(instructions_lst):
                        print("Bot: There are no more steps. There are only "+str(len(instructions_lst))+" steps.")
                        step_counter -= 1
                        continue
                    print("Bot: Step " + str(step_counter) + ": " + instructions_lst[step_counter-1])
                elif [x for x in back_step_words if x in s]:
                    if step_counter == 1:
                        print("Bot: There are no steps before this.")
                        continue
                    step_counter = step_counter - 1
                    print("Bot: Step " + str(step_counter) + ": " + instructions_lst[step_counter - 1])
                else:
                    print("Bot: Step " + str(step_counter) + ": " + instructions_lst[step_counter-1])

            elif [x for x in finish_words if x in s]:
                print("Bot: OK! Next recipe URL.")
                break

            print("Bot: What can I do for you?")