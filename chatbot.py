import nltk
import recipe_parser
import validators
import requests
from bs4 import BeautifulSoup

while True:
    user = input("User: ")

    tokens = nltk.word_tokenize(user)
    validate = validators.url(user)

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

        while recipe_content:
            print("Bot: What do you want to know the ingredients or tools or methods or instructions of the recipe?")

            user = input("User: ")

            tokens = nltk.word_tokenize(user)
            if "ingredients" in tokens:
                print("Ingredients:")
                for k in ingredients_dict.keys():
                    print("\t" + k + ": " + ingredients_dict[k])
            elif "tools" in tokens:
                print("Tools:")
                for t in tools_list:
                    print("\t" + t)
            elif "methods" in tokens:
                for m in methods_list:
                    print("\t" + m)
            elif "instructions" in tokens:
                for i, instruction in enumerate(instructions_lst):
                    print("\tStep " + str(i + 1) + ": " + instruction)
            print("Bot: Do you want to know more about the recipe?")
            user = input("User: ")
            tokens = nltk.word_tokenize(user)
            if "no" in tokens:
                recipe_content = False
                print("OK! Try a new recipe.")