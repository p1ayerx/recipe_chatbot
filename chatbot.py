import nltk
import recipe_parser
import validators
import requests
from bs4 import BeautifulSoup
import re
from text_to_num import alpha2digit

exit_flow = False
completely_done_flow = False

print("Recipe Robot:  How can I help today?")

while True:
    if completely_done_flow:
        break

    user = input("User:          ")

    tokens = nltk.word_tokenize(user)
    validate = validators.url(user)

    outer_finish_words = ["done","finish","exit","Done","Finish","Exit","no","No", "nothing", "no more", "Nothing", "No more", "no More", "No More", "I'm good", "I'm okay", "I'm ok", "i'm good", "i'm okay", "I'm OK", "i'm ok"]
    s = set(tokens)
    if [x for x in outer_finish_words if x in s]:
        exit_flow = True
        print("Recipe Robot:  Are you sure you want to exit?")

        exit_finish_words = ["Y", "y"]
        if exit_flow:
            exit_flow = False
            if [x for x in exit_finish_words if x in s]:
                print("Recipe Robot:  Bye! Enjoy Your Food!")
                break
            else:
                print("Recipe Robot:  Okay, I can continue to help")

    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Max-Age': '3600',
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'
    }

    googleURL = r"https://www.google.com/search?q=how+to"

    if "recipe" in tokens or "Recipe" in tokens:
        print("Recipe Robot:  Sure. Please specify a URL.")
    elif validate == True:
        print("Recipe Robot:  Loading recipe from URL. Please wait. It may take a minute.")

        req = requests.get(user, headers)
        soup = BeautifulSoup(req.content, 'html.parser')

        title = soup.find("h1", class_="headline heading-content").get_text().lstrip().rstrip()

        ingredients_dict,tools_list,methods_list,instructions_lst= recipe_parser.parse_url(user)

        print("Recipe Robot:  Alright. So let's start working with \"{0}.\" What do you want to do?".format(title))
        recipe_content = True

        ingredient_words = ["ingredients","ingredient","Ingredients","Ingredient"]
        tool_words = ["tool","tools","Tool","Tools"]
        method_words = ["method","methods","Method","Methods"]
        instruction_words = ["instructions","instruction","no","step","steps","Instructions","Instruction","No","Step","Steps"]
        finish_words = ["new", "New", "new recipe", "New recipe", "New Recipe", "new Recipe", "another", "Another", "another recipe", "Another recipe", "Another Recipe", "another Recipe", "different", "Different", "different recipe", "Different recipe", "Different Recipe", "different Recipe"]
        back_step_words = ["previous","back","last","Previous","Back","Last"]
        next_words = ["next", "yes", "forward", "Next", "Yes", "Forward"]
        how_to_words = ["How", "how"]
        bad_words = ["the", "a", "The", "A"]
        step_counter = 1
        last_was_step = False

        while recipe_content:
            if completely_done_flow:
                break

            user = input("User:          ")

            tokens = nltk.word_tokenize(user)
            s = set(tokens)
            if exit_flow == False:
                if [x for x in outer_finish_words if x in s]:
                    exit_flow = True
                    print("Recipe Robot:  Are you sure you want to exit? Y/n")
            else:
                exit_flow = False
                if [x for x in exit_finish_words if x in s]:
                    print("Recipe Robot:  Bye! Enjoy Your Food!")
                    completely_done_flow = True
                    break
                else:
                    print("Recipe Robot:  Okay, I can continue to help")

            if exit_flow == False:
                if [x for x in ingredient_words if x in s]:
                    last_was_step = False
                    print("Recipe Robot:  Here are the ingredients for \"{0}\":\n".format(title))
                    for k in ingredients_dict.keys():
                        print("\t- " + k + ": " + ingredients_dict[k])
                    print("")
                elif [x for x in tool_words if x in s]:
                    last_was_step = False
                    print("Recipe Robot:  Here are the tools for \"{0}\":\n".format(title))
                    for t in tools_list:
                        print("\t- " + t)
                    print("")
                elif [x for x in method_words if x in s]:
                    last_was_step = False
                    print("Recipe Robot:  Here are the methods for \"{0}\":\n".format(title))
                    for m in methods_list:
                        print("\t- " + m)
                    print("")
                elif [x for x in how_to_words if x in s]:
                    noun_phrases_input = recipe_parser.get_np(user)
                    noun_phrases_step = recipe_parser.get_np(instructions_lst[step_counter - 1])

                    if noun_phrases_input:
                        words = noun_phrases_input[0].split()
                    elif noun_phrases_step:
                        words = noun_phrases_step[0].split()
                    else:
                        print("Recipe Robot:  Sorry, I don't have answer for that.")
                        continue

                    words = [x for x in words if x not in bad_words]
                    query = googleURL
                    for x in words:
                        query += "+" + x
                    print("Recipe Robot:  No worries. I found a reference for you: " + query)

                elif [x for x in instruction_words if x in s] or [x for x in back_step_words if x in s] or [x for x in next_words if x in s]:
                    last_was_step = True
                    user = alpha2digit(user, "en")
                    if "first" in tokens:
                        step_counter = 1
                        print("Recipe Robot:  Step " + str(step_counter) + ": " + instructions_lst[step_counter - 1])
                    elif "second" in tokens:
                        if len(instructions_lst) < 2:
                            print("Recipe Robot:  Step is out of bounds.")
                            continue
                        step_counter = 2
                        print("Recipe Robot:  Step " + str(step_counter) + ": " + instructions_lst[step_counter - 1])
                    elif "third" in tokens:
                        if len(instructions_lst) < 3:
                            print("Recipe Robot:  Step is out of bounds.")
                            continue
                        step_counter = 3
                        print("Recipe Robot:  Step " + str(step_counter) + ": " + instructions_lst[step_counter - 1])
                    elif re.search("\d+",user):
                        stepInt = int(re.search("\d+",user)[0])
                        if len(instructions_lst) >= stepInt > 0:
                            step_counter = stepInt
                            print("Recipe Robot:  Step " + str(step_counter) + ": " + instructions_lst[step_counter - 1])
                        else:
                            print("Recipe Robot:  There is no step {0}. There are only {1} steps.".format(stepInt, len(instructions_lst)))
                    elif [x for x in next_words if x in s]:
                        step_counter += 1
                        if step_counter > len(instructions_lst):
                            print("Recipe Robot:  This is the final step. There are only {0} steps. What else can I do for you?".format(str(len(instructions_lst))))
                            step_counter -= 1
                            continue
                        print("Recipe Robot:  Step " + str(step_counter) + ": " + instructions_lst[step_counter-1])
                    elif [x for x in back_step_words if x in s]:
                        if step_counter == 1:
                            print("Recipe Robot:  There are no steps before this. Should I continue to step {0}?".format(step_counter+1))
                            continue
                        step_counter = step_counter - 1
                        print("Recipe Robot:  Step " + str(step_counter) + ": " + instructions_lst[step_counter - 1])
                    elif user == "no":
                        last_was_step = False
                        step_counter = 1
                    else:
                        print("Recipe Robot:  Step " + str(step_counter) + ": " + instructions_lst[step_counter-1])

                elif [x for x in finish_words if x in s]:
                    print("Recipe Robot:  Okay! Please enter another recipe URL.")
                    break

                if last_was_step:
                    if step_counter == len(instructions_lst):
                        print("Recipe Robot:  This is the final step. What else can I do for you?")
                    else:
                        print("Recipe Robot:  Should I continue to step {0}?".format(step_counter+1))
                else:
                    print("Recipe Robot:  What else can I do for you?")