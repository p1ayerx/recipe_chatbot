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
        print("Bot:  Sure. Please specify a URL.")
    elif validate == True:
        print("Bot:  Loading recipe from URL. Please wait. It may take a minute.")

        req = requests.get(user, headers)
        soup = BeautifulSoup(req.content, 'html.parser')

        title = soup.find("h1", class_="headline heading-content").get_text().lstrip().rstrip()

        ingredients_dict,tools_list,methods_list,instructions_lst= recipe_parser.parse_url(user)

        print("Bot:  Alright. So let's start working with \"{0}.\" What do you want to do?".format(title))
        recipe_content = True

        ingredient_words = ["ingredients","ingredient"]
        tool_words = ["tool","tools"]
        method_words = ["method","methods"]
        instruction_words = ["instructions","instruction","no","step","steps"]
        finish_words = ["done","finish","exit"]
        back_step_words = ["previous","back","last"]
        next_words = ["next", "yes"]
        step_counter = 1
        last_was_step = False

        while recipe_content:
            user = input("User: ")

            tokens = nltk.word_tokenize(user)
            s = set(tokens)
            if [x for x in ingredient_words if x in s]:
                last_was_step = False
                print("Bot:  Here are the ingredients for \"{0}\":".format(title))
                for k in ingredients_dict.keys():
                    print("\t" + k + ": " + ingredients_dict[k])
            elif [x for x in tool_words if x in s]:
                last_was_step = False
                print("Bot:  Here are the tools for \"{0}\":".format(title))
                for t in tools_list:
                    print("\t" + t)
            elif [x for x in method_words if x in s]:
                last_was_step = False
                print("Bot:  Here are the methods for \"{0}\":".format(title))
                for m in methods_list:
                    print("\t" + m)
            elif [x for x in instruction_words if x in s] or [x for x in back_step_words if x in s] or [x for x in next_words if x in s]:
                last_was_step = True
                user = alpha2digit(user, "en")
                if "first" in tokens:
                    step_counter = 1
                    print("Bot:  Step " + str(step_counter) + ": " + instructions_lst[step_counter - 1])
                elif "second" in tokens:
                    if len(instructions_lst) < 2:
                        print("Bot:  Step is out of bounds.")
                        continue
                    step_counter = 2
                    print("Bot:  Step " + str(step_counter) + ": " + instructions_lst[step_counter - 1])
                elif "third" in tokens:
                    if len(instructions_lst) < 3:
                        print("Bot:  Step is out of bounds.")
                        continue
                    step_counter = 3
                    print("Bot:  Step " + str(step_counter) + ": " + instructions_lst[step_counter - 1])
                elif re.search("\d+",user):
                    stepInt = int(re.search("\d+",user)[0])
                    if len(instructions_lst) >= stepInt > 0:
                        step_counter = stepInt
                        print("Bot:  Step " + str(step_counter) + ": " + instructions_lst[step_counter - 1])
                    else:
                        print("Bot:  There is no step {0}. There are only {1} steps.".format(stepInt, len(instructions_lst)))
                elif [x for x in next_words if x in s]:
                    step_counter += 1
                    if step_counter > len(instructions_lst):
                        print("Bot:  This is the final step. There are only {0} steps. What else can I do for you?".format(str(len(instructions_lst))))
                        step_counter -= 1
                        continue
                    print("Bot:  Step " + str(step_counter) + ": " + instructions_lst[step_counter-1])
                elif [x for x in back_step_words if x in s]:
                    if step_counter == 1:
                        print("Bot:  There are no steps before this. Should I continue to step {0}?".format(step_counter+1))
                        continue
                    step_counter = step_counter - 1
                    print("Bot:  Step " + str(step_counter) + ": " + instructions_lst[step_counter - 1])
                elif user == "no":
                    last_was_step = False
                    step_counter = 1
                else:
                    print("Bot:  Step " + str(step_counter) + ": " + instructions_lst[step_counter-1])

            elif [x for x in finish_words if x in s]:
                print("Bot:  Okay! Please enter another recipe URL.")
                break

            if last_was_step:
                if step_counter == len(instructions_lst):
                    print("Bot:  This is the final step. What else can I do for you?")
                else:
                    print("Bot:  Should I continue to step {0}?".format(step_counter+1))
            else:
                print("Bot:  What else can I do for you?")